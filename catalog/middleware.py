import hashlib
import logging

from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone


class PrivateLogFilter(logging.Filter):
    def filter(self, record):
        category = "general"
        if record.exc_info and record.exc_info[1]:
            message = str(record.exc_info[1]).lower()
            for fragment, safe_category in [
                ("certificate verify failed", "tls_verification"),
                ("permission denied", "database_permission"),
                ("does not exist", "missing_database_object"),
                ("staticfiles manifest", "static_manifest"),
                ("could not connect", "database_connection"),
                ("connection failed", "database_connection"),
                ("timed out", "timeout"),
            ]:
                if fragment in message:
                    category = safe_category
                    break
        record.msg = f"application event ({category})"
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


class SecurityBoundaries:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .models import LookupGate

        if request.method == "POST" and request.path in {"/librarian/login/", "/admin/login/"}:
            # Shared bounded buckets keyed by username, independent of spoofed proxy headers.
            # Hash collisions can conservatively throttle another user; no usernames/IPs stored.
            bucket = (
                100
                + int.from_bytes(
                    hashlib.sha256(request.POST.get("username", "")[:150].casefold().encode()).digest()[:2],
                    "big",
                )
                % 256
            )
            now = timezone.now()
            with transaction.atomic():
                LookupGate.objects.get_or_create(pk=bucket, defaults={"next_at": now})
                LookupGate.objects.filter(pk=bucket, next_at__lte=now).update(
                    next_at=now + timezone.timedelta(minutes=5), count=0
                )
                allowed = LookupGate.objects.filter(pk=bucket, count__lt=10).update(count=F("count") + 1)
            if not allowed:
                from .templatetags.library_ui import ui

                response = HttpResponse(
                    ui("login_throttled"), status=429, content_type="text/plain; charset=utf-8"
                )
                response["Retry-After"] = "300"
                response["Cache-Control"] = "no-store"
                response["X-Robots-Tag"] = "noindex, nofollow"
                return response
        response = self.get_response(request)
        if (
            request.path.startswith(
                ("/admin/", "/librarian/", "/i18n/", "/catalog/", "/offline/", "/health/")
            )
            or request.GET
            or response.status_code >= 400
        ):
            response["X-Robots-Tag"] = "noindex, nofollow"
        if request.path.startswith(("/admin/", "/librarian/")):
            response["Cache-Control"] = "private, no-store"
        if not request.path.startswith("/admin/") and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' https:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
            )
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
