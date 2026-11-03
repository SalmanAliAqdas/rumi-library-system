"""Canonical public links, never derived from a request Host header."""

import ipaddress
import re
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import URLValidator
from django.urls import reverse

from .models import LibrarySettings
from .templatetags.library_ui import ui


def canonical_site_url(value):
    try:
        URLValidator(schemes=["http", "https"])(value)
        parts = urlsplit(value)
        if parts.username or parts.password or parts.query or parts.fragment or parts.path not in {"", "/"}:
            raise ValueError
        if len(value) > 250:
            raise ValueError
        return value.rstrip("/")
    except (ValidationError, ValueError, TypeError):
        raise ImproperlyConfigured("SITE_URL must be an HTTP(S) origin without credentials, path or query")


def copy_url(copy):
    return canonical_site_url(settings.SITE_URL) + reverse("copy_detail", args=[copy.accession])


def temporary_site():
    host = urlsplit(settings.SITE_URL).hostname.lower()
    try:
        local_ip = ipaddress.ip_address(host).is_private
    except ValueError:
        local_ip = False
    return (
        not settings.SITE_URL_CONFIGURED
        or local_ip
        or host in {"localhost", "127.0.0.1", "::1"}
        or "." not in host
        or host.endswith(
            (
                ".vercel.app",
                ".ngrok.io",
                ".ngrok-free.app",
                ".trycloudflare.com",
                ".local",
                ".test",
                ".invalid",
            )
        )
    )


def whatsapp_url(copy):
    library = LibrarySettings.objects.first()
    number = (
        library.whatsapp_number if library and library.whatsapp_number else settings.WHATSAPP_NUMBER
    ).strip()
    # E.164 shape: explicit international country code, 8–15 digits, no extension.
    if not re.fullmatch(r"\+?[1-9][0-9 ()-]{6,25}", number):
        return ""
    digits = re.sub(r"[ ()+-]", "", number)
    if not re.fullmatch(r"[1-9][0-9]{7,14}", digits):
        return ""
    message = ui("enquiry_message").format(
        title=copy.edition.title, accession=copy.accession, volume=copy.volume or "—", url=copy_url(copy)
    )
    return f"https://wa.me/{digits}?" + urlencode({"text": message})
