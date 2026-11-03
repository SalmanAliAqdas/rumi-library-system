from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Category, Contribution, Contributor, Copy, Edition, Language, Shelf

TITLES = [
    ("The Orchard of Quiet Questions", "en", "literature"),
    ("A Map of Unwritten Roads", "en", "history"),
    ("Small Experiments in Wonder", "en", "science"),
    ("Letters from an Imaginary Garden", "en", "literature"),
    ("The Patient Reader", "en", "philosophy"),
    ("An Atlas of Everyday Stars", "en", "science"),
    ("Conversations beside the Window", "en", "philosophy"),
    ("The Paper Lantern Archive", "en", "history"),
    ("روشنی کے فرضی راستے", "ur", "literature"),
    ("خیالی باغ کی کہانیاں", "ur", "literature"),
    ("سوچ کے نئے دریچے", "ur", "philosophy"),
    ("ستاروں کی چھوٹی کتاب", "ur", "science"),
    ("ایک خیالی شہر کی تاریخ", "ur", "history"),
    ("لفظوں کا سفر", "ur", "literature"),
    ("حديقة الأسئلة الهادئة", "ar", "philosophy"),
    ("رسائل من مدينة خيالية", "ar", "literature"),
    ("أطلس النجوم الصغيرة", "ar", "science"),
    ("حكايات الرف القديم", "ar", "history"),
    ("Bridges of Words · لفظوں کے پل", "ur", "literature"),
    ("A Shared Sky · سماء مشتركة", "ar", "science"),
]


class Command(BaseCommand):
    help = "Explicitly add 20 fictional development editions; safe to rerun. Never run on a real collection."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Demo seeding is allowed only in development with local SQLite.")
        languages = {
            code: Language.objects.get_or_create(code=code, defaults={"name": name})[0]
            for code, name in [("en", "English"), ("ur", "اردو"), ("ar", "العربية")]
        }
        categories = {}
        for slug, name, ur, ar in [
            ("literature", "Literature & poetry", "ادب اور شاعری", "الأدب والشعر"),
            ("history", "History & heritage", "تاریخ اور ورثہ", "التاريخ والتراث"),
            ("science", "Science & nature", "سائنس اور فطرت", "العلوم والطبيعة"),
            ("philosophy", "Thought & philosophy", "فکر اور فلسفہ", "الفكر والفلسفة"),
        ]:
            categories[slug] = Category.objects.get_or_create(
                slug=slug, defaults={"name": name, "name_ur": ur, "name_ar": ar}
            )[0]
        shelves = [
            Shelf.objects.get_or_create(
                label=f"Example {n}",
                defaults={
                    "description": "Editable demo placeholder; not a map of the room.",
                    "display_order": n,
                },
            )[0]
            for n in range(1, 5)
        ]
        created = 0
        for index, (title, code, category) in enumerate(TITLES, 1):
            edition, new = Edition.objects.get_or_create(
                demo_key=f"rumi-demo-{index:02}",
                defaults={
                    "title": title,
                    "original_language": code,
                    "is_demo": True,
                    "summary": {
                        "en": "A fictional development book exploring curiosity and the joy of reading. This is sample content, not a real inventory record.",
                        "ur": "یہ ترقیاتی نمونے کے لیے ایک فرضی کتاب ہے۔ یہ حقیقی مجموعے کا ریکارڈ نہیں ہے۔",
                        "ar": "كتاب خيالي للتجربة والتطوير. هذا محتوى تجريبي وليس سجلاً لكتاب حقيقي.",
                    }[code],
                    "publisher": "Imaginary Press (fictional)",
                    "edition": "Demo edition",
                    "year": 2025,
                },
            )
            if not new:
                continue
            created += 1
            edition.languages.add(languages[code])
            if index >= 19:
                edition.languages.add(languages["en"])
            edition.categories.add(categories[category])
            contributor, _ = Contributor.objects.get_or_create(
                name={"en": "Avery Fable (fictional)", "ur": "خیالی مصنف", "ar": "كاتب خيالي"}[code]
            )
            Contribution.objects.create(edition=edition, contributor=contributor)
            for volume in ["I", "II", "III"] if index == 8 else ["", ""] if index == 1 else [""]:
                Copy.objects.create(edition=edition, shelf=shelves[(index - 1) % 3], volume=volume)
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} fictional editions. Demo shelves are editable placeholders."
            )
        )
