"""Public discovery uses configured origin, never request Host or private fields."""

from xml.sax.saxutils import escape

from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_safe

from .copy_links import canonical_site_url
from .models import Copy, Edition


def origin():
    from django.conf import settings

    return canonical_site_url(settings.SITE_URL)


@require_safe
def sitemap(request):
    # Paginate using a standard sitemap index so no response grows with the whole library.
    page = request.GET.get("page", "")
    editions = (
        Edition.objects.filter(copies__is_public=True).distinct().order_by("pk").values_list("pk", flat=True)
    )
    copies = Copy.objects.filter(is_public=True).order_by("pk").values_list("accession", flat=True)
    edition_count = editions.count()
    total = 2 + edition_count + copies.count()
    if not page:
        count = (total + 999) // 1000
        body = '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        body += "".join(
            f"<sitemap><loc>{escape(origin())}/sitemap.xml?page={n}</loc></sitemap>"
            for n in range(1, count + 1)
        )
        body += "</sitemapindex>"
    else:
        if (
            not page.isascii()
            or not page.isdigit()
            or len(page) > 6
            or not 1 <= int(page) <= (total + 999) // 1000
        ):
            return HttpResponse(status=404)
        start = (int(page) - 1) * 1000
        end = start + 1000
        routes = ["/", "/books/"][start:end]
        routes += [reverse("detail", args=[pk]) for pk in editions[max(0, start - 2) : max(0, end - 2)]]
        routes += [
            reverse("copy_detail", args=[accession])
            for accession in copies[max(0, start - 2 - edition_count) : max(0, end - 2 - edition_count)]
        ]
        body = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        body += "".join(f"<url><loc>{escape(origin() + route)}</loc></url>" for route in routes)
        body += "</urlset>"
    return HttpResponse(body, content_type="application/xml")


@require_safe
def robots(request):
    return HttpResponse(
        "User-agent: *\nDisallow: /librarian/\nDisallow: /admin/\nDisallow: /i18n/\nDisallow: /catalog/\nDisallow: /books/?\nSitemap: "
        + origin()
        + "/sitemap.xml\n",
        content_type="text/plain",
    )


@require_safe
def health(request):
    # Liveness only; does not query the database, inventory or environment.
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response
