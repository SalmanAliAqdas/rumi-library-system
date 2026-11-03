import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import (
    AccessionSequence,
    Category,
    Contribution,
    Contributor,
    Copy,
    Edition,
    Language,
    Loan,
    Shelf,
    Submission,
)
from catalog.workflows import create_copies, create_once, issue_token


class LibrarianTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_superuser("owner", password="test-fixture-only")
        cls.reader = get_user_model().objects.create_user("reader", password="test-fixture-only")
        cls.staff = get_user_model().objects.create_user("staff", is_staff=True, password="test-fixture-only")
        cls.shelf = Shelf.objects.create(label="Fixture A")
        cls.other_shelf = Shelf.objects.create(label="Fixture B")
        cls.category = Category.objects.create(slug="fixture", name="Fixture")
        cls.contributor = Contributor.objects.create(name="فرضی مصنف")
        cls.language = Language.objects.get_or_create(code="ur", defaults={"name": "اردو"})[0]
        Language.objects.get_or_create(code="en", defaults={"name": "English"})
        Language.objects.get_or_create(code="ar", defaults={"name": "العربية"})
        cls.book = Edition.objects.create(title="Fixture title")
        cls.copy = Copy.objects.create(edition=cls.book, shelf=cls.shelf)

    def setUp(self):
        self.client.force_login(self.owner)

    def book_data(self, **overrides):
        data = {
            "title": "باغِ علم · A garden",
            "original_language": "ur",
            "languages": [self.language.pk],
            "categories": [self.category.pk],
            "authors": [self.contributor.pk],
            "copy-shelf": self.shelf.pk,
            "copy-is_public": "on",
            "token": issue_token(self.owner, "edition:add"),
            "intent": "save",
        }
        data.update(overrides)
        return data

    def endpoints(self):
        paths = [
            reverse("librarian:" + name, args=args)
            for name, args in [
                ("dashboard", []),
                ("book_list", []),
                ("book_add", []),
                ("book_detail", [self.book.pk]),
                ("book_edit", [self.book.pk]),
                ("copy_add", [self.book.pk]),
                ("copy_edit", [self.copy.pk]),
                ("volumes", [self.book.pk]),
            ]
        ]
        for kind, record in [
            ("shelves", self.shelf),
            ("categories", self.category),
            ("contributors", self.contributor),
        ]:
            paths.extend(
                [
                    reverse("librarian:metadata_list", args=[kind]),
                    reverse("librarian:metadata_add", args=[kind]),
                    reverse("librarian:metadata_edit", args=[kind, record.pk]),
                ]
            )
        return paths

    def test_anonymous_and_unauthorized_direct_gets_and_posts(self):
        for user, expected in [(None, 302), (self.reader, 403), (self.staff, 403)]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for path in self.endpoints():
                self.assertEqual(self.client.get(path).status_code, expected, (user, path))
                # Read-only endpoints may return 405 before authentication; they cannot mutate.
                result = self.client.post(path, self.book_data()).status_code
                self.assertIn(result, [expected, 405], (user, path))
        self.assertEqual(Edition.objects.count(), 1)
        self.assertEqual(Copy.objects.count(), 1)

    def test_staff_needs_specific_model_permissions(self):
        self.staff.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_edition", "view_copy"])
        )
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("librarian:book_list")).status_code, 200)
        self.assertEqual(self.client.post(reverse("librarian:book_add"), self.book_data()).status_code, 403)
        self.assertEqual(self.client.get(reverse("librarian:dashboard")).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("librarian:copy_edit", args=[self.copy.pk]), {"shelf": self.other_shelf.pk}
            ).status_code,
            403,
        )

    def test_owner_can_read_every_screen_without_get_writes(self):
        before = (Edition.objects.count(), Copy.objects.count(), Submission.objects.count())
        for path in self.endpoints():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(before, (Edition.objects.count(), Copy.objects.count(), Submission.objects.count()))

    def test_login_logout_and_csrf(self):
        self.client.logout()
        response = self.client.post(
            reverse("librarian:login"), {"username": "reader", "password": "test-fixture-only"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(
            reverse("librarian:login"),
            {"username": "owner", "password": "test-fixture-only", "next": "https://untrusted.example/"},
        )
        self.assertRedirects(response, reverse("librarian:dashboard"))
        self.assertEqual(self.client.get(reverse("librarian:logout")).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner)
        self.assertEqual(strict.post(reverse("librarian:book_add"), self.book_data()).status_code, 403)
        self.assertEqual(strict.post(reverse("librarian:logout")).status_code, 403)
        self.assertRedirects(self.client.post(reverse("librarian:logout")), reverse("librarian:login"))

    def test_dashboard_counts(self):
        Copy.objects.create(edition=self.book, shelf=self.shelf, is_public=False)
        Loan.objects.create(copy=self.copy, borrower_name="PRIVATE FIXTURE")
        response = self.client.get(reverse("librarian:dashboard"))
        for key, expected in [
            ("edition_count", 1),
            ("copy_count", 2),
            ("available_count", 1),
            ("loan_count", 1),
        ]:
            self.assertEqual(response.context[key], expected)
        self.assertNotContains(response, "PRIVATE FIXTURE")

    def test_create_multilingual_book_and_roles_atomically(self):
        data = self.book_data(
            translators=[self.contributor.pk],
            aliases="Bagh\nGarden",
            languages=[self.language.pk, Language.objects.get(code="en").pk],
        )
        response = self.client.post(reverse("librarian:book_add"), data)
        self.assertEqual(response.status_code, 302)
        book = Edition.objects.get(title=data["title"])
        self.assertEqual(book.languages.count(), 2)
        self.assertEqual(set(book.credits.values_list("role", flat=True)), {"author", "translator"})
        copy = book.copies.get()
        self.assertEqual(copy.shelf, self.shelf)
        self.assertRegex(copy.accession, r"RL-\d{6}")
        self.assertContains(self.client.get(response.url), copy.accession)
        self.assertEqual(Submission.objects.count(), 1)

    def test_invalid_form_retains_draft_without_partial_saves(self):
        for override in [
            {"copy-shelf": ""},
            {"title": ""},
            {"languages": []},
            {"authors": []},
            {"cover_url": "not-url"},
        ]:
            response = self.client.post(reverse("librarian:book_add"), self.book_data(**override))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["form"].data["aliases"]
                if "aliases" in response.context["form"].data
                else "",
                "",
            )
            self.assertEqual(Edition.objects.count(), 1)
            self.assertEqual(Copy.objects.count(), 1)
            self.assertEqual(Submission.objects.count(), 0)
            self.assertTrue(response.context["form"].errors or response.context["copy_form"].errors)

    def test_unknown_author_does_not_create_fake_person(self):
        data = self.book_data(authors=[], unknown_author="on")
        self.assertEqual(self.client.post(reverse("librarian:book_add"), data).status_code, 302)
        self.assertEqual(Edition.objects.get(title=data["title"]).credits.count(), 0)
        self.assertEqual(Contributor.objects.count(), 1)

    def test_save_another_and_remember_only_success(self):
        response = self.client.post(reverse("librarian:book_add"), self.book_data(intent="another"))
        self.assertRedirects(response, reverse("librarian:book_add"))
        response = self.client.get(reverse("librarian:book_add"))
        self.assertEqual(response.context["copy_form"].initial["shelf"], self.shelf.pk)
        self.assertEqual(response.context["form"].initial["categories"], [self.category.pk])
        self.client.post(
            reverse("librarian:book_add"), self.book_data(title="", **{"copy-shelf": self.other_shelf.pk})
        )
        self.assertEqual(self.client.session["last_shelf"], self.shelf.pk)

    def test_refresh_choices_keeps_draft_and_does_not_write(self):
        person = Contributor.objects.create(name="New contributor")
        data = self.book_data(intent="refresh", aliases="Private draft alias", title="Still a draft")
        response = self.client.post(reverse("librarian:book_add"), data)
        self.assertContains(response, "Still a draft")
        self.assertContains(response, "Private draft alias")
        self.assertIn(person, response.context["form"].fields["authors"].queryset)
        self.assertFalse(response.context["form"].errors)
        self.assertEqual(Edition.objects.count(), 1)

    def test_edits_have_separate_scopes(self):
        second = Copy.objects.create(edition=self.book, shelf=self.shelf)
        data = self.book_data(title="Changed edition")
        response = self.client.post(reverse("librarian:book_edit", args=[self.book.pk]), data)
        self.assertEqual(response.status_code, 302)
        for copy in [self.copy, second]:
            copy.refresh_from_db()
            self.assertEqual(copy.edition.title, "Changed edition")
        response = self.client.post(
            reverse("librarian:copy_edit", args=[self.copy.pk]),
            {"shelf": self.other_shelf.pk, "volume": "II", "is_public": "on", "accession": "forged"},
        )
        self.assertEqual(response.status_code, 302)
        self.copy.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.copy.shelf, self.other_shelf)
        self.assertEqual(second.shelf, self.shelf)
        self.assertNotEqual(self.copy.accession, "forged")

    def test_duplicate_create_posts_create_one_book_or_copy(self):
        data = self.book_data()
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("librarian:book_add"), data).status_code, 302)
        self.assertEqual(Edition.objects.count(), 2)
        data = {
            "shelf": self.shelf.pk,
            "is_public": "on",
            "token": issue_token(self.owner, f"copy:add:{self.book.pk}"),
        }
        for _ in range(2):
            self.assertEqual(
                self.client.post(reverse("librarian:copy_add", args=[self.book.pk]), data).status_code, 302
            )
        self.assertEqual(self.book.copies.count(), 2)

    def test_tokens_are_user_action_scoped_and_required(self):
        for token in [
            "",
            "forged",
            issue_token(self.reader, "edition:add"),
            issue_token(self.owner, "other-action"),
        ]:
            self.assertEqual(
                self.client.post(reverse("librarian:book_add"), self.book_data(token=token)).status_code, 200
            )
        self.assertEqual(Edition.objects.count(), 1)

    def volume_data(self, **overrides):
        data = {
            "start": 1,
            "end": 3,
            "shelf": self.shelf.pk,
            "is_public": "on",
            "token": issue_token(self.owner, f"volumes:add:{self.book.pk}"),
            "intent": "preview",
        }
        data.update(overrides)
        return data

    def preview_data(self, data):
        response = self.client.post(reverse("librarian:volumes", args=[self.book.pk]), data)
        self.assertTrue(response.context["preview"])
        return response.context["form"].data.copy()

    def test_volume_preview_edit_labels_confirm_and_replay(self):
        data = self.preview_data(self.volume_data())
        self.assertEqual(self.book.copies.count(), 1)
        data["labels"] = "جلد اول\nII\nالثالث"
        data["intent"] = "confirm"
        for _ in range(2):
            self.assertEqual(
                self.client.post(reverse("librarian:volumes", args=[self.book.pk]), data).status_code, 302
            )
        self.assertEqual(self.book.copies.count(), 4)
        self.assertEqual(len(set(self.book.copies.values_list("accession", flat=True))), 4)
        self.assertEqual(
            list(self.book.copies.order_by("pk").values_list("volume", flat=True)),
            ["", "جلد اول", "II", "الثالث"],
        )

    def test_invalid_batches_and_preview_bypass(self):
        for changes in [
            {"end": 26},
            {"end": 0},
            {"start": 4, "end": 3},
            {"labels": "I\nI\nIII"},
            {"labels": "x" * 81 + "\nII\nIII"},
            {"labels": "I\nIII"},
            {"intent": "confirm", "labels": "I\nII\nIII"},
        ]:
            response = self.client.post(
                reverse("librarian:volumes", args=[self.book.pk]), self.volume_data(**changes)
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(Copy.objects.count(), 1)

    def test_batch_failure_rolls_back_copies_receipt_and_counter(self):
        original_save = Copy.save
        initial_counter = AccessionSequence.objects.get(pk=1).value

        def failing_save(copy, *args, **kwargs):
            if copy.volume == "2":
                raise ValidationError("Injected fixture failure")
            return original_save(copy, *args, **kwargs)

        with patch.object(Copy, "save", failing_save), self.assertRaises(ValidationError):
            create_once(
                self.owner,
                "fixture",
                uuid.uuid4(),
                lambda: create_copies(self.book, self.shelf, ["1", "2", "3"], True),
            )
        self.assertEqual(Copy.objects.count(), 1)
        self.assertEqual(Submission.objects.count(), 0)
        self.assertEqual(AccessionSequence.objects.get(pk=1).value, initial_counter)

    def test_book_failure_rolls_back_edition_and_credits(self):
        with (
            patch.object(Copy, "save", side_effect=ValidationError("Injected failure")),
            self.assertRaises(ValidationError),
        ):
            self.client.post(reverse("librarian:book_add"), self.book_data())
        self.assertEqual(Edition.objects.count(), 1)
        self.assertEqual(Contribution.objects.count(), 0)
        self.assertEqual(Submission.objects.count(), 0)

    def test_active_loan_copy_cannot_be_hidden_or_deleted(self):
        Loan.objects.create(copy=self.copy, borrower_name="Private fixture")
        response = self.client.post(
            reverse("librarian:copy_edit", args=[self.copy.pk]), {"shelf": self.shelf.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("is_public", response.context["form"].errors)
        self.copy.refresh_from_db()
        self.assertTrue(self.copy.is_public)
        with self.assertRaises(ProtectedError):
            self.copy.delete()

    def test_referenced_metadata_deletion_is_protected(self):
        self.book.categories.add(self.category)
        self.book.languages.add(self.language)
        Contribution.objects.create(edition=self.book, contributor=self.contributor)
        for record in [self.shelf, self.category, self.language, self.contributor]:
            with transaction.atomic(), self.assertRaises(ProtectedError):
                type(record).objects.filter(pk=record.pk).delete()

    def test_metadata_add_edit_search_and_empty_shelf(self):
        for kind, data, model in [
            ("shelves", {"label": "خالی شیلف", "description": "Empty", "display_order": 9}, Shelf),
            ("categories", {"slug": "new", "name": "New", "name_ur": "نیا", "name_ar": "جديد"}, Category),
            ("contributors", {"name": "كاتب جديد"}, Contributor),
        ]:
            response = self.client.post(reverse("librarian:metadata_add", args=[kind]), data)
            self.assertEqual(response.status_code, 302)
            record = model.objects.latest("pk")
            response = self.client.post(reverse("librarian:metadata_edit", args=[kind, record.pk]), data)
            self.assertEqual(response.status_code, 302)
            query = data.get("label") or data["name"]
            response = self.client.get(reverse("librarian:metadata_list", args=[kind]), {"q": query})
            self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_translated_forms_and_labels(self):
        for code, text in [("en", "Add a book"), ("ur", "کتاب شامل کریں"), ("ar", "إضافة كتاب")]:
            self.client.cookies["django_language"] = code
            response = self.client.get(reverse("librarian:book_add"))
            self.assertContains(response, text)
            self.assertContains(response, f'lang="{code}"')
            self.assertContains(response, 'dir="ltr"' if code == "en" else 'dir="rtl"')
