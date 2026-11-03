"""Opt-in browser verification against Django's isolated test database."""

import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from catalog.models import Category, Contributor, Copy, Edition, Language, Shelf


@skipUnless(
    os.getenv("RUMI_BROWSER_TESTS") == "1",
    "Set RUMI_BROWSER_TESTS=1 to run Chromium in the isolated test database",
)
class LibrarianBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(24)
        get_user_model().objects.create_superuser("browser-fixture", password=self.password)
        self.shelf = Shelf.objects.create(label="Browser fixture A")
        self.other_shelf = Shelf.objects.create(label="Browser fixture B")
        self.category = Category.objects.create(slug="browser-fixture", name="Browser fixture")
        self.author = Contributor.objects.create(name="Browser fictional writer")
        for code, name in [("en", "English"), ("ur", "اردو"), ("ar", "العربية")]:
            Language.objects.get_or_create(code=code, defaults={"name": name})
        self.urdu_pk = Language.objects.get(code="ur").pk

    def test_librarian_flow_mobile_rtl_and_public_search(self):
        from playwright.sync_api import sync_playwright

        output = Path("test-results")
        output.mkdir(exist_ok=True)
        # Playwright's sync API runs an event loop; ORM reads stay in a worker thread.
        with ThreadPoolExecutor(max_workers=1) as queries, sync_playwright() as playwright:

            def db_read(operation):
                return queries.submit(operation).result()

            browser = playwright.chromium.launch(channel="chromium")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/librarian/")
            page.locator("#id_username").fill("browser-fixture")
            page.locator("#id_password").fill(self.password)
            page.locator(".entry-form button").click()
            page.wait_for_url("**/librarian/")
            self.assertIn("Librarian dashboard", page.locator("h1").inner_text())
            page.get_by_role("link", name="+ Add a book", exact=True).click()
            title = "Browser fixture · باغِ علم"
            page.locator("#id_title").fill(title)
            page.select_option("#id_original_language", "ur")
            page.select_option("#id_authors", str(self.author.pk))
            page.select_option("#id_languages", str(self.urdu_pk))
            page.select_option("#id_categories", str(self.category.pk))
            page.select_option("#id_copy-shelf", str(self.shelf.pk))
            # A new metadata record in another tab does not discard the book draft.
            with page.expect_popup() as popup:
                page.locator('.draft-links a[href$="contributors/add/"]').click()
            tab = popup.value
            tab.locator("#id_name").fill("Browser new contributor")
            tab.locator(".entry-form button").click()
            tab.wait_for_url("**/records/contributors/")
            tab.close()
            page.get_by_role("button", name="Refresh choices (keep draft)", exact=True).click()
            self.assertEqual(page.locator("#id_title").input_value(), title)
            self.assertIn("Browser new contributor", page.locator("#id_authors").inner_text())
            page.locator('button[name="intent"][value="save"]').click()
            page.wait_for_url("**/librarian/books/*/")
            book = db_read(lambda: Edition.objects.get(title=title))
            self.assertEqual(db_read(lambda: book.copies.count()), 1)
            page.get_by_role("link", name="Add another copy", exact=True).click()
            page.locator("#id_volume").fill("Duplicate fixture")
            page.locator(".entry-form button").click()
            page.wait_for_url("**/librarian/books/*/")
            page.get_by_role("link", name="Add volumes", exact=True).click()
            page.locator("#id_end").fill("3")
            page.locator('button[value="preview"]').click()
            self.assertEqual(db_read(lambda: book.copies.count()), 2)
            page.locator("#id_labels").fill("جلد اول\nII\nالثالث")
            page.locator('button[value="confirm"]').click()
            page.wait_for_url("**/librarian/books/*/")
            self.assertEqual(db_read(lambda: book.copies.count()), 5)
            page.locator(".record-list li a").first.click()
            page.select_option("#id_shelf", str(self.other_shelf.pk))
            page.locator(".entry-form button").click()
            page.wait_for_url("**/librarian/books/*/")
            self.assertEqual(
                db_read(lambda: Copy.objects.filter(edition=book, shelf=self.other_shelf).count()), 1
            )
            page.select_option("#interface-language", "ur")
            page.locator(".language-switch button").click()
            self.assertEqual(page.locator("html").get_attribute("dir"), "rtl")
            page.goto(self.live_server_url + "/librarian/books/add/")
            page.evaluate("document.fonts.ready")
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            page.screenshot(path=str(output / "phase2-entry-urdu-mobile.png"), full_page=True)
            page.select_option("#interface-language", "ar")
            page.locator(".language-switch button").click()
            self.assertEqual(page.locator("html").get_attribute("lang"), "ar")
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            page.goto(self.live_server_url + "/books/?q=باغ علم")
            self.assertEqual(page.locator(".book-card").count(), 1)
            page.locator(".book-card a").click()
            self.assertEqual(page.locator(".copy-list li").count(), 5)
            self.assertIn("Browser fixture B", page.locator(".copy-list").inner_text())
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.goto(self.live_server_url + "/librarian/")
            page.screenshot(path=str(output / "phase2-dashboard-arabic-desktop.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
