"""Public-only snapshot and non-personalized offline interface resources."""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from .search import isbn_key, normalize
from .views import public_copies, public_editions

SCHEMA_VERSION = 1


class SnapshotLimit(Exception):
    pass


def edition_record(book):
    aliases = book.aliases.splitlines()
    contributors = [{"name": credit.contributor.name, "role": credit.role} for credit in book.credits.all()]
    categories = [
        {
            "slug": category.slug,
            "name": category.name,
            "name_ur": category.name_ur,
            "name_ar": category.name_ar,
        }
        for category in book.categories.all()
    ]
    copies = [
        {
            "accession": copy.accession,
            "volume": copy.volume,
            "shelf": copy.shelf.label,
            "available": not copy.on_loan,
        }
        for copy in book.visible_copies
    ]
    return {
        "id": book.pk,
        "title": book.title,
        "original_language": book.original_language,
        "aliases": aliases,
        "contributors": contributors,
        "languages": [{"code": language.code, "name": language.name} for language in book.languages.all()],
        "categories": categories,
        "isbn": book.isbn,
        "publisher": book.publisher,
        "edition": book.edition,
        "year": book.year,
        "summary": book.summary,
        "cover_url": book.cover_url,
        "is_demo": book.is_demo,
        "url": reverse("detail", args=[book.pk]),
        "copies": copies,
        "search": {
            "title": normalize(book.title),
            "aliases": [normalize(alias) for alias in aliases],
            "contributors": [normalize(person["name"]) for person in contributors],
            "subjects": [
                normalize(category[field])
                for category in categories
                for field in ("name", "name_ur", "name_ar")
            ],
            "isbn": isbn_key(book.isbn),
            "summary": normalize(book.summary),
        },
    }


def snapshot_bytes():
    # Each backend sees one database snapshot for the main query and all prefetches.
    with transaction.atomic(durable=True):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        generated_at = timezone.now().isoformat(timespec="microseconds")
        if public_copies().count() > settings.OFFLINE_MAX_COPIES:
            raise SnapshotLimit
        books = list(public_editions().order_by("pk")[: settings.OFFLINE_MAX_EDITIONS + 1])
        if len(books) > settings.OFFLINE_MAX_EDITIONS:
            raise SnapshotLimit
        records = [edition_record(book) for book in books]
        copy_count = sum(len(book["copies"]) for book in records)
        if copy_count > settings.OFFLINE_MAX_COPIES:
            raise SnapshotLimit
        snapshot = {
            "schema_version": SCHEMA_VERSION,
            "normalization_version": 1,
            "generated_at": generated_at,
            "edition_count": len(records),
            "copy_count": copy_count,
            "editions": records,
        }
        encoded = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > settings.OFFLINE_MAX_BYTES:
            raise SnapshotLimit
        return encoded


@transaction.non_atomic_requests
@require_safe
def snapshot(request):
    try:
        response = HttpResponse(snapshot_bytes(), content_type="application/json; charset=utf-8")
    except SnapshotLimit:
        response = JsonResponse(
            {"error": "snapshot_limit_exceeded", "schema_version": SCHEMA_VERSION}, status=503
        )
        response["X-Rumi-Snapshot-Error"] = "limit"
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def public_template(name, content_type, context=None):
    # No request: no auth/session/CSRF/library-settings context processors.
    response = HttpResponse(get_template(name).render(context or {}), content_type=content_type)
    response["Cache-Control"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_safe
def shell(request):
    response = public_template("offline/shell.html", "text/html; charset=utf-8")
    response["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; font-src 'self'; connect-src 'self' https: http:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    return response


@require_safe
def service_worker(request):
    plain_assets = [
        "offline/" + name
        for name in (
            "app.js",
            "search.js",
            "snapshot.js",
            "store.js",
            "labels.js",
            "unicode-data.js",
            "manifest.webmanifest",
            "icon-192.png",
            "icon-512.png",
        )
    ]
    styled_assets = [
        "css/library.css",
        "offline/offline.css",
        "fonts/Newsreader.ttf",
        "fonts/NotoNaskhArabic.ttf",
        "fonts/NotoNastaliqUrdu.ttf",
    ]
    # JS module imports and manifest icons use canonical paths, not manifest-hashed aliases.
    assets = (
        ["/offline/"]
        + [settings.STATIC_URL + name for name in plain_assets]
        + [staticfiles_storage.url(name) for name in styled_assets]
    )
    digest = hashlib.sha256()
    for name in plain_assets + styled_assets:
        digest.update((Path(settings.BASE_DIR) / "static" / name).read_bytes())
    for name in ("shell.html", "sw.js"):
        digest.update((Path(settings.BASE_DIR) / "templates" / "offline" / name).read_bytes())
    return public_template(
        "offline/sw.js",
        "application/javascript; charset=utf-8",
        {"assets_json": json.dumps(assets), "version": digest.hexdigest()[:20]},
    )
