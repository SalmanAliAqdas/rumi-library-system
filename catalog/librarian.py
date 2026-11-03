from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from .forms import (
    CategoryForm,
    ContributorForm,
    CopyForm,
    EditionForm,
    LibrarianAuthenticationForm,
    SearchForm,
    ShelfForm,
    VolumeForm,
)
from .models import Category, Contributor, Copy, Edition, Language, Loan, Shelf
from .search import normalize, ranked_books
from .templatetags.library_ui import ui
from .workflows import create_copies, create_once, issue_token, save_credits, save_new_edition, validate_token


def librarian_required(*permissions):
    def decorator(view):
        @never_cache
        @wraps(view)
        def protected(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(), reverse("librarian:login"), REDIRECT_FIELD_NAME
                )
            if (
                not request.user.is_active
                or not request.user.is_staff
                or not request.user.has_perms(permissions)
            ):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return protected

    return decorator


class LibrarianLoginView(LoginView):
    template_name = "librarian/login.html"
    authentication_form = LibrarianAuthenticationForm
    next_page = "librarian:dashboard"

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class LibrarianLogoutView(LogoutView):
    next_page = "librarian:login"

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("librarian:login")
        if not request.user.is_staff or not request.user.has_perms(
            ["catalog.view_edition", "catalog.view_copy"]
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def management_editions():
    copies = Copy.objects.select_related("shelf").annotate(
        on_loan=Exists(Loan.objects.filter(copy=OuterRef("pk"), returned_date__isnull=True))
    )
    return Edition.objects.prefetch_related(
        "credits__contributor",
        "categories",
        "languages",
        Prefetch("copies", queryset=copies, to_attr="search_copies"),
    )


@librarian_required("catalog.view_edition", "catalog.view_copy", "catalog.view_loan")
@require_safe
def dashboard(request):
    active = Loan.objects.filter(returned_date__isnull=True)
    return render(
        request,
        "librarian/dashboard.html",
        {
            "edition_count": Edition.objects.count(),
            "copy_count": Copy.objects.count(),
            "available_count": Copy.objects.exclude(pk__in=active.values("copy_id")).count(),
            "loan_count": active.count(),
        },
    )


@librarian_required("catalog.view_edition", "catalog.view_copy")
@require_safe
def book_list(request):
    form = SearchForm(request.GET)
    books = []
    if form.is_valid():
        data = form.cleaned_data
        queryset = management_editions()
        if data["category"]:
            queryset = queryset.filter(categories__slug=data["category"])
        if data["language"]:
            queryset = queryset.filter(languages__code=data["language"])
        books = ranked_books(
            queryset.distinct(),
            data["q"],
            availability=data["availability"],
            shelf=data["shelf"],
            visibility=data["visibility"],
        )
    parameters = request.GET.copy()
    parameters.pop("page", None)
    return render(
        request,
        "librarian/book_list.html",
        {
            "search_form": form,
            "page_obj": Paginator(books, 15).get_page(request.GET.get("page", "")[:10]),
            "parameters": parameters.urlencode(),
            "shelves": Shelf.objects.all(),
            "categories": Category.objects.order_by("name"),
            "languages": Language.objects.order_by("code"),
        },
    )


@librarian_required("catalog.view_edition", "catalog.view_copy")
@require_safe
def book_detail(request, pk):
    return render(
        request, "librarian/book_detail.html", {"book": get_object_or_404(management_editions(), pk=pk)}
    )


def remember(request, shelf=None, categories=None):
    if shelf is not None:
        request.session["last_shelf"] = shelf.pk
    if categories is not None:
        request.session["last_categories"] = [category.pk for category in categories]


def announce(request, receipt, created):
    messages.success(request, ui("saved") if created else ui("already_saved"))
    messages.info(request, ui("accessions_saved") + " " + ", ".join(receipt.accessions))


@librarian_required("catalog.add_edition", "catalog.add_copy", "catalog.add_contribution")
@require_http_methods(["GET", "POST"])
def book_add(request):
    action = "edition:add"
    form = EditionForm(
        request.POST or None,
        initial={
            "categories": request.session.get("last_categories", []),
            "token": issue_token(request.user, action),
        },
    )
    copy_form = CopyForm(
        request.POST or None,
        prefix="copy",
        initial={"shelf": request.session.get("last_shelf"), "is_public": True},
    )
    if request.method == "POST" and request.POST.get("intent") != "refresh":
        valid = form.is_valid()
        valid = copy_form.is_valid() and valid
        token = validate_token(form, request.user, action) if valid else None
        if token:
            receipt, created = create_once(
                request.user, action, token, lambda: save_new_edition(form, copy_form)
            )
            if created:
                remember(request, copy_form.cleaned_data["shelf"], form.cleaned_data["categories"])
            announce(request, receipt, created)
            if request.POST.get("intent") == "another":
                return redirect("librarian:book_add")
            return redirect("librarian:book_detail", pk=receipt.edition_id)
    # Bound forms retain every draft field; refresh updates choices without saving.
    if request.POST.get("intent") == "refresh":
        form.errors.clear()
        copy_form.errors.clear()
    return render(
        request,
        "librarian/book_form.html",
        {"form": form, "copy_form": copy_form, "heading": "add_book", "adding": True},
    )


@librarian_required("catalog.change_edition", "catalog.add_contribution", "catalog.delete_contribution")
@require_http_methods(["GET", "POST"])
def book_edit(request, pk):
    book = get_object_or_404(Edition, pk=pk)
    form = EditionForm(request.POST or None, instance=book)
    if request.method == "POST" and request.POST.get("intent") != "refresh" and form.is_valid():
        with transaction.atomic():
            book = form.save()
            save_credits(book, form)
        remember(request, categories=form.cleaned_data["categories"])
        messages.success(request, ui("saved"))
        return redirect("librarian:book_detail", pk=book.pk)
    if request.POST.get("intent") == "refresh":
        form.errors.clear()
    return render(request, "librarian/book_form.html", {"form": form, "book": book, "heading": "edit_book"})


@librarian_required("catalog.add_copy", "catalog.view_edition")
@require_http_methods(["GET", "POST"])
def copy_add(request, pk):
    book = get_object_or_404(Edition, pk=pk)
    action = f"copy:add:{book.pk}"
    form = CopyForm(
        request.POST or None,
        initial={
            "shelf": request.session.get("last_shelf"),
            "token": issue_token(request.user, action),
            "is_public": True,
        },
    )
    if request.method == "POST" and form.is_valid():
        token = validate_token(form, request.user, action)
        if token:
            receipt, created = create_once(
                request.user,
                action,
                token,
                lambda: create_copies(
                    book,
                    form.cleaned_data["shelf"],
                    [form.cleaned_data["volume"]],
                    form.cleaned_data["is_public"],
                ),
            )
            if created:
                remember(request, form.cleaned_data["shelf"])
            announce(request, receipt, created)
            return redirect("librarian:book_detail", pk=book.pk)
    return render(request, "librarian/copy_form.html", {"form": form, "book": book, "heading": "add_copy"})


@librarian_required("catalog.change_copy", "catalog.view_edition")
@require_http_methods(["GET", "POST"])
def copy_edit(request, pk):
    copy = get_object_or_404(Copy.objects.select_related("edition"), pk=pk)
    form = CopyForm(request.POST or None, instance=copy)
    if request.method == "POST" and form.is_valid():
        form.save()
        remember(request, form.cleaned_data["shelf"])
        messages.success(request, ui("saved"))
        return redirect("librarian:book_detail", pk=copy.edition_id)
    return render(
        request,
        "librarian/copy_form.html",
        {"form": form, "book": copy.edition, "copy": copy, "heading": "edit_copy"},
    )


@librarian_required("catalog.add_copy", "catalog.view_edition")
@require_http_methods(["GET", "POST"])
def volumes(request, pk):
    book = get_object_or_404(Edition, pk=pk)
    action = f"volumes:add:{book.pk}"
    form = VolumeForm(
        request.POST or None,
        initial={"shelf": request.session.get("last_shelf"), "token": issue_token(request.user, action)},
    )
    preview = False
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        token = validate_token(form, request.user, action)
        if token:
            if request.POST.get("intent") == "confirm":
                try:
                    payload = signing.loads(data["preview_token"], salt="rumi-volume-preview", max_age=86400)
                    if (
                        payload != {"token": str(token), "start": data["start"], "end": data["end"]}
                        or "volume_labels" not in data
                    ):
                        raise ValueError
                except (signing.BadSignature, ValueError, TypeError):
                    form.add_error(None, ui("preview_required"))
                else:
                    receipt, created = create_once(
                        request.user,
                        action,
                        token,
                        lambda: create_copies(book, data["shelf"], data["volume_labels"], data["is_public"]),
                    )
                    if created:
                        remember(request, data["shelf"])
                    announce(request, receipt, created)
                    return redirect("librarian:book_detail", pk=book.pk)
            else:
                posted = request.POST.copy()
                posted["labels"] = data.get("labels") or "\n".join(
                    str(number) for number in range(data["start"], data["end"] + 1)
                )
                posted["preview_token"] = signing.dumps(
                    {"token": str(token), "start": data["start"], "end": data["end"]},
                    salt="rumi-volume-preview",
                )
                form = VolumeForm(posted)
                preview = form.is_valid()
    return render(request, "librarian/volumes.html", {"form": form, "book": book, "preview": preview})


METADATA = {
    "shelves": (Shelf, ShelfForm),
    "categories": (Category, CategoryForm),
    "contributors": (Contributor, ContributorForm),
}


def metadata_model(kind):
    if kind not in METADATA:
        raise Http404
    return METADATA[kind]


@never_cache
@require_safe
def metadata_list(request, kind):
    model, _ = metadata_model(kind)

    @librarian_required(f"catalog.view_{model._meta.model_name}")
    def page(request):
        query = request.GET.get("q", "")[:200]
        records = model.objects.all()
        if model is Shelf:
            records = records.annotate(copy_count=Count("copies"))
        records = list(records.order_by("pk"))
        if query:
            fields = {
                Shelf: ["label", "description"],
                Category: ["slug", "name", "name_ur", "name_ar"],
                Contributor: ["name"],
            }[model]
            records = [
                record
                for record in records
                if any(normalize(query) in normalize(getattr(record, field)) for field in fields)
            ]
        return render(
            request,
            "librarian/metadata_list.html",
            {
                "kind": kind,
                "query": query,
                "parameters": urlencode({"q": query}),
                "page_obj": Paginator(records, 20).get_page(request.GET.get("page", "")[:10]),
            },
        )

    return page(request)


@never_cache
@require_http_methods(["GET", "POST"])
def metadata_edit(request, kind, pk=None):
    model, form_class = metadata_model(kind)
    permission = "change" if pk else "add"

    @librarian_required(f"catalog.{permission}_{model._meta.model_name}")
    def page(request):
        record = get_object_or_404(model, pk=pk) if pk else None
        form = form_class(request.POST or None, instance=record)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, ui("saved"))
            return redirect("librarian:metadata_list", kind=kind)
        return render(request, "librarian/metadata_form.html", {"form": form, "kind": kind, "record": record})

    return page(request)
