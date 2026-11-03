"""Phase 4 labels in English, Urdu and Arabic."""

LABELS = {
    "loans": ("Loans", "عاریتیں", "الإعارات"),
    "issue_copy": ("Issue a copy", "نسخہ عاریت پر دیں", "إعارة نسخة"),
    "copy": ("Physical copy", "کتاب کا نسخہ", "النسخة"),
    "borrower_name": ("Borrower name", "عاریت لینے والے کا نام", "اسم المستعير"),
    "contact": ("Contact details (optional)", "رابطے کی تفصیل (اختیاری)", "بيانات الاتصال (اختيارية)"),
    "issue_date": ("Issue date", "عاریت کی تاریخ", "تاريخ الإعارة"),
    "due_date": ("Due date (optional)", "واپسی کی مقررہ تاریخ (اختیاری)", "تاريخ الاستحقاق (اختياري)"),
    "returned_date": ("Returned on", "واپسی کی تاریخ", "تاريخ الإرجاع"),
    "overdue": ("Overdue only", "صرف تاخیر والی عاریتیں", "المتأخرة فقط"),
    "return_copy": ("Mark returned", "واپسی درج کریں", "تسجيل الإرجاع"),
    "confirm_return": (
        "Confirm this copy has been returned. The loan history will be kept.",
        "تصدیق کریں کہ یہ نسخہ واپس مل گیا ہے۔ عاریت کا ریکارڈ محفوظ رہے گا۔",
        "أكد استلام هذه النسخة. سيُحفظ سجل الإعارة.",
    ),
    "returned": ("Returned", "واپس آ گئی", "أُعيدت"),
    "loan_history": ("Private copy loan history", "نسخے کی نجی عاریت کا ریکارڈ", "سجل إعارات النسخة الخاص"),
    "loan_saved": ("Loan recorded.", "عاریت درج ہو گئی۔", "سُجلت الإعارة."),
    "return_saved": (
        "Return recorded (or already returned).",
        "واپسی درج ہو گئی (یا پہلے درج تھی)۔",
        "سُجل الإرجاع (أو كان مسجلاً بالفعل).",
    ),
    "loan_conflict": (
        "This copy already has an active loan. Refresh and check the loan list.",
        "یہ نسخہ پہلے ہی عاریت پر ہے۔ فہرست تازہ کر کے دیکھیں۔",
        "هذه النسخة مُعارة بالفعل. حدّث قائمة الإعارات وتحقق منها.",
    ),
    "issue_future": (
        "Issue date cannot be in the future.",
        "عاریت کی تاریخ مستقبل کی نہیں ہو سکتی۔",
        "لا يمكن أن يكون تاريخ الإعارة في المستقبل.",
    ),
    "due_before_issue": (
        "Due date cannot be before issue date.",
        "مقررہ واپسی کی تاریخ عاریت سے پہلے نہیں ہو سکتی۔",
        "لا يمكن أن يسبق الاستحقاق تاريخ الإعارة.",
    ),
    "return_before_issue": (
        "Return date cannot be before issue date or in the future.",
        "واپسی کی تاریخ عاریت سے پہلے یا مستقبل کی نہیں ہو سکتی۔",
        "لا يمكن أن يسبق الإرجاع تاريخ الإعارة أو يكون في المستقبل.",
    ),
    "ask_book": ("Ask about this book", "اس کتاب کے بارے میں پوچھیں", "استفسر عن هذا الكتاب"),
    "enquiry_message": (
        "Hello, I would like to ask about {title}. Accession: {accession}. Volume: {volume}. {url}",
        "السلام علیکم، میں {title} کے بارے میں پوچھنا چاہتا ہوں۔ نمبر: {accession}۔ جلد: {volume}۔ {url}",
        "مرحباً، أود الاستفسار عن {title}. رقم النسخة: {accession}. المجلد: {volume}. {url}",
    ),
    "whatsapp_help": (
        "Opens WhatsApp; does not reserve a book or send a message automatically. Sending an enquiry requires internet, including when browsing a saved catalog.",
        "واٹس ایپ کھلے گا؛ کتاب محفوظ نہیں ہوگی اور پیغام خود نہیں جائے گا۔ محفوظ کیٹلاگ دیکھتے وقت بھی پیغام بھیجنے کے لیے انٹرنیٹ ضروری ہے۔",
        "يفتح واتساب؛ لا يحجز الكتاب ولا يرسل رسالة تلقائياً. يتطلب إرسال الاستفسار الإنترنت حتى عند تصفح فهرس محفوظ.",
    ),
    "saved_copy": (
        "Open this edition in the saved offline catalog",
        "یہ اشاعت محفوظ آف لائن کیٹلاگ میں کھولیں",
        "افتح هذه الطبعة في الفهرس المحفوظ دون اتصال",
    ),
    "labels": ("Print copy labels", "نسخوں کے لیبل چھاپیں", "طباعة ملصقات النسخ"),
    "label_help": (
        "Select 1–24 visible copies, then preview. Search or filter by shelf before selecting; selections apply to this page only.",
        "۱ تا ۲۴ نمایاں نسخے منتخب کر کے پیش منظر دیکھیں۔ پہلے تلاش یا شیلف سے چھانٹیں؛ انتخاب صرف اس صفحے کا ہے۔",
        "اختر من نسخة واحدة إلى 24 نسخة ظاهرة ثم عاين. ابحث أو رشّح بالرف أولاً؛ الاختيار يخص هذه الصفحة فقط.",
    ),
    "label_bounds": (
        "Select between 1 and 24 distinct visible copies.",
        "۱ تا ۲۴ الگ نمایاں نسخے منتخب کریں۔",
        "اختر من نسخة واحدة إلى 24 نسخة ظاهرة ومختلفة.",
    ),
    "preview_labels": ("Preview labels", "لیبلوں کا پیش منظر", "معاينة الملصقات"),
    "print": ("Print / Save as PDF", "چھاپیں / پی ڈی ایف محفوظ کریں", "طباعة / حفظ بصيغة PDF"),
    "site_warning": (
        "Test destination: localhost, temporary address or unconfigured SITE_URL. Wait for a final public domain before printing permanent labels.",
        "آزمائشی پتہ: لوکل ہوسٹ، عارضی پتہ یا غیر مقرر SITE_URL۔ مستقل لیبل چھاپنے سے پہلے حتمی عوامی ڈومین مقرر کریں۔",
        "وجهة تجريبية: عنوان محلي أو مؤقت أو SITE_URL غير مضبوط. انتظر النطاق العام النهائي قبل طباعة ملصقات دائمة.",
    ),
    "qr_destination": ("QR destination", "کیو آر کا پتہ", "وجهة رمز QR"),
    "csv_export": ("Public catalog CSV export", "عوامی کیٹلاگ کا CSV اخراج", "تصدير الفهرس العام بصيغة CSV"),
    "csv_help": (
        "One row per visible physical copy. UTF-8 for Excel; fields that could be spreadsheet formulas are prefixed with an apostrophe. Public catalog only; this cannot restore loans or the database.",
        "ہر نمایاں نسخے کی ایک سطر۔ ایکسل کے لیے UTF-8؛ فارمولہ بن سکنے والے خانوں کے شروع میں apostrophe لگایا جاتا ہے۔ صرف عوامی کیٹلاگ؛ اس سے عاریتیں یا ڈیٹابیس بحال نہیں ہو سکتے۔",
        "صف لكل نسخة ظاهرة، بترميز UTF-8 لإكسل؛ تُسبق الحقول المحتملة كصيغ بعلامة اقتباس مفردة. فهرس عام فقط؛ لا يستعيد الإعارات أو قاعدة البيانات.",
    ),
}
