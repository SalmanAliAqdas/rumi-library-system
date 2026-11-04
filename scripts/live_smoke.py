"""Read-only live checks in fresh Chromium storage; never creates inventory."""

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import Error, expect, sync_playwright

BASE = "https://rumi-library.vercel.app"
ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "test-results" / "phase6-live.json"
SECRETS = []


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def saved(page):
    return page.evaluate("async () => (await import('/static/offline/store.js')).readState()")


def run(authenticated=False, expect_empty=False):
    report = {"url": BASE, "checks": [], "authenticated": authenticated}
    REPORT.parent.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(error.name))
        check(page.goto(BASE + "/").status == 200, "homepage")
        check(page.locator('link[rel="canonical"]').get_attribute("href") == BASE + "/", "canonical")
        check(
            page.locator('meta[property="og:image"]').get_attribute("content").startswith(BASE + "/static/"),
            "Open Graph",
        )
        check(not page.locator('a[href^="https://wa.me/"]').count(), "WhatsApp hidden until configured")
        for language in ["ur", "ar", "en"]:
            page.select_option("#interface-language", language)
            page.locator(".language-switch button").click()
            expect(page.locator("html")).to_have_attribute("lang", language)
            expect(page.locator("html")).to_have_attribute("dir", "ltr" if language == "en" else "rtl")
            page.evaluate("document.fonts.ready")
            check(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "mobile overflow")
        report["checks"].append("homepage, canonical, Open Graph, HTTPS language/CSRF, mobile RTL")
        for path in [
            "/static/css/library.css",
            "/static/js/library.js",
            "/static/fonts/Newsreader.ttf",
            "/static/fonts/NotoNaskhArabic.ttf",
            "/static/fonts/NotoNastaliqUrdu.ttf",
            "/static/offline/icon-192.png",
            "/static/offline/icon-512.png",
            "/static/offline/manifest.webmanifest",
        ]:
            response = context.request.get(BASE + path)
            check(response.status == 200 and len(response.body()) > 0, "static asset " + path)
        report["checks"].append("CSS, JavaScript, three local fonts, icons and manifest")
        check(context.request.get(BASE + "/health/").json() == {"status": "ok"}, "health")
        snapshot = context.request.get(BASE + "/catalog/public-snapshot.json").json()
        report["edition_count"] = snapshot["edition_count"]
        report["copy_count"] = snapshot["copy_count"]
        if expect_empty:
            check(snapshot["edition_count"] == snapshot["copy_count"] == 0, "empty catalog")
        for path in [
            "/books/?q=unmatched-fixture&language=ur&availability=available&page=2",
            "/sitemap.xml",
            "/sitemap.xml?page=1",
            "/robots.txt",
        ]:
            response = context.request.get(BASE + path)
            check(response.status == 200, "public route " + path)
            check(
                "SECRET_KEY" not in response.text() and "DATABASE_URL" not in response.text(),
                "public configuration privacy",
            )
        for path in ["/books/2147483647/", "/copies/PHASE6-NONEXISTENT/", "/phase6-nonexistent/"]:
            response = context.request.get(BASE + path)
            check(response.status == 404, "production missing route")
            check(
                "Using the URLconf" not in response.text() and "Traceback" not in response.text(),
                "production debug disabled",
            )
        for path in [
            "/librarian/",
            "/librarian/public-catalog.csv",
            "/librarian/labels/",
            "/librarian/loans/",
        ]:
            response = context.request.get(BASE + path, max_redirects=0)
            check(
                response.status == 302 and "/librarian/login/" in response.headers.get("location", ""),
                "anonymous permission " + path,
            )
        check(
            context.request.post(BASE + "/librarian/books/add/", data={"title": "must not save"}).status
            == 403,
            "CSRF mutation rejection",
        )
        page.goto(BASE + "/?display=1")
        expect(page.locator("body")).to_have_class("display-mode")
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.screenshot(path=str(REPORT.parent / "phase6-live-display.png"), full_page=True)
        report["checks"].append(
            "search/filter/pagination empty states, sitemap/robots, production 404, anonymous/private/CSRF, display mode"
        )
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE + "/offline/")
        expect(page.locator("#download")).to_be_enabled(timeout=45000)
        page.locator("#download").click()
        expect(page.locator("#status")).to_contain_text("saved successfully", timeout=45000)
        state = saved(page)
        check(state["snapshot"]["edition_count"] == snapshot["edition_count"], "offline count")
        expect(page.locator("#download-summary")).to_contain_text("Last successful download")
        context.set_offline(True)
        page.reload()
        expect(page.locator("#connection")).to_contain_text("reports offline")
        for language in ["ur", "ar", "en"]:
            page.select_option("#offline-language", language)
            expect(page.locator("html")).to_have_attribute("lang", language)
            page.locator("#q").fill("علم")
            page.locator("#offline-search button").click()
        private = context.new_page()
        try:
            private.goto(BASE + "/librarian/")
        except Error:
            pass
        else:
            raise AssertionError("private page incorrectly available offline")
        check(
            page.evaluate(
                "async () => {try {await fetch('/librarian/books/add/', {method:'POST', body:'title=forged'});return false;}catch{return true;}}"
            ),
            "offline mutations unavailable",
        )
        private.close()
        context.set_offline(False)
        page.locator("#download").click()
        expect(page.locator("#status")).to_contain_text("saved successfully", timeout=45000)
        updated = saved(page)
        check(updated["revision"] != state["revision"], "catalog update revision")
        page.route("**/catalog/public-snapshot.json", lambda route: route.abort())
        page.locator("#download").click()
        expect(page.locator("#status")).to_contain_text("Update failed", timeout=45000)
        check(saved(page)["revision"] == updated["revision"], "interrupted update rollback")
        page.unroute("**/catalog/public-snapshot.json")
        cached = page.evaluate(
            "async () => (await Promise.all((await caches.keys()).map(async name => (await (await caches.open(name)).keys()).map(request => request.url)))).flat()"
        )
        check(
            not any("/librarian/" in url or "/admin/" in url or "snapshot.json" in url for url in cached),
            "worker cache boundaries",
        )
        sw = context.request.get(BASE + "/offline/sw.js")
        check(
            sw.status == 200
            and "javascript" in sw.headers["content-type"]
            and "no-cache" in sw.headers["cache-control"],
            "service worker response",
        )
        report["checks"].append(
            "live HTTPS catalog download/timestamp, offline reload/search/languages, private failures, update/interruption, cache boundaries"
        )
        if authenticated:
            credentials = json.loads((ROOT / ".vercel" / "smoke-account.json").read_text(encoding="utf-8"))
            SECRETS.append(credentials["password"])
            page.goto(BASE + "/librarian/login/")
            page.locator("#id_username").fill(credentials["username"])
            page.locator("#id_password").fill(credentials["password"])
            page.locator(".entry-form button").click()
            page.wait_for_url(BASE + "/librarian/", timeout=45000)
            cookie = next(value for value in context.cookies() if value["name"] == "sessionid")
            check(cookie["secure"] and cookie["httpOnly"], "secure session cookie")
            response = context.request.get(BASE + "/librarian/")
            check("no-store" in response.headers.get("cache-control", ""), "private caching")
            page.goto(BASE + "/librarian/books/add/")
            page.locator("#id_title").fill("UNSAVED PHASE 6 VERIFICATION DRAFT")
            page.locator("details").first.locator("summary").click()
            page.locator("#id_lookup_isbn").fill("9780140328721")
            page.locator('button[value="lookup"]').click()
            page.wait_for_load_state()
            check(
                page.locator("#id_title").input_value() == "UNSAVED PHASE 6 VERIFICATION DRAFT",
                "metadata draft preservation",
            )
            content = page.locator(".book-entry details").first.inner_text()
            report["metadata_outcome"] = (
                "suggestion" if page.locator("[data-suggestion]").count() else "graceful fallback"
            )
            check(
                any(value in content for value in ["Open Library", "unavailable", "No suggestions"]),
                "metadata response",
            )
            export = context.request.get(BASE + "/librarian/public-catalog.csv")
            check(export.status == 200 and export.body().startswith(b"\xef\xbb\xbf"), "authenticated CSV")
            for path in ["/librarian/loans/", "/librarian/loans/issue/", "/librarian/labels/"]:
                check(context.request.get(BASE + path).status == 200, "private tool " + path)
            page.goto(BASE + "/librarian/")
            page.locator('form[action="/librarian/logout/"] button').click()
            page.wait_for_url("**/librarian/login/")
            check(context.request.get(BASE + "/librarian/", max_redirects=0).status == 302, "logout")
            report["checks"].append(
                "temporary-account HTTPS login/logout, secure cookies, private tools/CSV, live metadata without saving"
            )
        check(not errors, "JavaScript errors")
        context.close()
        browser.close()
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authenticated", action="store_true")
    parser.add_argument("--expect-empty", action="store_true")
    options = parser.parse_args()
    try:
        run(options.authenticated, options.expect_empty)
    except Exception as error:
        message = str(error)
        for secret in SECRETS:
            message = message.replace(secret, "[redacted]")
        print(f"Live check failed: {type(error).__name__}: {message}", file=sys.stderr)
        sys.exit(1)
