"""Run against a local, seeded development server: python scripts/browser_smoke.py."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT = Path("test-results")
OUTPUT.mkdir(exist_ok=True)


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        assert page.goto("http://127.0.0.1:8000/").status == 200
        page.get_by_role("heading", level=1).wait_for()
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.fonts.check('16px Literary')")
        page.screenshot(path=str(OUTPUT / "home-desktop.png"), full_page=True)
        page.locator("#home-q").fill("Orchard")
        page.locator(".hero-search button").click()
        assert page.locator(".book-card").count() == 1
        page.locator(".book-card a").click()
        assert page.locator(".copy-list li").count() == 2
        assert "RL-" in page.locator(".copy-list").inner_text()
        detail_url = page.url
        page.select_option("#interface-language", "ur")
        page.locator(".language-switch button").click()
        assert page.url == detail_url
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.locator("html").get_attribute("lang") == "ur"
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUTPUT / "detail-urdu-mobile.png"), full_page=True)
        page.goto("http://127.0.0.1:8000/")
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUTPUT / "home-urdu-mobile.png"), full_page=True)
        page.select_option("#interface-language", "ar")
        page.locator(".language-switch button").click()
        assert page.locator("html").get_attribute("lang") == "ar"
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.goto("http://127.0.0.1:8000/?display=1")
        assert page.locator(".librarian").is_hidden()
        assert page.evaluate("document.fullscreenElement === null")
        assert not errors, errors
        browser.close()
        print(
            "PASS: welcome, search, detail/copies, language preservation, Urdu mobile/RTL, Arabic, display; no JS errors"
        )


if __name__ == "__main__":
    main()
