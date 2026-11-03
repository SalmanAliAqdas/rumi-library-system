import json

from django.core import serializers
from django.test import TestCase

from catalog.models import Copy, Edition, Language, Shelf


class ImportTests(TestCase):
    def test_language_natural_keys_reuse_reference_records(self):
        language, _ = Language.objects.get_or_create(code="ur", defaults={"name": "اردو"})
        shelf = Shelf.objects.create(label="Import fixture")
        edition = Edition.objects.create(title="بُخَاری", aliases="Bukhari")
        edition.languages.add(language)
        copy = Copy.objects.create(edition=edition, shelf=shelf)
        original_accession = copy.accession
        payload = serializers.serialize(
            "json", [language, edition, copy], use_natural_foreign_keys=True, use_natural_primary_keys=True
        )
        data = json.loads(payload)
        self.assertNotIn("pk", data[0])
        self.assertEqual(data[1]["fields"]["languages"], [["ur"]])
        # Reimport into a database where reference languages already exist.
        for record in serializers.deserialize("json", payload):
            record.save()
        self.assertEqual(Language.objects.filter(code="ur").count(), 1)
        self.assertEqual(edition.languages.get(), language)
        copy.refresh_from_db()
        self.assertEqual(copy.accession, original_accession)
        response = self.client.get("/books/", {"q": "Bukhari"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
