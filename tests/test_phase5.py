import io
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.management import call_command
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from catalog.metadata import LookupError, fetch, lookup, reserve_request, signed_result, suggestion
from catalog.models import Copy, Edition, Language, Loan, LookupGate, Shelf


class MetadataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_superuser("phase5", password="fixture-only")
        cls.book = Edition.objects.create(title="Manual title", publisher="Manual publisher")
        cls.shelf = Shelf.objects.create(label="Fixture")
        cls.copy = Copy.objects.create(edition=cls.book, shelf=cls.shelf)
        cls.loan = Loan.objects.create(copy=cls.copy, borrower_name="Private fixture")

    def setUp(self):
        self.client.force_login(self.owner)
        self.url = reverse("librarian:book_edit", args=[self.book.pk])
        self.result = suggestion(
            {
                "key": "/books/OL123M",
                "title": "Suggested · علم",
                "publishers": ["Provider"],
                "publish_date": "May 2001",
                "description": "<script>bad()</script><b>Text</b>",
                "covers": [123],
            }
        )

    def test_lookup_isbn_and_title_multilingual_bounded(self):
        with patch(
            "catalog.metadata.fetch",
            return_value={
                "ISBN:9780140328721": {
                    "details": {"key": "/books/OL123M", "title": "Book", "authors": [{"name": "Writer"}]}
                }
            },
        ) as provider:
            result = lookup({"lookup_isbn": "9780140328721"})
            self.assertEqual(result[0]["fields"]["isbn"], "9780140328721")
            self.assertEqual(result[0]["contributors"], ["Writer"])
            self.assertEqual(provider.call_args.args[0], "/api/books")
        for title in ["Knowledge", "علم", "معرفة"]:
            with patch(
                "catalog.metadata.fetch", return_value={"docs": [{"key": "/works/OL1W", "title": title}] * 20}
            ) as provider:
                result = lookup({"lookup_isbn": "", "lookup_title": title, "lookup_author": "كاتب"})
                self.assertEqual(len(result), 5)
                self.assertEqual(provider.call_args.args[1]["title"], title)

    def test_missing_malformed_and_untrusted_provider_fields(self):
        for record in [None, {}, {"key": "https://evil.test", "title": "bad"}, {"key": [1], "title": "bad"}]:
            self.assertIsNone(suggestion(record))
        self.assertNotIn("<", self.result["fields"]["summary"])
        result = suggestion(
            {
                "key": "/works/OL1W",
                "title": "<b>Title</b>",
                "covers": ["https://evil.test"],
                "publishers": {"bad": True},
            }
        )
        self.assertEqual(result["fields"]["cover_url"], "")
        self.assertEqual(result["fields"]["title"], "Title")
        with patch("catalog.metadata.fetch", return_value={"docs": None}), self.assertRaises(LookupError):
            lookup({"lookup_isbn": "", "lookup_title": "Book", "lookup_author": ""})

    def test_timeouts_rate_limits_redirects_and_byte_bounds(self):
        from urllib.error import HTTPError

        for error in [TimeoutError(), HTTPError("https://openlibrary.org", 429, "busy", {}, None)]:
            with patch("catalog.metadata.reserve_request"), patch("catalog.metadata.build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaises(LookupError):
                    fetch("/search.json")
        for chunks in [[b"x" * (512 * 1024 + 1)], [b"not-json", b""]]:
            with patch("catalog.metadata.reserve_request"), patch("catalog.metadata.build_opener") as opener:
                response = MagicMock()
                response.read.side_effect = chunks
                opener.return_value.open.return_value.__enter__.return_value = response
                with self.assertRaises(LookupError):
                    fetch("/search.json")
        from catalog.metadata import NoRedirect

        with self.assertRaises(LookupError):
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test")

    def test_shared_gate(self):
        reserve_request()
        with self.assertRaises(LookupError):
            reserve_request()
        self.assertEqual(LookupGate.objects.count(), 1)

    def test_preview_preserves_draft_and_never_saves_inventory(self):
        with patch("catalog.metadata.lookup", return_value=[self.result]):
            response = self.client.post(
                self.url, {"intent": "lookup", "lookup_title": "Book", "title": "Draft", "publisher": "Mine"}
            )
        self.assertEqual(response.context["form"]["title"].value(), "Draft")
        self.assertContains(response, "Open Library")
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Manual title")
        self.assertEqual(Copy.objects.count(), 1)
        self.assertEqual(Loan.objects.count(), 1)

    def test_approval_replacement_confirmation_and_attribution(self):
        token = signed_result(self.result, self.owner)
        data = {
            "intent": "apply_metadata",
            "suggestion": token,
            "approve": ["title", "summary", "copy-shelf"],
            "title": "Manual title",
            "publisher": "Manual publisher",
            "copy-shelf": "123",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.context["form"]["title"].value(), "Manual title")
        data["replace_confirm"] = "on"
        response = self.client.post(self.url, data)
        self.assertEqual(response.context["form"]["title"].value(), self.result["fields"]["title"])
        self.assertEqual(response.context["form"]["publisher"].value(), "Manual publisher")
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Manual title")
        language = Language.objects.get(code="en")
        response = self.client.post(
            self.url,
            {
                "intent": "save",
                "title": self.result["fields"]["title"],
                "publisher": "Manual publisher",
                "summary": self.result["fields"]["summary"],
                "metadata_token": token,
                "original_language": "en",
                "languages": [language.pk],
                "unknown_author": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.assertEqual(self.book.metadata_source, self.result["source"])
        self.assertIsNotNone(self.book.metadata_retrieved_at)
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.shelf, self.shelf)
        self.assertEqual(Loan.objects.get().borrower_name, "Private fixture")

    def test_unselected_fields_and_expired_or_wrong_user_tokens(self):
        token = signed_result(self.result, self.owner)
        response = self.client.post(
            self.url,
            {"intent": "apply_metadata", "suggestion": token, "title": "Mine", "approve": ["summary"]},
        )
        self.assertEqual(response.context["form"]["title"].value(), "Mine")
        for value in [
            token + "bad",
            signing.dumps({"user": -1, "result": self.result}, salt="rumi-metadata-v1"),
        ]:
            response = self.client.post(
                self.url, {"intent": "apply_metadata", "suggestion": value, "title": "Mine"}
            )
            self.assertEqual(response.context["form"]["title"].value(), "Mine")

    def test_authorization_csrf_and_public_browsing_never_calls_provider(self):
        self.client.logout()
        with patch("catalog.metadata.lookup") as provider:
            self.assertEqual(self.client.post(self.url, {"intent": "lookup"}).status_code, 302)
            self.client.get("/")
            self.client.get(f"/books/{self.book.pk}/")
            provider.assert_not_called()
        staff = get_user_model().objects.create_user("limited", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.url, {"intent": "lookup"}).status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url, {"intent": "lookup"}).status_code, 403)

    def test_empty_outage_and_invalid_input_recovery(self):
        for result, error in [([], None), (None, LookupError())]:
            with patch("catalog.metadata.lookup", return_value=result, side_effect=error):
                response = self.client.post(
                    self.url, {"intent": "lookup", "lookup_title": "Book", "title": "Draft"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["form"]["title"].value(), "Draft")
        with patch("catalog.metadata.lookup") as provider:
            self.client.post(self.url, {"intent": "lookup", "lookup_isbn": "bad"})
            provider.assert_not_called()


@override_settings(SITE_URL="https://library.example.org")
class LaunchTests(TestCase):
    def test_sitemap_page_boundaries_and_error_log_privacy(self):
        import logging
        from xml.etree import ElementTree

        book = Edition.objects.create(title="Pagination fixture")
        shelf = Shelf.objects.create(label="Sitemap fixture")
        for _ in range(1001):
            Copy.objects.create(edition=book, shelf=shelf)
        pages = [
            ElementTree.fromstring(self.client.get(f"/sitemap.xml?page={page}").content) for page in [1, 2]
        ]
        self.assertEqual([len(page) for page in pages], [1000, 4])
        self.assertEqual(self.client.get("/sitemap.xml?page=3").status_code, 404)
        logger = logging.getLogger("django.request")
        handler = logger.handlers[0]
        stream = io.StringIO()
        previous = handler.setStream(stream)
        try:
            try:
                raise ValueError("Private borrower fixture")
            except ValueError:
                logger.exception("postgresql://private-credential-fixture")
            try:
                raise ValueError("certificate verify failed: Private borrower fixture")
            except ValueError:
                logger.exception("postgresql://private-credential-fixture")
            self.assertIn("ERROR", stream.getvalue())
            self.assertIn("tls_verification", stream.getvalue())
            self.assertNotIn("Private borrower", stream.getvalue())
            self.assertNotIn("private-credential", stream.getvalue())
        finally:
            handler.setStream(previous)

    def test_public_sitemap_canonical_headers_and_no_private_data(self):
        shelf = Shelf.objects.create(label="Fixture")
        book = Edition.objects.create(title="Public book", summary="Public summary")
        hidden_book = Edition.objects.create(title="Private book")
        copy = Copy.objects.create(edition=book, shelf=shelf)
        hidden = Copy.objects.create(edition=hidden_book, shelf=shelf, is_public=False)
        Loan.objects.create(copy=copy, borrower_name="Secret borrower", contact="Secret contact")
        response = self.client.get("/sitemap.xml?page=1")
        self.assertContains(response, f"https://library.example.org/books/{book.pk}/")
        self.assertNotContains(response, f"/books/{hidden_book.pk}/")
        self.assertNotContains(response, hidden.accession)
        self.assertNotContains(response, "librarian")
        response = self.client.get(f"/books/{book.pk}/", HTTP_HOST="localhost")
        self.assertContains(response, f'rel="canonical" href="https://library.example.org/books/{book.pk}/"')
        self.assertContains(response, 'property="og:image"')
        self.assertNotContains(response, "Secret borrower")
        self.assertEqual(self.client.get("/books/?q=book")["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(self.client.get("/librarian/login/")["Cache-Control"], "private, no-store")
        self.assertContains(self.client.get("/robots.txt"), "https://library.example.org/sitemap.xml")

    def test_login_throttle_shared_database_and_health(self):
        for _ in range(10):
            self.assertEqual(self.client.post("/librarian/login/", {"username": "none"}).status_code, 200)
        response = Client().post("/admin/login/", {"username": "none"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "300")
        with self.assertNumQueries(0):
            self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})

    def test_database_independent_error_page(self):
        from catalog.views import server_error

        response = server_error(None)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"try again", response.content)

    def test_production_settings_fail_safe_and_connection_policy(self):
        base = {
            **os.environ,
            "DJANGO_ENV": "production",
            "SECRET_KEY": "x7!" * 24,
            "DATABASE_URL": "postgresql://placeholder:placeholder@db.example.org/rumi",
            "ALLOWED_HOSTS": "library.example.org",
            "CSRF_TRUSTED_ORIGINS": "https://library.example.org",
            "SITE_URL": "https://library.example.org",
            "VERCEL": "1",
        }
        code = "from config import settings as s; assert not s.DEBUG; assert s.DATABASES['default']['CONN_MAX_AGE'] == 0; assert s.DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS']; assert s.DATABASES['default']['OPTIONS']['sslmode'] == 'verify-full'"
        self.assertEqual(
            subprocess.run([sys.executable, "-c", code], env=base, capture_output=True).returncode, 0
        )
        for overrides in [
            {"SECRET_KEY": ""},
            {"DATABASE_URL": ""},
            {"DATABASE_URL": "sqlite:///db.sqlite3"},
            {"SITE_URL": "https://user:pass@host.test"},
            {"ALLOWED_HOSTS": "*.example.org"},
            {"CSRF_TRUSTED_ORIGINS": "https://*.example.org"},
        ]:
            self.assertNotEqual(
                subprocess.run(
                    [sys.executable, "-c", code], env={**base, **overrides}, capture_output=True
                ).returncode,
                0,
                overrides,
            )


class TransferAuditTests(TransactionTestCase):
    def test_read_only_audit_and_fixture_round_trip(self):
        from django.core import serializers

        shelf = Shelf.objects.create(label="Transfer fixture")
        book = Edition.objects.create(title="علم", metadata_source="https://openlibrary.org/books/OL1M")
        copy = Copy.objects.create(edition=book, shelf=shelf, is_public=False)
        Loan.objects.create(copy=copy, borrower_name="Private fixture")
        book.languages.add(Language.objects.get_or_create(code="ur", defaults={"name": "اردو"})[0])
        before = io.StringIO()
        call_command("audit_catalog", stdout=before)
        fixture = io.StringIO()
        call_command(
            "dumpdata",
            "catalog",
            exclude=["catalog.submission", "catalog.lookupgate"],
            use_natural_foreign_keys=True,
            use_natural_primary_keys=True,
            stdout=fixture,
        )
        for record in serializers.deserialize("json", fixture.getvalue()):
            record.save()
        after = io.StringIO()
        call_command("audit_catalog", stdout=after)
        self.assertEqual(json.loads(before.getvalue()), json.loads(after.getvalue()))
        self.assertNotIn("Private fixture", before.getvalue())
