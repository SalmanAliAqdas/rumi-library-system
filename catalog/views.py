from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from .forms import SearchForm
from .models import Category, Copy, Edition, Language, Loan
from .search import ranked_books


def public_copies():
    return (
        Copy.objects.filter(is_public=True)
        .select_related("shelf")
        .annotate(on_loan=Exists(Loan.objects.filter(copy=OuterRef("pk"), returned_date__isnull=True)))
    )


def public_editions():
    return (
        Edition.objects.filter(copies__is_public=True)
        .distinct()
        .prefetch_related(
            "categories",
            "languages",
            "credits__contributor",
            Prefetch("copies", queryset=public_copies(), to_attr="visible_copies"),
        )
    )


def home(request):
    return render(
        request,
        "catalog/home.html",
        {
            "books": public_editions()[:8],
            "edition_count": public_editions().count(),
            "copy_count": public_copies().count(),
            "language_count": Language.objects.filter(edition__copies__is_public=True).distinct().count(),
            "categories": Category.objects.annotate(
                public_count=Count("edition", filter=Q(edition__copies__is_public=True), distinct=True)
            )
            .filter(public_count__gt=0)
            .order_by("name"),
        },
    )


def detail(request, pk):
    return render(request, "catalog/detail.html", {"book": get_object_or_404(public_editions(), pk=pk)})


def copy_detail(request, accession):
    from .copy_links import copy_url, whatsapp_url

    copy = get_object_or_404(public_copies().select_related("edition"), accession=accession)
    return render(
        request,
        "catalog/copy.html",
        {
            "copy": copy,
            "book": copy.edition,
            "public_url": copy_url(copy),
            "whatsapp_url": whatsapp_url(copy),
        },
    )


def search(request):
    form = SearchForm(request.GET)
    results = []
    if form.is_valid():
        data = form.cleaned_data
        books = public_editions()
        if data["category"]:
            books = books.filter(categories__slug=data["category"])
        if data["language"]:
            books = books.filter(languages__code=data["language"])
        results = ranked_books(books.distinct(), data["q"], availability=data["availability"])
    parameters = request.GET.copy()
    for key in list(parameters):
        if key not in {"q", "category", "language", "availability", "display"}:
            parameters.pop(key)
        else:
            parameters[key] = parameters[key][:200]
    return render(
        request,
        "catalog/search.html",
        {
            "page_obj": Paginator(results, 12).get_page(request.GET.get("page", "")[:10]),
            "search_form": form,
            "query": request.GET.get("q", "")[:200],
            "parameters": parameters.urlencode(),
            "categories": Category.objects.filter(edition__copies__is_public=True).distinct(),
            "languages": Language.objects.filter(edition__copies__is_public=True).distinct(),
        },
    )


def permission_denied(request, exception):
    return render(request, "403.html", status=403)
