import json
import struct
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings

from catalog.models import (
    Category,
    Contribution,
    Contributor,
    Copy,
    Edition,
    Language,
    LibrarySettings,
    Loan,
    Shelf,
)
from catalog.offline_labels import LABELS
from catalog.search import normalize
from catalog.templatetags.library_ui import ui

FIXTURES = Path(__file__).parent / "fixtures" / "search_parity.json"


class SnapshotTests(TransactionTestCase):
    def setUp(self):
        self.shelf = Shelf.objects.create(label="Public shelf", description="PRIVATE SHELF DESCRIPTION")
        self.book = Edition.objects.create(
            title="بُخَاری · Fictional",
            aliases="Bukhari",
            summary="Public summary",
            isbn="978-123",
            is_demo=True,
        )
        self.copy = Copy.objects.create(edition=self.book, shelf=self.shelf)
        self.hidden = Copy.objects.create(edition=self.book, shelf=self.shelf, is_public=False)
        hidden_edition = Edition.objects.create(title="HIDDEN EDITION")
        Copy.objects.create(edition=hidden_edition, shelf=self.shelf, is_public=False)
        self.book.categories.add(
            Category.objects.create(slug="public", name="Public", name_ur="عوامی", name_ar="عام")
        )
        self.book.languages.add(Language.objects.get_or_create(code="ur", defaults={"name": "اردو"})[0])
        Contribution.objects.create(
            edition=self.book,
            contributor=Contributor.objects.create(name="Fictional Writer"),
            role="translator",
        )
        Loan.objects.create(copy=self.copy, borrower_name="PRIVATE BORROWER", contact="PRIVATE CONTACT")
        LibrarySettings.objects.create(whatsapp_number="PRIVATE WHATSAPP", description="PRIVATE SETTINGS")

    def snapshot(self):
        return self.client.get("/catalog/public-snapshot.json")

    def test_public_snapshot_allowlist_privacy_and_counts(self):
        response = self.snapshot()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual((data["edition_count"], data["copy_count"]), (1, 1))
        book = data["editions"][0]
        self.assertEqual(
            set(book),
            {
                "id",
                "title",
                "original_language",
                "aliases",
                "contributors",
                "languages",
                "categories",
                "isbn",
                "publisher",
                "edition",
                "year",
                "summary",
                "cover_url",
                "is_demo",
                "url",
                "copies",
                "search",
            },
        )
        self.assertEqual(set(book["copies"][0]), {"accession", "volume", "shelf", "available"})
        self.assertFalse(book["copies"][0]["available"])
        self.assertEqual(book["search"]["title"], normalize(self.book.title))
        self.assertEqual(book["url"], f"/books/{self.book.pk}/")
        for private in [
            "PRIVATE BORROWER",
            "PRIVATE CONTACT",
            "PRIVATE WHATSAPP",
            "PRIVATE SETTINGS",
            "PRIVATE SHELF DESCRIPTION",
            "HIDDEN EDITION",
            self.hidden.accession,
            "borrower",
            "loan_id",
            "contact",
            "user_id",
        ]:
            self.assertNotContains(response, private)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("Set-Cookie", response)

    def test_authenticated_export_is_not_personalized(self):
        user = get_user_model().objects.create_superuser("PRIVATE STAFF", password="fixture-only")
        self.client.force_login(user)
        response = self.snapshot()
        self.assertNotContains(response, "PRIVATE STAFF")
        self.assertNotContains(response, "csrfmiddlewaretoken")

    def test_export_is_complete_and_not_filtered_by_search(self):
        for index in range(18):
            book = Edition.objects.create(title=f"Unvisited {index}")
            Copy.objects.create(edition=book, shelf=self.shelf)
        response = self.client.get("/catalog/public-snapshot.json?q=absent&page=2&language=en")
        self.assertEqual(response.json()["edition_count"], 19)

    def test_snapshot_safety_limits_fail_without_partial_records(self):
        for setting, value in [
            ("OFFLINE_MAX_EDITIONS", 0),
            ("OFFLINE_MAX_COPIES", 0),
            ("OFFLINE_MAX_BYTES", 10),
        ]:
            with override_settings(**{setting: value}):
                response = self.snapshot()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error"], "snapshot_limit_exceeded")
                self.assertNotIn("editions", response.json())

    def test_only_safe_methods(self):
        for path in ["/offline/", "/offline/sw.js", "/catalog/public-snapshot.json"]:
            self.assertEqual(self.client.post(path).status_code, 405)

    def test_shell_is_generic_and_has_no_auth_or_csrf_content(self):
        self.client.force_login(
            get_user_model().objects.create_superuser("PRIVATE STAFF", password="fixture-only")
        )
        response = self.client.get("/offline/")
        for private in ["csrfmiddlewaretoken", "PRIVATE STAFF", "PRIVATE SETTINGS", "/admin/", "/librarian/"]:
            self.assertNotContains(response, private)
        self.assertContains(response, 'href="/static/offline/manifest.webmanifest"')
        self.assertIn("object-src 'none'", response["Content-Security-Policy"])
        self.assertFalse(response.cookies)

    def test_worker_allowlist_and_no_forced_takeover(self):
        response = self.client.get("/offline/sw.js")
        text = response.content.decode()
        self.assertIn("request.method !== 'GET'", text)
        self.assertIn("ALLOWED.has(key)", text)
        self.assertNotIn("self.skipWaiting(", text)
        self.assertNotIn("clients.claim(", text)
        start = text.index("const ASSETS = ") + len("const ASSETS = ")
        assets = json.loads(text[start : text.index(";", start)])
        self.assertIn("/offline/", assets)
        self.assertTrue(all(path == "/offline/" or path.startswith("/static/") for path in assets))
        self.assertFalse(
            any("/admin/" in path or "/librarian/" in path or "snapshot" == path for path in assets)
        )

    def test_manifest_icons_scope_and_install_metadata(self):
        root = Path(__file__).parent.parent / "static" / "offline"
        manifest = json.loads((root / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["start_url"], "/offline/")
        self.assertEqual(manifest["scope"], "/offline/")
        self.assertEqual(manifest["display"], "standalone")
        for icon in manifest["icons"]:
            content = (root / Path(icon["src"]).name).read_bytes()
            self.assertEqual(content[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", content[16:24])
            self.assertEqual(icon["sizes"], f"{width}x{height}")


class ParityFixtureTests(TestCase):
    def test_python_normalization_and_online_ranking_share_fixtures(self):
        fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
        for source, expected in fixtures["normalization"]:
            self.assertEqual(normalize(source), expected)
        shelf = Shelf.objects.create(label="Parity fixture")
        for source in fixtures["books"]:
            book = Edition.objects.create(**source)
            Copy.objects.create(edition=book, shelf=shelf)
        for query, expected in fixtures["ranking"]:
            response = self.client.get("/books/", {"q": query})
            self.assertEqual([book.pk for book in response.context["page_obj"]], expected, query)

    def test_offline_labels_exist_in_all_three_languages(self):
        self.assertTrue(all(len(values) == 3 and all(values) for values in LABELS.values()))
        for key in LABELS:
            self.assertNotEqual(ui(key), key)
