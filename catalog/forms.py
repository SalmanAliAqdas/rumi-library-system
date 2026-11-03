from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.functional import lazy

from .models import Category, Contributor, Copy, Edition, Language, Shelf
from .templatetags.library_ui import ui

label = lazy(ui, str)
ROLE_FIELDS = {
    "authors": "author",
    "translators": "translator",
    "editors": "editor",
    "commentators": "commentator",
}


class LocalizedFields:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        names = {
            "unknown_author": "unknown",
            "is_public": "public_visibility",
            "start": "start_volume",
            "end": "end_volume",
            "labels": "volume_labels",
            "isbn": "ISBN",
            "q": "search",
            "category": "categories",
            "language": "languages",
            "token": "submission_confirmation",
            "preview_token": "submission_confirmation",
        }
        for name, field in self.fields.items():
            field.label = label(names.get(name, name))
            field.help_text = ""
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs["dir"] = (
                    "ltr"
                    if name in {"isbn", "cover_url", "slug", "token", "username", "password"}
                    else "auto"
                )


class LibrarianAuthenticationForm(LocalizedFields, AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff or not user.has_perms(["catalog.view_edition", "catalog.view_copy"]):
            raise ValidationError(label("permission_denied"), code="not_librarian")


class EditionForm(LocalizedFields, forms.ModelForm):
    authors = forms.ModelMultipleChoiceField(Contributor.objects.order_by("name", "pk"), required=False)
    unknown_author = forms.BooleanField(required=False)
    translators = forms.ModelMultipleChoiceField(Contributor.objects.order_by("name", "pk"), required=False)
    editors = forms.ModelMultipleChoiceField(Contributor.objects.order_by("name", "pk"), required=False)
    commentators = forms.ModelMultipleChoiceField(Contributor.objects.order_by("name", "pk"), required=False)
    original_language = forms.ChoiceField()
    token = forms.CharField(widget=forms.HiddenInput, max_length=500, required=False)

    class Meta:
        model = Edition
        fields = [
            "title",
            "original_language",
            "languages",
            "categories",
            "aliases",
            "isbn",
            "publisher",
            "edition",
            "year",
            "summary",
            "cover_url",
        ]
        widgets = {"aliases": forms.Textarea(attrs={"rows": 3}), "summary": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        languages = list(Language.objects.order_by("code").values_list("code", "name"))
        if self.instance.pk and self.instance.original_language not in {item[0] for item in languages}:
            languages.append((self.instance.original_language, self.instance.original_language))
        self.fields["original_language"].choices = languages
        self.fields["languages"].queryset = Language.objects.order_by("code")
        self.fields["categories"].queryset = Category.objects.order_by("name", "pk")
        self.fields["categories"].label_from_instance = lambda category: category.display_name
        self.initial.setdefault("original_language", "en")
        if self.instance.pk:
            for name, role in ROLE_FIELDS.items():
                self.initial[name] = list(
                    self.instance.credits.filter(role=role).values_list("contributor_id", flat=True)
                )
            self.initial["unknown_author"] = not self.initial["authors"]

    def clean(self):
        data = super().clean()
        authors = data.get("authors")
        if not authors and not data.get("unknown_author"):
            self.add_error("authors", label("author_required"))
        if authors and data.get("unknown_author"):
            self.add_error("unknown_author", label("author_conflict"))
        return data

    @property
    def main_fields(self):
        return [
            self[name]
            for name in ["title", "original_language", "authors", "unknown_author", "languages", "categories"]
        ]

    @property
    def optional_fields(self):
        return [
            self[name]
            for name in [
                "isbn",
                "aliases",
                "publisher",
                "edition",
                "year",
                "summary",
                "cover_url",
                "translators",
                "editors",
                "commentators",
            ]
        ]


class CopyForm(LocalizedFields, forms.ModelForm):
    token = forms.CharField(widget=forms.HiddenInput, max_length=500, required=False)

    class Meta:
        model = Copy
        fields = ["shelf", "volume", "is_public"]


class VolumeForm(LocalizedFields, forms.Form):
    start = forms.IntegerField(min_value=1, max_value=9999, initial=1)
    end = forms.IntegerField(min_value=1, max_value=9999, initial=3)
    shelf = forms.ModelChoiceField(Shelf.objects.all())
    is_public = forms.BooleanField(required=False, initial=True)
    labels = forms.CharField(required=False, max_length=2025, widget=forms.Textarea(attrs={"rows": 8}))
    token = forms.CharField(widget=forms.HiddenInput, max_length=500)
    preview_token = forms.CharField(required=False, max_length=600, widget=forms.HiddenInput)

    def clean(self):
        data = super().clean()
        if "start" in data and "end" in data:
            count = data["end"] - data["start"] + 1
            if not 1 <= count <= 25:
                raise ValidationError(label("bad_range"))
            raw = data.get("labels", "")
            if raw.strip():
                labels = [line.strip() for line in raw.strip().splitlines()]
                if (
                    len(labels) != count
                    or len(set(labels)) != count
                    or any(not x or len(x) > 80 for x in labels)
                ):
                    self.add_error("labels", label("bad_labels"))
                else:
                    data["volume_labels"] = labels
        return data


class ShelfForm(LocalizedFields, forms.ModelForm):
    class Meta:
        model = Shelf
        fields = ["label", "description", "display_order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class CategoryForm(LocalizedFields, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["slug", "name", "name_ur", "name_ar"]


class ContributorForm(LocalizedFields, forms.ModelForm):
    class Meta:
        model = Contributor
        fields = ["name"]


class SearchForm(LocalizedFields, forms.Form):
    q = forms.CharField(required=False, max_length=200)
    category = forms.RegexField(r"^[a-zA-Z0-9_-]*$", required=False, max_length=50)
    language = forms.RegexField(r"^[a-zA-Z0-9_-]*$", required=False, max_length=12)
    availability = forms.ChoiceField(
        required=False,
        choices=[
            ("", label("all_availability")),
            ("available", label("available")),
            ("on_loan", label("on_loan")),
        ],
    )
    shelf = forms.IntegerField(required=False, min_value=1)
    visibility = forms.ChoiceField(
        required=False,
        choices=[("", label("any_visibility")), ("public", label("public")), ("hidden", label("hidden"))],
    )
