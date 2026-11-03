from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Contribution, Contributor, Copy, Edition, Language, Loan, Shelf


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.shelf = Shelf.objects.create(label="A")
        cls.book = Edition.objects.create(title="Quiet gardens", aliases="Bagh", isbn="123456")
        cls.book.languages.add(Language.objects.create(code="ur", name="اردو"))
        cls.category = Category.objects.create(slug="nature", name="Nature")
        cls.book.categories.add(cls.category)
        Contribution.objects.create(
            edition=cls.book, contributor=Contributor.objects.create(name="Fictional Writer")
        )
        cls.copy = Copy.objects.create(edition=cls.book, shelf=cls.shelf)
        cls.hidden_copy = Copy.objects.create(edition=cls.book, shelf=cls.shelf, is_public=False)
        cls.secret = Edition.objects.create(title="Private title")
        Copy.objects.create(edition=cls.secret, shelf=cls.shelf, is_public=False)
        Loan.objects.create(copy=cls.copy, borrower_name="PRIVATE BORROWER", contact="PRIVATE CONTACT")

    def test_public_visibility_and_counts(self):
        response = self.client.get("/")
        self.assertEqual(response.context["edition_count"], 1)
        self.assertEqual(response.context["copy_count"], 1)
        self.assertNotContains(response, "Private title")
        self.assertEqual(self.client.get(reverse("detail", args=[self.secret.pk])).status_code, 404)

    def test_detail_privacy_and_availability(self):
        response = self.client.get(reverse("detail", args=[self.book.pk]))
        self.assertContains(response, self.copy.accession)
        self.assertContains(response, "On loan")
        for private in [self.hidden_copy.accession, "PRIVATE BORROWER", "PRIVATE CONTACT"]:
            self.assertNotContains(response, private)
        self.assertFalse(self.copy.available)
        Loan.objects.filter(copy=self.copy).update(returned_date=date.today())
        self.assertTrue(self.copy.available)

    def test_basic_search(self):
        for query in ["Quiet", "Writer", "Nature", "Bagh", "123456", self.copy.accession]:
            response = self.client.get("/books/", {"q": query})
            self.assertEqual(response.context["page_obj"].paginator.count, 1, query)
        self.assertEqual(
            self.client.get("/books/", {"q": self.hidden_copy.accession}).context["page_obj"].paginator.count,
            0,
        )
        self.assertEqual(
            self.client.get("/books/", {"q": "Private title"}).context["page_obj"].paginator.count, 0
        )

    def test_filters(self):
        self.assertEqual(
            self.client.get("/books/", {"language": "ur", "category": "nature"})
            .context["page_obj"]
            .paginator.count,
            1,
        )
        self.assertEqual(
            self.client.get("/books/", {"language": "en"}).context["page_obj"].paginator.count, 0
        )

    def test_private_management(self):
        self.assertEqual(self.client.get("/admin/catalog/loan/").status_code, 302)
        user = get_user_model().objects.create_user("reader", password="test-only-password")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/catalog/edition/add/").status_code, 302)
        user.is_staff = True
        user.save()
        self.assertEqual(self.client.get("/admin/catalog/loan/").status_code, 403)

    def test_admin_superuser_can_access(self):
        user = get_user_model().objects.create_superuser("librarian", password="test-only-password")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/catalog/loan/").status_code, 200)

    def test_accessions_and_volumes(self):
        other = Copy.objects.create(edition=self.book, shelf=self.shelf, volume="II")
        self.assertNotEqual(other.accession, self.copy.accession)
        self.assertRegex(other.accession, r"^RL-\d{6}$")
        self.shelf.label = "Renamed"
        self.shelf.save()
        old_accession = other.accession
        other.refresh_from_db()
        self.assertEqual(other.accession, old_accession)
        other.accession = "RL-999999"
        with self.assertRaises(ValidationError):
            other.save()
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Copy.objects.filter(pk=other.pk).update(accession=self.copy.accession)

    def test_active_loan_database_constraint(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Loan.objects.create(copy=self.copy, borrower_name="Second")
        Loan.objects.filter(copy=self.copy).update(returned_date=date.today())
        Loan.objects.create(copy=self.copy, borrower_name="Next")

    def test_loan_date_constraints(self):
        for kwargs in [{"due_date": date(2020, 1, 1)}, {"returned_date": date(2020, 1, 1)}]:
            with transaction.atomic(), self.assertRaises(IntegrityError):
                Loan.objects.create(
                    copy=self.hidden_copy, borrower_name="Test", issue_date=date(2025, 1, 1), **kwargs
                )

    def test_deletion_protection_and_empty_shelves(self):
        with self.assertRaises(ProtectedError):
            self.shelf.delete()
        with self.assertRaises(ProtectedError):
            self.book.delete()
        Shelf.objects.create(label="Empty")
        self.assertEqual(Shelf.objects.get(label="Empty").copies.count(), 0)

    def test_language_switch_preserves_page_and_filters(self):
        response = self.client.post(
            "/i18n/setlang/", {"language": "ur", "next": "/books/?q=Quiet&category=nature"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/books/?q=Quiet&category=nature")
        response = self.client.get(response.url)
        self.assertContains(response, 'lang="ur" dir="rtl"')
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    @override_settings(DEBUG=True)
    def test_seed_is_explicit_and_idempotent(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Edition.objects.filter(is_demo=True).count(), 20)
        self.assertEqual(Copy.objects.filter(edition__is_demo=True).count(), 23)
        self.assertEqual(Copy.objects.filter(edition__demo_key="rumi-demo-08").count(), 3)
        self.assertEqual(Edition.objects.get(demo_key="rumi-demo-19").languages.count(), 2)

    @override_settings(DEBUG=False)
    def test_production_seed_refused(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("seed_demo")

    def test_pagination_and_empty_results(self):
        self.assertContains(self.client.get("/books/?q=nothing-matches"), "No books found")
        self.assertEqual(self.client.get("/books/?page=999").status_code, 200)


class EmptyCatalogTests(TestCase):
    def test_empty_welcome(self):
        self.assertContains(self.client.get("/"), "The shelves are waiting")
