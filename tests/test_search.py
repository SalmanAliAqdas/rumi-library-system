from django.test import SimpleTestCase, TestCase

from catalog.models import Category, Contribution, Contributor, Copy, Edition, Language, Loan, Shelf
from catalog.search import isbn_key, normalize


class NormalizationTests(SimpleTestCase):
    def test_documented_normalization(self):
        cases = [
            ("  A\tBOOK\n", "a book"),
            ("ＡＢＣ", "abc"),
            ("كِتَـاب ي", "کتاب ی"),
            ("بُخَارِی", "بخاری"),
            ("علم\u200cوفن", "علم وفن"),
            ("کتا\u200dب", "کتاب"),
            ("A Book · كِتَاب", "a book · کتاب"),
            ("Cafe\u0301", "café"),
        ]
        for value, expected in cases:
            self.assertEqual(normalize(value), expected)
            self.assertEqual(normalize(normalize(value)), expected)

    def test_retains_distinctions_and_no_transliteration(self):
        for left, right in [
            ("ة", "ه"),
            ("ے", "ی"),
            ("أ", "ا"),
            ("ى", "ی"),
            ("ؤ", "و"),
            ("é", "e"),
            ("Bukhari", "بخاری"),
        ]:
            self.assertNotEqual(normalize(left), normalize(right))
        self.assertEqual(isbn_key("978-1 234–56789-x"), "978123456789X")


class RankedSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.shelf = Shelf.objects.create(label="Search fixture")
        cls.language = Language.objects.get_or_create(code="ur", defaults={"name": "اردو"})[0]
        cls.category = Category.objects.create(
            slug="test-subject", name="Nature", name_ur="فطرت", name_ar="طبيعة"
        )

    def book(self, title, **kwargs):
        book = Edition.objects.create(title=title, **kwargs)
        book.languages.add(self.language)
        book.categories.add(self.category)
        Copy.objects.create(edition=book, shelf=self.shelf)
        return book

    def results(self, query="", **kwargs):
        response = self.client.get("/books/", {"q": query, **kwargs})
        self.assertEqual(response.status_code, 200)
        return list(response.context["page_obj"]), response

    def test_ranking_and_stable_ties(self):
        exact = self.book("Garden")
        alias = self.book("Aliases", aliases="Garden\nAnother title")
        partial = self.book("Garden paths")
        credit = self.book("Other title")
        Contribution.objects.create(
            edition=credit, contributor=Contributor.objects.create(name="Garden Writer")
        )
        summary = self.book("Summary fixture", summary="A garden story")
        books, _ = self.results("GARDEN")
        self.assertEqual(books, [alias, exact, partial, credit, summary])
        self.assertEqual(self.results("Garden")[0], books)

    def test_exact_isbn_and_accession_first(self):
        isbn = self.book("ISBN fixture", isbn="978-1-234-56789-X")
        title = self.book("978123456789X")
        self.assertEqual(self.results("978 1 234 56789 X")[0][0], isbn)
        self.assertEqual(self.results("978123456789X")[0], [isbn, title])
        copy = isbn.copies.get()
        accession_title = self.book(copy.accession)
        self.assertEqual(self.results(copy.accession.lower())[0], [isbn, accession_title])

    def test_urdu_arabic_alias_and_original_preservation(self):
        book = self.book("بُخَـاری", aliases="Bukhari\nSahih Bukhari")
        self.assertEqual(self.results("بخاري")[0], [book])
        self.assertEqual(self.results("bukhari")[0], [book])
        book.aliases = ""
        book.save()
        self.assertEqual(self.results("Bukhari")[0], [])
        book.refresh_from_db()
        self.assertEqual(book.title, "بُخَـاری")
        arabic = self.book("كِتَابُ العِلْم")
        self.assertEqual(self.results("کتاب العلم")[0], [arabic])

    def test_related_edits_and_import_style_updates_are_immediate(self):
        book = self.book("Original")
        contributor = Contributor.objects.create(name="Old name")
        Contribution.objects.create(edition=book, contributor=contributor)
        Contributor.objects.filter(pk=contributor.pk).update(name="كِتَاب")
        self.assertEqual(self.results("کتاب")[0], [book])
        Edition.objects.filter(pk=book.pk).update(aliases="Updated Roman alias")
        self.assertEqual(self.results("updated roman alias")[0], [book])

    def test_combined_filters_and_no_duplicates(self):
        book = self.book("Multi")
        for number in range(3):
            Copy.objects.create(edition=book, shelf=self.shelf)
            Contribution.objects.create(
                edition=book, contributor=Contributor.objects.create(name=f"Multi writer {number}")
            )
        book.categories.add(Category.objects.create(slug="second", name="Multi second"))
        self.assertEqual(self.results("Multi")[0], [book])
        copies = list(book.copies.all())
        Loan.objects.create(copy=copies[0], borrower_name="PRIVATE SEARCH FIXTURE", contact="PRIVATE CONTACT")
        self.assertEqual(
            self.results("Multi", category=self.category.slug, language="ur", availability="available")[0],
            [book],
        )
        self.assertEqual(self.results("Multi", availability="on_loan")[0], [book])
        self.assertEqual(self.results(copies[0].accession, availability="available")[0], [])
        self.assertEqual(self.results("Multi", language="en")[0], [])
        for query in ["PRIVATE SEARCH FIXTURE", "PRIVATE CONTACT"]:
            self.assertEqual(self.results(query)[0], [])
        response = self.results("Multi")[1]
        self.assertNotContains(response, "PRIVATE SEARCH FIXTURE")

    def test_hidden_copy_does_not_supply_availability_or_search(self):
        book = self.book("Public fixture")
        hidden = Copy.objects.create(edition=book, shelf=self.shelf, is_public=False)
        Loan.objects.create(copy=book.copies.get(is_public=True), borrower_name="Private")
        self.assertEqual(self.results("Public fixture", availability="available")[0], [])
        self.assertEqual(self.results(hidden.accession)[0], [])
        private = Edition.objects.create(title="Hidden only")
        Copy.objects.create(edition=private, shelf=self.shelf, is_public=False)
        self.assertEqual(self.results("Hidden only")[0], [])

    def test_invalid_and_bounded_inputs(self):
        self.book("Fixture")
        for parameters in [
            {"q": "a" * 201},
            {"category": "x" * 51},
            {"language": "x" * 13},
            {"availability": "bad"},
            {"category": "' OR 1=1"},
        ]:
            response = self.client.get("/books/", parameters)
            self.assertTrue(response.context["search_form"].errors)
            self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_pagination_does_not_repeat_tied_results(self):
        for _ in range(16):
            self.book("Same title")
        first, response = self.results("Same")
        second, _ = self.results("Same", page="2")
        self.assertEqual(response.context["page_obj"].paginator.count, 16)
        self.assertEqual(len(first), 12)
        self.assertEqual(len(second), 4)
        self.assertFalse(set(book.pk for book in first) & set(book.pk for book in second))
