from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone, translation


class LibrarySettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    name = models.CharField(max_length=120, default="Rumi Library")
    name_ur = models.CharField(max_length=120, default="رومی لائبریری")
    name_ar = models.CharField(max_length=120, default="مكتبة الرومي")
    description = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "library settings"
        constraints = [models.CheckConstraint(condition=Q(id=1), name="single_library_settings")]

    def __str__(self):
        return self.name


class Shelf(models.Model):
    label = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "label"]

    def __str__(self):
        return self.label


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    name_ur = models.CharField(max_length=100, blank=True)
    name_ar = models.CharField(max_length=100, blank=True)

    @property
    def display_name(self):
        return getattr(self, f"name_{translation.get_language()}", "") or self.name

    def __str__(self):
        return self.name


class LanguageManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


class Language(models.Model):
    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=60)
    objects = LanguageManager()

    def natural_key(self):
        return (self.code,)

    def __str__(self):
        return self.name


class Contributor(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Edition(models.Model):
    title = models.CharField(max_length=300)
    original_language = models.CharField(max_length=12, default="en")
    aliases = models.TextField(blank=True, help_text="Alternative titles and recorded search aliases")
    contributors = models.ManyToManyField(Contributor, through="Contribution", blank=True)
    languages = models.ManyToManyField(Language)
    categories = models.ManyToManyField(Category, blank=True)
    isbn = models.CharField(max_length=32, blank=True, db_index=True)
    publisher = models.CharField(max_length=200, blank=True)
    edition = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    metadata_source = models.URLField(blank=True, editable=False)
    metadata_retrieved_at = models.DateTimeField(null=True, blank=True, editable=False)
    is_demo = models.BooleanField(default=False, editable=False)
    demo_key = models.CharField(max_length=60, null=True, blank=True, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return self.title


class Contribution(models.Model):
    class Role(models.TextChoices):
        AUTHOR = "author", "Author"
        TRANSLATOR = "translator", "Translator"
        EDITOR = "editor", "Editor"
        COMMENTATOR = "commentator", "Commentator"

    edition = models.ForeignKey(Edition, on_delete=models.CASCADE, related_name="credits")
    contributor = models.ForeignKey(Contributor, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AUTHOR)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["edition", "contributor", "role"], name="unique_credit")
        ]


class AccessionSequence(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    value = models.PositiveBigIntegerField(default=0)


class Copy(models.Model):
    accession = models.CharField(max_length=24, unique=True, editable=False)
    edition = models.ForeignKey(Edition, on_delete=models.PROTECT, related_name="copies")
    volume = models.CharField(max_length=80, blank=True)
    shelf = models.ForeignKey(Shelf, on_delete=models.PROTECT, related_name="copies")
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["accession"]

    def save(self, *args, **kwargs):
        self.clean()
        if self.pk:
            original = type(self).objects.get(pk=self.pk).accession
            if self.accession != original:
                raise ValidationError("Accession numbers are permanent")
        elif self.accession:
            raise ValidationError("Accession numbers are generated automatically")
        if self._state.adding:
            with transaction.atomic():
                sequence, _ = AccessionSequence.objects.get_or_create(pk=1)
                # The UPDATE obtains the database write lock before the read, also on SQLite.
                AccessionSequence.objects.filter(pk=sequence.pk).update(value=F("value") + 1)
                sequence.refresh_from_db()
                self.accession = f"RL-{sequence.value:06d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def clean(self):
        if self.pk and not self.is_public:
            was_public = type(self).objects.filter(pk=self.pk, is_public=True).exists()
            if was_public and self.loans.filter(returned_date__isnull=True).exists():
                from .templatetags.library_ui import ui

                raise ValidationError({"is_public": ui("loan_visibility")})

    @property
    def available(self):
        return not self.loans.filter(returned_date__isnull=True).exists()

    def __str__(self):
        return f"{self.accession} · {self.edition} {self.volume}"


class Loan(models.Model):
    copy = models.ForeignKey(Copy, on_delete=models.PROTECT, related_name="loans")
    borrower_name = models.CharField(max_length=160)
    contact = models.CharField(max_length=160, blank=True)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    returned_date = models.DateField(null=True, blank=True)

    def clean(self):
        from .templatetags.library_ui import ui

        errors = {}
        today = timezone.localdate()
        if self.issue_date and self.issue_date > today:
            errors["issue_date"] = ui("issue_future")
        if self.due_date and self.issue_date and self.due_date < self.issue_date:
            errors["due_date"] = ui("due_before_issue")
        if self.returned_date and (
            self.returned_date > today or (self.issue_date and self.returned_date < self.issue_date)
        ):
            errors["returned_date"] = ui("return_before_issue")
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["copy"], condition=Q(returned_date__isnull=True), name="one_active_loan_per_copy"
            ),
            models.CheckConstraint(
                condition=Q(due_date__isnull=True) | Q(due_date__gte=F("issue_date")), name="due_after_issue"
            ),
            models.CheckConstraint(
                condition=Q(returned_date__isnull=True) | Q(returned_date__gte=F("issue_date")),
                name="return_after_issue",
            ),
        ]

    def __str__(self):
        return f"Loan {self.pk} · {self.copy.accession}"


class Submission(models.Model):
    """An atomic receipt for a signed, user/action-scoped create request."""

    token = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    edition = models.ForeignKey(Edition, on_delete=models.PROTECT, null=True)
    accessions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class LookupGate(models.Model):
    """One shared outgoing-provider reservation; contains no search or personal data."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    next_at = models.DateTimeField(default=timezone.now)
    count = models.PositiveSmallIntegerField(default=0)
