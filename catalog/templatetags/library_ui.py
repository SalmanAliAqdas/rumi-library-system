from django import template
from django.utils.translation import get_language

from catalog.management_labels import LABELS as MANAGEMENT_LABELS
from catalog.offline_labels import LABELS as OFFLINE_LABELS

register = template.Library()

# A small, explicit Phase 1 UI catalogue. Admin uses Django's built-in translations.
LABELS = {
    "catalog": ("The collection", "کتابوں کا مجموعہ", "المجموعة"),
    "home": ("Welcome", "خوش آمدید", "مرحباً"),
    "display": ("Display mode", "نمائشی انداز", "وضع العرض"),
    "exit_display": ("Exit display", "نمائش ختم کریں", "إنهاء العرض"),
    "fullscreen": ("Fullscreen", "پوری اسکرین", "ملء الشاشة"),
    "librarian": ("Librarian", "منتظم", "أمين المكتبة"),
    "eyebrow": (
        "A PERSONAL LIBRARY · A SHARED CURIOSITY",
        "ذاتی کتب خانہ · مشترکہ جستجو",
        "مكتبة شخصية · فضول مشترك",
    ),
    "headline": (
        "A quiet place for curious minds.",
        "جستجو کرنے والوں کے لیے ایک پُرسکون جگہ۔",
        "مكان هادئ للعقول الفضولية.",
    ),
    "intro": (
        "Find your next companion among the shelves. Explore stories, ideas and knowledge, one book at a time.",
        "کتابوں میں اپنا اگلا ساتھی تلاش کریں۔ کہانیوں، خیالات اور علم کی دنیا میں قدم رکھیں۔",
        "اعثر على رفيقك القادم بين الرفوف. اكتشف القصص والأفكار والمعرفة، كتاباً تلو الآخر.",
    ),
    "search": ("Find a book", "کتاب تلاش کریں", "ابحث عن كتاب"),
    "placeholder": (
        "Title, author, subject or library number…",
        "عنوان، مصنف، موضوع یا کتاب نمبر…",
        "العنوان أو المؤلف أو الموضوع أو رقم الكتاب…",
    ),
    "editions": ("Unique editions", "منفرد اشاعتیں", "طبعات مميزة"),
    "copies": ("Physical copies & volumes", "نسخے اور جلدیں", "النسخ والمجلدات"),
    "languages": ("Book languages", "کتابوں کی زبانیں", "لغات الكتب"),
    "browse": ("Follow your curiosity", "اپنی دلچسپی کا انتخاب کریں", "اتبع فضولك"),
    "subjects": ("BROWSE BY SUBJECT", "موضوع کے لحاظ سے", "تصفح حسب الموضوع"),
    "recent": ("New to the shelves", "نئی شامل کردہ کتابیں", "أضيف حديثاً"),
    "all": ("View all books", "تمام کتابیں دیکھیں", "عرض جميع الكتب"),
    "demo": (
        "Development collection — all sample books and contributors are fictional.",
        "ترقیاتی نمونہ — تمام نمونہ کتابیں اور مصنفین فرضی ہیں۔",
        "مجموعة تجريبية — جميع الكتب والمساهمين في العينات خياليون.",
    ),
    "fictional": ("Fictional demo", "فرضی نمونہ", "عينة خيالية"),
    "available": ("Available", "دستیاب", "متاح"),
    "on_loan": ("On loan", "عاریت پر", "مُعار"),
    "empty": ("The shelves are waiting.", "شیلف کتابوں کے منتظر ہیں۔", "الرفوف تنتظر الكتب."),
    "empty_help": (
        "Books will appear here as the librarian adds them. Come back soon.",
        "منتظم کی شامل کردہ کتابیں یہاں نظر آئیں گی۔",
        "ستظهر الكتب هنا عندما يضيفها أمين المكتبة.",
    ),
    "no_results": (
        "No books found. Try another title or remove a filter.",
        "کوئی کتاب نہیں ملی۔ عنوان یا فلٹر تبدیل کریں۔",
        "لم يتم العثور على كتب. جرّب عنواناً آخر أو أزل عامل التصفية.",
    ),
    "all_subjects": ("All subjects", "تمام موضوعات", "جميع المواضيع"),
    "all_languages": ("All languages", "تمام زبانیں", "جميع اللغات"),
    "filter": ("Search & filter", "تلاش اور فلٹر", "بحث وتصفية"),
    "results": ("editions found", "اشاعتیں ملیں", "طبعات موجودة"),
    "clear": ("Clear filters", "فلٹر ہٹائیں", "إزالة عوامل التصفية"),
    "previous": ("Previous", "پچھلا", "السابق"),
    "next": ("Next", "اگلا", "التالي"),
    "about": ("About this edition", "اس اشاعت کے بارے میں", "عن هذه الطبعة"),
    "no_summary": (
        "A description has not been added yet.",
        "تفصیل ابھی شامل نہیں کی گئی۔",
        "لم تتم إضافة وصف بعد.",
    ),
    "location": ("Find it on the shelf", "شیلف پر تلاش کریں", "اعثر عليه على الرف"),
    "shelf": ("Shelf", "شیلف", "الرف"),
    "volume": ("Volume", "جلد", "المجلد"),
    "footer": (
        "Collected with care. Shared with you.",
        "محبت سے جمع کی گئی کتابیں، آپ کے لیے۔",
        "جُمعت بعناية. نشاركها معكم.",
    ),
    "skip": ("Skip to content", "مواد پر جائیں", "انتقل إلى المحتوى"),
    "not_found": ("This page is not on our shelves.", "یہ صفحہ دستیاب نہیں۔", "هذه الصفحة غير موجودة."),
    "author": ("Author", "مصنف", "المؤلف"),
    "translator": ("Translator", "مترجم", "المترجم"),
    "editor": ("Editor", "مدیر", "المحرر"),
    "commentator": ("Commentator", "شارح", "الشارح"),
    "publisher": ("Publisher", "ناشر", "الناشر"),
    "edition": ("Edition", "اشاعت", "الطبعة"),
    "year": ("Year", "سال", "السنة"),
}

LABELS.update(MANAGEMENT_LABELS)
LABELS.update(OFFLINE_LABELS)


@register.simple_tag
def ui(key):
    return LABELS.get(key, (key, key, key))[{"en": 0, "ur": 1, "ar": 2}.get(get_language(), 0)]
