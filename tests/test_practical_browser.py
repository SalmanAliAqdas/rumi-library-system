"""Isolated browser verification for Phase 4; never uses local inventory."""

import os
import secrets
from pathlib import Path
from unittest import skipUnless
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from catalog.models import Copy, Edition, LibrarySettings, Shelf


@skipUnless(os.getenv("RUMI_BROWSER_TESTS") == "1", "Set RUMI_BROWSER_TESTS=1 for isolated Chromium tests")
@override_settings(SITE_URL="https://library.example.org", SITE_URL_CONFIGURED=True)
class PracticalBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(24)
        get_user_model().objects.create_superuser("phase4-browser", password=self.password)
        shelf = Shelf.objects.create(label="Phase 4 fixture shelf")
        book = Edition.objects.create(title="Phase 4 · علم · المعرفة", original_language="ur")
        self.copy = Copy.objects.create(edition=book, shelf=shelf, volume="۲")
        LibrarySettings.objects.create(whatsapp_number="+923001234567")

    def test_issue_public_return_whatsapp_csv_print_and_rtl(self):
        from playwright.sync_api import sync_playwright

        output = Path("test-results")
        output.mkdir(exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/librarian/login/")
            page.locator("#id_username").fill("phase4-browser")
            page.locator("#id_password").fill(self.password)
            page.locator(".entry-form button").click()
            page.wait_for_url("**/librarian/")
            page.goto(self.live_server_url + "/librarian/loans/issue/")
            page.locator("#id_copy").select_option(str(self.copy.pk))
            page.locator("#id_borrower_name").fill("Private browser fixture")
            page.locator("form[method=post].entry-form button").click()
            page.wait_for_url("**/librarian/loans/")
            page.goto(self.live_server_url + f"/copies/{self.copy.accession}/")
            self.assertEqual(page.locator(".availability").inner_text(), "On loan")
            self.assertNotIn("Private browser fixture", page.locator("body").inner_text())
            enquiry = page.locator('a[href^="https://wa.me/"]').get_attribute("href")
            self.assertEqual(urlsplit(enquiry).path, "/923001234567")
            self.assertIn(self.copy.accession, parse_qs(urlsplit(enquiry).query)["text"][0])
            # Inspect only: never click or send an enquiry.
            page.goto(self.live_server_url + "/librarian/loans/")
            page.get_by_role("link", name="Mark returned", exact=True).click()
            page.locator(".entry-form button").click()
            page.wait_for_url("**/librarian/loans/")
            page.goto(self.live_server_url + f"/copies/{self.copy.accession}/")
            self.assertEqual(page.locator(".availability").inner_text(), "Available")
            for code in ("ur", "ar"):
                page.locator("#interface-language").select_option(code)
                page.locator(".language-switch button").click()
                self.assertEqual(page.locator("html").get_attribute("lang"), code)
                self.assertEqual(page.locator("html").get_attribute("dir"), "rtl")
                page.goto(self.live_server_url + "/librarian/loans/issue/")
                self.assertTrue(page.locator("#id_borrower_name").is_visible())
                self.assertLessEqual(
                    page.evaluate("document.documentElement.scrollWidth"),
                    391,
                    page.evaluate(
                        "Array.from(document.querySelectorAll('body *')).filter(e => e.getBoundingClientRect().right > 391 || e.getBoundingClientRect().left < -1).map(e => [e.tagName,e.className,e.id]).slice(-10)"
                    ),
                )
            page.goto(self.live_server_url + "/librarian/labels/")
            page.locator(f'input[name=copies][value="{self.copy.pk}"]').check()
            page.locator("form[method=post] button").last.click()
            self.assertEqual(page.locator(".copy-label").count(), 1)
            self.assertEqual(page.locator(".qr-code svg").count(), 1)
            self.assertTrue(page.locator(".qr-code svg").get_attribute("viewBox"))
            self.assertIn(f"/copies/{self.copy.accession}/", page.locator(".copy-label").inner_text())
            page.screenshot(path=str(output / "phase4-label-mobile-ar.png"), full_page=True)
            page.emulate_media(media="print")
            self.assertFalse(page.locator(".management-nav").is_visible())
            self.assertFalse(page.locator(".label-controls").is_visible())
            self.assertTrue(page.locator(".copy-label").is_visible())
            page.pdf(path=str(output / "phase4-label-a4.pdf"), prefer_css_page_size=True)
            page.set_viewport_size({"width": 900, "height": 900})
            page.evaluate("document.fonts.ready")
            page.evaluate("window.scrollTo(0, 0)")
            page.evaluate(
                "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
            )
            page.locator(".label-sheet").screenshot(path=str(output / "phase4-label-print-ar.png"))
            page.emulate_media(media="screen")
            with page.expect_download() as download:
                page.locator('a[href="/librarian/public-catalog.csv"]').click()
            data = Path(download.value.path()).read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
            self.assertIn("علم", data.decode("utf-8-sig"))
            self.assertIn("المعرفة", data.decode("utf-8-sig"))
            self.assertNotIn(b"Private browser fixture", data)
            self.assertEqual(errors, [])
            browser.close()
