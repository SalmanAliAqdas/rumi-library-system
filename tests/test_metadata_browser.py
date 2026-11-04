import os
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from catalog.metadata import suggestion
from catalog.models import Language, Shelf


@skipUnless(os.getenv("RUMI_BROWSER_TESTS") == "1", "Set RUMI_BROWSER_TESTS=1 for isolated Chromium tests")
class MetadataBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        get_user_model().objects.create_superuser("metadata-browser", password="isolated-fixture-only")
        Shelf.objects.create(label="Metadata fixture shelf")
        Language.objects.get_or_create(code="en", defaults={"name": "English"})

    def test_mobile_lookup_preview_approval_save_and_public_result(self):
        from playwright.sync_api import sync_playwright

        result = suggestion(
            {
                "key": "/books/OL1M",
                "title": "Provider title",
                "publisher": ["Fixture press"],
                "description": "<b>Safe description</b>",
                "publish_date": "2001",
            }
        )
        with patch("catalog.metadata.lookup", return_value=[result]), sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/librarian/login/")
            page.locator("#id_username").fill("metadata-browser")
            page.locator("#id_password").fill("isolated-fixture-only")
            page.locator(".entry-form button").click()
            page.wait_for_url("**/librarian/")
            page.goto(self.live_server_url + "/librarian/books/add/")
            page.locator("#id_title").fill("Manual title · علم")
            page.locator("#id_unknown_author").check()
            page.locator("#id_languages").select_option(label="English")
            page.locator("#id_copy-shelf").select_option(label="Metadata fixture shelf")
            page.locator("details").first.locator("summary").click()
            page.locator("#id_lookup_title").fill("علم")
            page.locator('button[value="lookup"]').click()
            page.wait_for_load_state()
            self.assertEqual(page.locator("#id_title").input_value(), "Manual title · علم")
            self.assertFalse(page.locator("[name=approve][value=title]").is_checked())
            self.assertTrue(page.locator("[name=approve][value=publisher]").is_checked())
            page.locator('button[value="apply_metadata"]').click()
            page.wait_for_load_state()
            self.assertEqual(page.locator("#id_title").input_value(), "Manual title · علم")
            self.assertEqual(page.locator("#id_publisher").input_value(), "Fixture press")
            self.assertEqual(page.locator("#id_summary").input_value(), "Safe description")
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.locator('button[value="save"]').click()
            page.wait_for_url("**/librarian/books/*/")
            page.goto(self.live_server_url + "/books/?q=Manual+title")
            self.assertEqual(page.get_by_role("heading", name="Manual title · علم", exact=True).count(), 1)
            page.locator(".book-card .book-link").first.click()
            self.assertIn("Safe description", page.locator("body").inner_text())
            self.assertIn("Fixture press", page.locator("body").inner_text())
            self.assertEqual(errors, [])
            Path("test-results").mkdir(exist_ok=True)
            page.screenshot(path="test-results/phase5-public-mobile.png", full_page=True)
            public_path = page.url.removeprefix(self.live_server_url)
            for language in ["ur", "ar"]:
                page.context.add_cookies(
                    [{"name": "django_language", "value": language, "url": self.live_server_url}]
                )
                page.goto(self.live_server_url + "/librarian" + public_path + "edit/")
                page.locator("details").first.locator("summary").click()
                page.locator("#id_lookup_title").fill("علم")
                page.locator('button[value="lookup"]').click()
                page.wait_for_load_state()
                self.assertEqual(page.locator("html").get_attribute("dir"), "rtl")
                self.assertEqual(page.locator("#id_title").input_value(), "Manual title · علم")
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
                page.screenshot(path=f"test-results/phase5-lookup-{language}.png", full_page=True)
            browser.close()
