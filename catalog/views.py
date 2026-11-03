from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Copy, Edition, Language, Loan


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


def search(request):
    books = public_editions()
    query = request.GET.get("q", "").strip()[:200]
    if query:
        matching_copy = Copy.objects.filter(is_public=True, accession__icontains=query).values("edition_id")
        books = books.filter(
            Q(title__icontains=query)
            | Q(aliases__icontains=query)
            | Q(contributors__name__icontains=query)
            | Q(categories__name__icontains=query)
            | Q(categories__name_ur__icontains=query)
            | Q(categories__name_ar__icontains=query)
            | Q(isbn__icontains=query)
            | Q(pk__in=matching_copy)
        ).distinct()
    category = request.GET.get("category", "")
    language = request.GET.get("language", "")
    if category:
        books = books.filter(categories__slug=category)
    if language:
        books = books.filter(languages__code=language)
    parameters = request.GET.copy()
    parameters.pop("page", None)
    return render(
        request,
        "catalog/search.html",
        {
            "page_obj": Paginator(books.distinct(), 12).get_page(request.GET.get("page")),
            "query": query,
            "selected_category": category,
            "selected_language": language,
            "parameters": parameters.urlencode(),
            "categories": Category.objects.filter(edition__copies__is_public=True).distinct(),
            "languages": Language.objects.filter(edition__copies__is_public=True).distinct(),
        },
    )


def detail(request, pk):
    return render(request, "catalog/detail.html", {"book": get_object_or_404(public_editions(), pk=pk)})
