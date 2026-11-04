from django.test import SimpleTestCase
from django.utils.translation import override

from catalog.management_labels import LABELS
from catalog.phase5_labels import LABELS as PHASE5_LABELS
from catalog.templatetags.library_ui import ui


class TranslationTests(SimpleTestCase):
    def test_phase5_label_catalogue_is_complete(self):
        for key, values in PHASE5_LABELS.items():
            self.assertEqual(len(values), 3, key)
            self.assertTrue(all(isinstance(value, str) and value.strip() for value in values), key)
            for code, expected in zip(["en", "ur", "ar"], values, strict=True):
                with override(code):
                    self.assertEqual(ui(key), expected)

    def test_phase2_label_catalogue_is_complete(self):
        for key, translations in LABELS.items():
            self.assertEqual(len(translations), 3, key)
            self.assertTrue(all(isinstance(value, str) and value.strip() for value in translations), key)
            for code, expected in zip(["en", "ur", "ar"], translations, strict=True):
                with override(code):
                    self.assertEqual(ui(key), expected, (key, code))
