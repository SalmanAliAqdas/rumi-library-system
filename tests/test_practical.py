import csv
import io
import json
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import segno
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from catalog.copy_links import canonical_site_url, copy_url, temporary_site, whatsapp_url
from catalog.lending import csv_safe
from catalog.models import Copy, Edition, LibrarySettings, Loan, Shelf, Submission
from catalog.offline import snapshot_bytes
from catalog.practical_labels import LABELS
from catalog.templatetags.library_ui import ui
from catalog.workflows import issue_token


@override_settings(SITE_URL="https://library.example.org", SITE_URL_CONFIGURED=True)
class PracticalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("phase4-fixture")
        self.shelf = Shelf.objects.create(label="Fixture shelf")
        self.book = Edition.objects.create(title='علم، المعرفة "Book"\nsecond line')
        self.copy = Copy.objects.create(edition=self.book, shelf=self.shelf, volume="جلد ۲")
        self.hidden = Copy.objects.create(edition=self.book, shelf=self.shelf, is_public=False)
        self.client.force_login(self.user)

    def payload(self, **updates):
        values = {
            "copy": self.copy.pk,
            "borrower_name": "PRIVATE FICTIONAL BORROWER",
            "contact": "PRIVATE CONTACT",
            "issue_date": timezone.localdate(),
            "due_date": "",
            "token": issue_token(self.user, "loan:issue"),
        }
        values.update(updates)
        return values

    def test_permissions_all_endpoints_and_direct_posts(self):
        loan = Loan.objects.create(copy=self.copy, borrower_name="Fixture")
        paths = [
            "/librarian/loans/",
            "/librarian/loans/issue/",
            f"/librarian/loans/{loan.pk}/return/",
            f"/librarian/copies/{self.copy.accession}/loans/",
            "/librarian/labels/",
            "/librarian/public-catalog.csv",
        ]
        self.client.logout()
        for path in paths:
            for method in (self.client.get, self.client.post):
                self.assertEqual(method(path).status_code, 302, path)
        staff = get_user_model().objects.create_user("restricted", is_staff=True)
        self.client.force_login(staff)
        for path in paths:
            for method in (self.client.get, self.client.post):
                self.assertEqual(method(path).status_code, 403, path)
        staff.user_permissions.set(
            Permission.objects.filter(
                codename__in=["view_edition", "view_copy", "view_loan"], content_type__app_label="catalog"
            )
        )
        self.assertEqual(self.client.post("/librarian/loans/issue/", self.payload()).status_code, 403)
        self.assertEqual(self.client.post(f"/librarian/loans/{loan.pk}/return/").status_code, 403)

    def test_csrf_and_http_methods(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/librarian/loans/issue/", self.payload()).status_code, 403)
        loan = Loan.objects.create(copy=self.copy, borrower_name="Fixture")
        self.assertEqual(client.post(f"/librarian/loans/{loan.pk}/return/").status_code, 403)
        self.assertEqual(client.post("/librarian/labels/", {"copies": self.copy.pk}).status_code, 403)
        self.assertEqual(self.client.post("/librarian/public-catalog.csv").status_code, 405)
        self.client.get(f"/librarian/loans/{loan.pk}/return/")
        loan.refresh_from_db()
        self.assertIsNone(loan.returned_date)

    def test_issue_return_retry_availability_and_private_history(self):
        self.assertTrue(self.copy.available)
        payload = self.payload()
        self.assertEqual(self.client.post("/librarian/loans/issue/", payload).status_code, 302)
        self.assertFalse(self.copy.available)
        self.assertEqual(self.client.post("/librarian/loans/issue/", payload).status_code, 302)
        self.assertEqual(Loan.objects.count(), 1)
        loan = Loan.objects.get()
        self.assertContains(self.client.get(copy_url(self.copy)), "On loan")
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("librarian:return", args=[loan.pk])).status_code, 302)
        self.assertTrue(self.copy.available)
        self.assertEqual(Loan.objects.count(), 1)
        # A retried issue after return must not create a new loan.
        self.client.post("/librarian/loans/issue/", payload)
        self.assertEqual(Loan.objects.count(), 1)
        self.assertContains(
            self.client.get(reverse("librarian:loan_history", args=[self.copy.accession])),
            payload["borrower_name"],
        )
        self.assertContains(self.client.get(copy_url(self.copy)), "Available")

    def test_invalid_dates_and_already_borrowed(self):
        today = timezone.localdate()
        for updates in [
            {"issue_date": today + timedelta(days=1)},
            {"due_date": today - timedelta(days=1)},
            {"issue_date": "invalid"},
        ]:
            response = self.client.post("/librarian/loans/issue/", self.payload(**updates))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(Loan.objects.count(), 0)
        Loan.objects.create(copy=self.copy, borrower_name="Existing")
        response = self.client.post("/librarian/loans/issue/", self.payload())
        self.assertContains(response, ui("loan_conflict"))
        self.assertEqual(Submission.objects.count(), 0)
        self.assertEqual(Loan.objects.count(), 1)

    def test_timezone_and_admin_model_date_validation(self):
        from datetime import datetime
        from datetime import timezone as dt_timezone

        from django.core.exceptions import ValidationError

        moment = datetime(2026, 11, 3, 21, tzinfo=dt_timezone.utc)
        with patch("django.utils.timezone.now", return_value=moment):
            today = timezone.localdate()
            self.assertEqual(today.day, 4)  # Asia/Karachi is already on the next day.
            loan = Loan(copy=self.copy, borrower_name="Date fixture", issue_date=today)
            loan.clean()
            for returned_date in (today - timedelta(days=1), today + timedelta(days=1)):
                loan.returned_date = returned_date
                with self.assertRaises(ValidationError):
                    loan.clean()

    def test_snapshot_availability_tracks_issue_and_return(self):
        def available():
            records = json.loads(snapshot_bytes())["editions"]
            return records[0]["copies"][0]["available"]

        self.assertTrue(available())
        self.client.post("/librarian/loans/issue/", self.payload())
        self.assertFalse(available())
        self.client.post(reverse("librarian:return", args=[Loan.objects.get().pk]))
        self.assertTrue(available())

    def test_issue_search_and_signed_token_validation(self):
        response = self.client.get("/librarian/loans/issue/", {"q": self.copy.accession})
        self.assertEqual(list(response.context["form"].fields["copy"].queryset), [self.copy])
        self.client.post("/librarian/loans/issue/", self.payload(token="invalid"))
        self.assertEqual(Loan.objects.count(), 0)
        self.assertEqual(Submission.objects.count(), 0)

    def test_constraint_and_receipt_transaction_rollback(self):
        Loan.objects.create(copy=self.copy, borrower_name="Existing")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Loan.objects.create(copy=self.copy, borrower_name="Duplicate")
        with patch("catalog.lending.Loan.objects.create", side_effect=IntegrityError("fixture")):
            self.client.post("/librarian/loans/issue/", self.payload(copy=self.hidden.pk))
        self.assertEqual(Submission.objects.count(), 0)
        self.assertFalse(Loan.objects.filter(copy=self.hidden).exists())

    def test_overdue_search_pagination(self):
        Loan.objects.create(
            copy=self.copy,
            borrower_name="Overdue fixture",
            issue_date=timezone.localdate() - timedelta(days=3),
            due_date=timezone.localdate() - timedelta(days=1),
        )
        Loan.objects.create(copy=self.hidden, borrower_name="No due date")
        response = self.client.get("/librarian/loans/", {"overdue": "1", "q": "Overdue"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertNotContains(response, "No due date")
        for index in range(21):
            copy = Copy.objects.create(edition=self.book, shelf=self.shelf)
            Loan.objects.create(copy=copy, borrower_name=f"Pagination {index}")
        self.assertEqual(len(self.client.get("/librarian/loans/").context["page_obj"]), 20)
        self.assertEqual(len(self.client.get("/librarian/loans/?page=2").context["page_obj"]), 3)

    def test_public_privacy_and_stable_urls(self):
        self.client.post("/librarian/loans/issue/", self.payload())
        url = copy_url(self.copy)
        self.book.title = "Changed title"
        self.book.save()
        self.shelf.label = "Changed shelf"
        self.shelf.save()
        self.assertEqual(copy_url(self.copy), url)
        for language in ["en", "ur", "ar"]:
            self.client.cookies["django_language"] = language
            response = self.client.get(url)
            self.assertContains(response, "Changed title")
            self.assertContains(response, "Changed shelf")
            self.assertNotContains(response, "PRIVATE")
        for path in ["/", "/books/?q=PRIVATE", f"/books/{self.book.pk}/", "/librarian/public-catalog.csv"]:
            self.assertNotIn(b"PRIVATE FICTIONAL BORROWER", self.client.get(path).content)
            self.assertNotIn(b"PRIVATE CONTACT", self.client.get(path).content)
        self.assertNotIn(b"PRIVATE", snapshot_bytes())
        self.assertEqual(self.client.get(copy_url(self.hidden)).status_code, 404)
        self.assertEqual(self.client.get("/copies/RL-999999/").status_code, 404)

    def test_whatsapp_settings_encoding_and_translations(self):
        with override_settings(WHATSAPP_NUMBER=""):
            self.assertEqual(whatsapp_url(self.copy), "")
        for number in ["abc", "0123456789", "+123", "https://evil.test", "+1234567890123456"]:
            with override_settings(WHATSAPP_NUMBER=number):
                self.assertEqual(whatsapp_url(self.copy), "")
        library = LibrarySettings.objects.create(whatsapp_number="+92 (300) 123-4567")
        for code in ["en", "ur", "ar"]:
            with translation.override(code):
                url = whatsapp_url(self.copy)
                parts = urlsplit(url)
                self.assertEqual(parts.netloc, "wa.me")
                self.assertEqual(parts.path, "/923001234567")
                text = parse_qs(parts.query)["text"][0]
                for value in [self.book.title, self.copy.accession, self.copy.volume, copy_url(self.copy)]:
                    self.assertIn(value, text)
                self.assertIn(LABELS["enquiry_message"][["en", "ur", "ar"].index(code)].split("{")[0], text)
        library.whatsapp_number = "invalid"
        library.save()
        self.assertNotContains(self.client.get(copy_url(self.copy)), "https://wa.me/")

    def test_canonical_url_validation_and_warnings(self):
        for value in [
            "",
            "javascript:alert(1)",
            "https://user:pass@example.org",
            "https://example.org/path",
            "https://example.org?x=1",
            "https://example.org#x",
        ]:
            with self.assertRaises(ImproperlyConfigured):
                canonical_site_url(value)
        self.assertEqual(canonical_site_url("https://example.org/"), "https://example.org")
        self.assertFalse(temporary_site())
        for value in ["http://localhost:8000", "https://preview.vercel.app", "http://192.168.1.5:8000"]:
            with override_settings(SITE_URL=value):
                self.assertTrue(temporary_site())
        self.assertEqual(copy_url(self.copy), f"https://library.example.org/copies/{self.copy.accession}/")

    def test_labels_bounds_filter_content_and_no_private_records(self):
        self.client.post("/librarian/loans/issue/", self.payload())
        with patch("catalog.lending.segno.make_qr", wraps=segno.make_qr) as qr:
            response = self.client.post("/librarian/labels/", {"copies": [self.copy.pk]})
            qr.assert_called_once_with(copy_url(self.copy), error="m")
        self.assertContains(response, "<svg")
        self.assertContains(response, 'viewBox="0 0 ')
        self.assertContains(response, copy_url(self.copy))
        self.assertContains(response, self.copy.volume)
        self.assertNotContains(response, "PRIVATE")
        self.assertIn("no-store", response["Cache-Control"])
        for selected in [
            [],
            [self.copy.pk] * 25,
            [self.copy.pk] * 2,
            [self.hidden.pk],
            ["999999"],
            ["not-a-number"],
        ]:
            self.assertContains(
                self.client.post("/librarian/labels/", {"copies": selected}), ui("label_bounds")
            )
        self.assertNotContains(self.client.get("/librarian/labels/?q=missing"), self.copy.accession)
        self.assertContains(self.client.get(f"/librarian/labels/?shelf={self.shelf.pk}"), self.copy.accession)

    def test_csv_encoding_escaping_formula_safety_and_only_public_rows(self):
        response = self.client.get("/librarian/public-catalog.csv")
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], self.book.title)
        self.assertEqual(rows[1][2], self.copy.volume)
        self.assertEqual(rows[1][-1], copy_url(self.copy))
        self.assertNotIn(self.hidden.accession, response.content.decode("utf-8-sig"))
        self.assertIn("no-store", response["Cache-Control"])
        for value in ["=1+1", "+CMD", "-123", "@SUM(A1)", " \t=1", "\ttext", "\rtext", "\ufeff=1"]:
            self.assertEqual(csv_safe(value), "'" + value)
        self.book.title = '=HYPERLINK("bad")'
        self.book.save()
        rows = list(
            csv.reader(
                io.StringIO(self.client.get("/librarian/public-catalog.csv").content.decode("utf-8-sig"))
            )
        )
        self.assertTrue(rows[1][1].startswith("'="))

    def test_private_routes_excluded_from_worker_allowlist(self):
        response = self.client.get("/offline/sw.js")
        script = response.content.decode()
        self.assertIn("if (request.method !== 'GET') return", script)
        self.assertIn("if (!ALLOWED.has(key)) return", script)
        for path in ["/librarian/loans/", "/librarian/labels/", "/librarian/public-catalog.csv"]:
            self.assertNotIn(path, script)

    def test_all_phase4_translations_present(self):
        for key, values in LABELS.items():
            self.assertEqual(len(values), 3)
            for code, text in zip(["en", "ur", "ar"], values, strict=True):
                with translation.override(code):
                    self.assertTrue(text.strip())
                    self.assertEqual(ui(key), text)
