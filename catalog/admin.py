from django.contrib import admin

from .models import Category, Contribution, Contributor, Copy, Edition, Language, LibrarySettings, Loan, Shelf
from .templatetags.library_ui import ui


class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 1
    autocomplete_fields = ["contributor"]


class CopyInline(admin.TabularInline):
    model = Copy
    extra = 0
    readonly_fields = ["accession"]


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display = ["title", "original_language", "isbn", "is_demo"]
    search_fields = ["title", "aliases", "isbn"]
    list_filter = ["languages", "categories", "is_demo"]
    filter_horizontal = ["languages", "categories"]
    inlines = [ContributionInline, CopyInline]


@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display = ["accession", "edition", "volume", "shelf", "is_public", "available"]
    readonly_fields = ["accession"]
    list_filter = ["is_public", "shelf"]
    search_fields = ["accession", "edition__title"]
    autocomplete_fields = ["edition"]


@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["copy", "borrower_name", "issue_date", "due_date", "returned_date"]
    list_filter = ["returned_date"]
    search_fields = ["copy__accession", "borrower_name"]
    autocomplete_fields = ["copy"]


class RetainedTagAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        # Keep tagging metadata editable without exposing a cascading delete action.
        return False

    def get_fieldsets(self, request, obj=None):
        return [(None, {"fields": self.get_fields(request, obj), "description": ui("keep_records")})]


admin.site.register([Category, Language], RetainedTagAdmin)
admin.site.register([LibrarySettings, Shelf])
admin.site.site_header = "Rumi Library · Librarian"
