"""Online-only private lending and public-data tools."""

import csv
import io
import re
from urllib.parse import urlencode

import segno
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods, require_safe

from .copy_links import copy_url, temporary_site
from .forms import LocalizedFields
from .librarian import librarian_required
from .models import Copy, Loan, Shelf
from .templatetags.library_ui import ui
from .views import public_editions
from .workflows import create_once, issue_token, validate_token


class IssueForm(LocalizedFields, forms.Form):
    copy = forms.ModelChoiceField(Copy.objects.select_related("edition", "shelf"))
    borrower_name = forms.CharField(max_length=160)
    contact = forms.CharField(max_length=160, required=False)
    issue_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}))
    due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    token = forms.CharField(widget=forms.HiddenInput, max_length=500)

    def clean(self):
        data = super().clean()
        loan = Loan(
            **{
                key: data[key]
                for key in ("copy", "borrower_name", "contact", "issue_date", "due_date")
                if key in data
            }
        )
        try:
            loan.clean()
        except ValidationError as error:
            for key, errors in error.message_dict.items():
                self.add_error(key, errors)
        return data


@librarian_required("catalog.view_loan", "catalog.view_copy", "catalog.view_edition")
@require_safe
def loan_list(request, accession=None):
    copy = get_object_or_404(Copy, accession=accession) if accession else None
    loans = Loan.objects.select_related("copy__edition").order_by("-issue_date", "-pk")
    if copy:
        loans = loans.filter(copy=copy)
    else:
        loans = loans.filter(returned_date__isnull=True)
    query = request.GET.get("q", "")[:200]
    if query:
        loans = loans.filter(
            Q(copy__accession__icontains=query)
            | Q(copy__edition__title__icontains=query)
            | Q(borrower_name__icontains=query)
        )
    overdue = request.GET.get("overdue") == "1"
    if overdue:
        loans = loans.filter(returned_date__isnull=True, due_date__lt=timezone.localdate())
    return render(
        request,
        "librarian/loans.html",
        {
            "copy": copy,
            "query": query,
            "overdue": overdue,
            "page_obj": Paginator(loans, 20).get_page(request.GET.get("page", "")[:10]),
            "parameters": urlencode({"q": query, "overdue": "1" if overdue else ""}),
        },
    )


@librarian_required("catalog.add_loan", "catalog.view_loan", "catalog.view_copy", "catalog.view_edition")
@require_http_methods(["GET", "POST"])
def issue(request):
    action = "loan:issue"
    form = IssueForm(
        request.POST if request.method == "POST" else None,
        initial={"token": issue_token(request.user, action), "copy": request.GET.get("copy")},
    )
    query = request.GET.get("q", "")[:200]
    if request.method == "GET" and query:
        form.fields["copy"].queryset = form.fields["copy"].queryset.filter(
            Q(accession__icontains=query) | Q(edition__title__icontains=query)
        )
    if request.method == "POST" and form.is_valid():
        token = validate_token(form, request.user, action)
        if token:

            def operation():
                copy = Copy.objects.select_for_update().get(pk=form.cleaned_data["copy"].pk)
                if copy.loans.filter(returned_date__isnull=True).exists():
                    raise ValidationError(ui("loan_conflict"))
                Loan.objects.create(
                    **{
                        key: form.cleaned_data[key]
                        for key in ("copy", "borrower_name", "contact", "issue_date", "due_date")
                    }
                )
                return copy.edition, [copy]

            try:
                _, created = create_once(request.user, action, token, operation)
            except (IntegrityError, ValidationError):
                form.add_error(None, ui("loan_conflict"))
            else:
                messages.success(request, ui("loan_saved") if created else ui("already_saved"))
                return redirect("librarian:loans")
    return render(request, "librarian/issue.html", {"form": form, "query": query})


@librarian_required("catalog.change_loan", "catalog.view_loan", "catalog.view_copy", "catalog.view_edition")
@require_http_methods(["GET", "POST"])
def return_loan(request, pk):
    loan = get_object_or_404(Loan.objects.select_related("copy__edition"), pk=pk)
    error = ""
    if request.method == "POST":
        with transaction.atomic():
            # Write first: one conditional UPDATE is atomic on PostgreSQL and
            # SQLite, without a SQLite read-to-write lock upgrade on retries.
            updated = Loan.objects.filter(
                pk=loan.pk, returned_date__isnull=True, issue_date__lte=timezone.localdate()
            ).update(returned_date=timezone.localdate())
            if not updated and Loan.objects.filter(pk=loan.pk, returned_date__isnull=True).exists():
                error = ui("return_before_issue")
        if not error:
            messages.success(request, ui("return_saved"))
            return redirect("librarian:loans")
    return render(request, "librarian/return.html", {"loan": loan, "error": error})


def qr_svg(url):
    output = io.BytesIO()
    segno.make_qr(url, error="m").save(
        output, kind="svg", scale=4, border=4, dark="#000", light="#fff", xmldecl=False, omitsize=True
    )
    # Only Segno-generated geometry is marked safe, never catalogue text.
    return mark_safe(output.getvalue().decode("utf-8"))


@librarian_required("catalog.view_copy", "catalog.view_edition")
@require_http_methods(["GET", "POST"])
def labels(request):
    copies = Copy.objects.filter(is_public=True).select_related("edition", "shelf")
    query = request.GET.get("q", "")[:200]
    shelf = request.GET.get("shelf", "")[:20]
    if query:
        copies = copies.filter(Q(accession__icontains=query) | Q(edition__title__icontains=query))
    if shelf:
        copies = copies.filter(shelf_id=int(shelf)) if shelf.isdecimal() else copies.none()
    error = ""
    preview = []
    if request.method == "POST":
        selected = request.POST.getlist("copies")
        if (
            not 1 <= len(selected) <= 24
            or len(set(selected)) != len(selected)
            or any(not value.isdecimal() or len(value) > 18 for value in selected)
        ):
            error = ui("label_bounds")
        else:
            chosen = list(copies.filter(pk__in=selected))
            if len(chosen) != len(selected):
                error = ui("label_bounds")
            else:
                preview = [
                    {"copy": copy, "url": copy_url(copy), "svg": qr_svg(copy_url(copy))} for copy in chosen
                ]
    return render(
        request,
        "librarian/labels.html",
        {
            "page_obj": Paginator(copies, 24).get_page(request.GET.get("page", "")[:10]),
            "shelves": Shelf.objects.all(),
            "shelf": shelf,
            "query": query,
            "parameters": urlencode({"q": query, "shelf": shelf}),
            "preview": preview,
            "error": error,
            "site_warning": temporary_site(),
        },
    )


def csv_safe(value):
    value = str(value if value is not None else "")
    # Whitespace/control prefixes must not conceal a spreadsheet formula.
    if re.sub(r"^[\s\x00-\x1f\ufeff]+", "", value).startswith(("=", "+", "-", "@")) or value.startswith(
        ("\t", "\r", "\n")
    ):
        return "'" + value
    return value


@librarian_required("catalog.view_copy", "catalog.view_edition")
@require_safe
def export_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rumi-public-catalog.csv"'
    response["X-Content-Type-Options"] = "nosniff"
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Accession",
            "Original title",
            "Volume",
            "Contributors",
            "Languages",
            "Categories",
            "ISBN",
            "Publisher",
            "Edition",
            "Year",
            "Shelf",
            "Availability",
            "Public URL",
        ]
    )
    for book in public_editions().order_by("pk"):
        for copy in book.visible_copies:
            writer.writerow(
                map(
                    csv_safe,
                    [
                        copy.accession,
                        book.title,
                        copy.volume,
                        "; ".join(
                            f"{credit.contributor.name} ({credit.role})" for credit in book.credits.all()
                        ),
                        "; ".join(language.name for language in book.languages.all()),
                        "; ".join(category.name for category in book.categories.all()),
                        book.isbn,
                        book.publisher,
                        book.edition,
                        book.year,
                        copy.shelf.label,
                        "On loan" if copy.on_loan else "Available",
                        copy_url(copy),
                    ],
                )
            )
    return response
