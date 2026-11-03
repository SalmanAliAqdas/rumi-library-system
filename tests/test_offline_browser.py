import os
from pathlib import Path
from unittest import skipUnless

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from catalog.models import Category, Copy, Edition, Language, Loan, Shelf


@skipUnless(
    os.getenv("RUMI_BROWSER_TESTS") == "1",
    "Set RUMI_BROWSER_TESTS=1 for isolated offline Chromium verification",
)
class OfflineBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.shelf = Shelf.objects.create(label="Offline fixture shelf")
        self.category = Category.objects.create(
            slug="offline-test", name="Fictional", name_ur="فرضی", name_ar="خيالي"
        )
        self.books = []
        for title, code, aliases in [
            ("Garden fixture", "en", ""),
            ("بُخَـاری", "ur", "Bukhari"),
            ("كِتَاب العلم", "ar", ""),
        ]:
            language = Language.objects.get_or_create(code=code, defaults={"name": code})[0]
            book = Edition.objects.create(title=title, original_language=code, aliases=aliases, is_demo=True)
            book.languages.add(language)
            book.categories.add(self.category)
            Copy.objects.create(edition=book, shelf=self.shelf)
            self.books.append(book)
        for index in range(17):
            title = (
                f"Previously unvisited fixture {index}"
                if index
                else 'Fictional <img src=x onerror="window.injected=true">'
            )
            book = Edition.objects.create(
                title=title,
                summary="<script>window.injected=true</script>" if not index else "",
                is_demo=True,
            )
            Copy.objects.create(edition=book, shelf=self.shelf)
            self.books.append(book)
        self.english = self.books[0]
        self.english.cover_url = self.live_server_url + "/static/offline/icon-192.png"
        self.english.save()
        self.books[1].cover_url = self.live_server_url + "/missing-cover.png"
        self.books[1].save()
        self.books[2].cover_url = "https://covers.invalid/no-cors.png"
        self.books[2].save()
        self.extra_copy = Copy.objects.create(edition=self.english, shelf=self.shelf, volume="II")
        self.hidden = Copy.objects.create(edition=self.english, shelf=self.shelf, is_public=False)
        Loan.objects.create(
            copy=self.english.copies.get(volume="", is_public=True),
            borrower_name="PRIVATE OFFLINE BORROWER",
            contact="PRIVATE OFFLINE CONTACT",
        )
        private = Edition.objects.create(title="PRIVATE HIDDEN TITLE")
        Copy.objects.create(edition=private, shelf=self.shelf, is_public=False)

    def open_offline(self, page):
        from playwright.sync_api import expect

        page.goto(self.live_server_url + "/offline/")
        expect(page.locator("#download")).to_be_enabled(timeout=30000)

    def saved(self, page):
        return page.evaluate("async () => (await import('/static/offline/store.js')).readState()")

    def download(self, page):
        from playwright.sync_api import expect

        page.locator("#download").click()
        expect(page.locator("#status")).to_contain_text("saved successfully", timeout=20000)

    def test_complete_download_offline_navigation_update_failure_and_remove(self):
        from playwright.sync_api import Error, expect, sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            self.open_offline(page)
            self.assertIsNone(self.saved(page)["snapshot"])
            expect(page.locator("#results")).to_contain_text("No catalogue saved")
            self.download(page)
            saved = self.saved(page)
            self.assertEqual((saved["snapshot"]["edition_count"], saved["snapshot"]["copy_count"]), (20, 21))
            expect(page.locator("#download-summary")).to_contain_text("Last successful download")
            self.assertNotIn("PRIVATE OFFLINE", str(saved))
            self.assertNotIn(self.hidden.accession, str(saved))
            context.set_offline(True)
            page.reload()
            expect(page.locator("#connection")).to_contain_text("reports offline")
            expect(page.locator(".book-card")).to_have_count(12)
            self.assertIsNone(page.evaluate("window.injected"))
            expect(page.locator('img[src="x"]')).to_have_count(0)
            for query, expected in [
                ("Garden", "Garden fixture"),
                ("بخاري", "بُخَـاری"),
                ("کتاب العلم", "كِتَاب العلم"),
                ("Bukhari", "بُخَـاری"),
            ]:
                page.locator("#q").fill(query)
                page.locator("#offline-search button").click()
                expect(page.locator(".book-card")).to_have_count(1)
                expect(page.locator(".book-card h3")).to_have_text(expected)
            page.locator("#q").fill("Garden")
            page.select_option("#language", "en")
            page.select_option("#category", self.category.slug)
            page.select_option("#availability", "on_loan")
            page.locator("#offline-search button").click()
            expect(page.locator(".book-card")).to_have_count(1)
            page.locator(".book-card a").click()
            expect(page.locator(".copy-list li")).to_have_count(2)
            expect(page.locator(".copy-list")).to_contain_text(self.shelf.label)
            page.reload()
            expect(page.locator(".copy-list")).to_contain_text(self.extra_copy.accession)
            unvisited = context.new_page()
            unvisited.goto(self.live_server_url + f"/offline/?book={self.books[-1].pk}")
            expect(unvisited.locator("#book-detail h1")).to_have_text(self.books[-1].title)
            unvisited.reload()
            expect(unvisited.locator(".copy-list")).to_contain_text(self.shelf.label)
            page.select_option("#offline-language", "ur")
            self.assertEqual(page.locator("html").get_attribute("dir"), "rtl")
            page.select_option("#offline-language", "ar")
            self.assertEqual(page.locator("html").get_attribute("lang"), "ar")
            page.evaluate("document.fonts.ready")
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            output = Path("test-results")
            output.mkdir(exist_ok=True)
            page.screenshot(path=str(output / "phase3-offline-arabic-mobile.png"), full_page=True)
            # Private pages are outside the service worker's scope and must fail, never show a public fallback.
            private = context.new_page()
            with self.assertRaises(Error):
                private.goto(self.live_server_url + "/librarian/")
            self.assertTrue(
                page.evaluate(
                    "async () => { try { await fetch('/librarian/books/add/', {method: 'POST', body: 'title=forged'}); return false; } catch { return true; } }"
                )
            )
            context.set_offline(False)
            page.select_option("#offline-language", "en")
            self.download(page)
            updated = self.saved(page)
            self.assertNotEqual(saved["revision"], updated["revision"])
            context.route("**/catalog/public-snapshot.json", lambda route: route.abort())
            page.locator("#download").click()
            expect(page.locator("#status")).to_contain_text("Update failed")
            self.assertEqual(self.saved(page)["revision"], updated["revision"])
            context.unroute("**/catalog/public-snapshot.json")
            context.route(
                "**/catalog/public-snapshot.json",
                lambda route: route.fulfill(
                    status=200, content_type="application/json", body='{"schema_version":99}'
                ),
            )
            page.locator("#download").click()
            expect(page.locator("#status")).to_contain_text("incomplete or incompatible")
            self.assertEqual(self.saved(page)["revision"], updated["revision"])
            context.unroute("**/catalog/public-snapshot.json")
            caches = page.evaluate(
                "async () => { const result = []; for (const name of await caches.keys()) result.push(...(await (await caches.open(name)).keys()).map(r => r.url)); return result; }"
            )
            self.assertTrue(all("/static/" in url or url.endswith("/offline/") for url in caches))
            self.assertTrue(
                all(
                    "/admin/" not in url and "/librarian/" not in url and "snapshot.json" not in url
                    for url in caches
                )
            )
            page.goto(self.live_server_url + "/offline/")
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#remove").click()
            expect(page.locator("#results")).to_contain_text("No catalogue saved")
            self.assertIsNone(self.saved(page)["snapshot"])
            context.set_offline(True)
            page.reload()
            expect(page.locator("#results")).to_contain_text("No catalogue saved")
            self.assertEqual(errors, [])
            browser.close()

    def test_storage_abort_quota_and_concurrent_revision_guards(self):
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            context = browser.new_context()
            page = context.new_page()
            self.open_offline(page)
            self.download(page)
            original = self.saved(page)
            for mode in ["quota", "abort"]:
                page.evaluate(
                    """mode => { window.originalPut = IDBObjectStore.prototype.put;
                IDBObjectStore.prototype.put = function(...args) {
                  if (mode === 'quota') throw new DOMException('Full', 'QuotaExceededError');
                  const result = window.originalPut.apply(this, args); this.transaction.abort(); return result;
                }; }""",
                    mode,
                )
                page.locator("#download").click()
                expect(page.locator("#status")).to_contain_text("storage is unavailable")
                page.evaluate("() => { IDBObjectStore.prototype.put = window.originalPut; }")
                self.assertEqual(self.saved(page)["revision"], original["revision"])
            other = page.context.new_page()
            self.open_offline(other)
            for tab in [page, other]:
                tab.evaluate(
                    "async () => { window.testBase = await (await import('/static/offline/store.js')).readState(); }"
                )
            page.evaluate(
                "async () => { const store = await import('/static/offline/store.js'); await store.replaceCatalog(window.testBase.snapshot, window.testBase.revision); }"
            )
            stale_tab = other.evaluate(
                "async () => { const store = await import('/static/offline/store.js'); try { await store.replaceCatalog(window.testBase.snapshot, window.testBase.revision); return false; } catch (error) { return error.message; } }"
            )
            self.assertEqual(stale_tab, "catalog_changed")
            other.close()
            # Same base revision from two tabs: only one can activate; removal is a tombstone.
            result = page.evaluate("""async () => {
                const store = await import('/static/offline/store.js'); const base = await store.readState();
                const outcomes = await Promise.allSettled([store.replaceCatalog(base.snapshot, base.revision), store.replaceCatalog(base.snapshot, base.revision)]);
                const beforeRemove = await store.readState(); await store.removeCatalog();
                let stale; try { await store.replaceCatalog(beforeRemove.snapshot, beforeRemove.revision); stale = false; } catch (e) { stale = e.message; }
                return {outcomes: outcomes.map(o => o.status), stale, final: (await store.readState()).snapshot};
            }""")
            self.assertEqual(sorted(result["outcomes"]), ["fulfilled", "rejected"])
            self.assertEqual(result["stale"], "catalog_changed")
            self.assertIsNone(result["final"])
            browser.close()

    def test_storage_unavailable_and_empty_catalogue_are_recoverable(self):
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            blocked = browser.new_context()
            blocked.add_init_script(
                "window.originalOpen = indexedDB.open; indexedDB.open = () => { throw new DOMException('Blocked', 'SecurityError'); };"
            )
            page = blocked.new_page()
            self.open_offline(page)
            expect(page.locator("#status")).to_contain_text("storage is unavailable")
            page.evaluate("() => { indexedDB.open = window.originalOpen; }")
            # Empty but structurally valid snapshots are successful downloads, not an error.
            blocked.route(
                "**/catalog/public-snapshot.json",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body='{"schema_version":1,"normalization_version":1,"generated_at":"2026-11-03T01:00:00.000000+00:00","edition_count":0,"copy_count":0,"editions":[]}',
                ),
            )
            self.download(page)
            expect(page.locator("#results")).to_contain_text("no public books yet")
            self.assertEqual(self.saved(page)["snapshot"]["edition_count"], 0)
            browser.close()

    def test_optional_covers_are_separate_removable_and_nonfatal(self):
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            context = browser.new_context()
            context.route(
                "https://covers.invalid/**",
                lambda route: route.fulfill(
                    status=200,
                    content_type="image/png",
                    # Explicit mismatch: Playwright may add a permissive CORS
                    # header to fulfilled requests when the header is absent.
                    headers={"access-control-allow-origin": "https://different.invalid"},
                    body=(Path(__file__).parent.parent / "static/offline/icon-192.png").read_bytes(),
                ),
            )
            page = context.new_page()
            self.open_offline(page)
            self.download(page)
            original = self.saved(page)
            page.locator(".download-panel summary").click()
            page.locator("#download-covers").click()
            expect(page.locator("#status")).to_contain_text("Saved / attempted: 1 / 3")
            self.assertEqual(self.saved(page)["revision"], original["revision"])
            context.set_offline(True)
            page.goto(self.live_server_url + f"/offline/?book={self.english.pk}")
            expect(page.locator("#book-detail .book-art img")).to_be_visible()
            page.locator(".download-panel summary").click()
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#remove-covers").click()
            expect(page.locator("#status")).to_contain_text("Catalogue text is kept")
            expect(page.locator("#book-detail .book-art img")).to_have_count(0)
            self.assertEqual(self.saved(page)["snapshot"]["edition_count"], 20)
            browser.close()
