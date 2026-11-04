"""Optional, bounded Open Library suggestions. No provider URL is followed."""

import json
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django import forms
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from .models import LookupGate
from .templatetags.library_ui import ui

FIELDS = {"title": 300, "isbn": 32, "publisher": 200, "year": 4, "summary": 6000, "cover_url": 200}
SALT = "rumi-metadata-v1"


class LookupError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LookupError


class LookupForm(forms.Form):
    lookup_isbn = forms.CharField(required=False, max_length=32)
    lookup_title = forms.CharField(required=False, max_length=200)
    lookup_author = forms.CharField(required=False, max_length=120)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["dir"] = "ltr" if name == "lookup_isbn" else "auto"

    def clean(self):
        data = super().clean()
        isbn = re.sub(r"[\s-]", "", data.get("lookup_isbn", "")).upper()
        if isbn and not re.fullmatch(r"(?:\d{9}[\dX]|\d{13})", isbn):
            raise forms.ValidationError(ui("lookup_input"))
        if not isbn and not data.get("lookup_title"):
            raise forms.ValidationError(ui("lookup_input"))
        data["lookup_isbn"] = isbn
        return data


def reserve_request():
    # Shared database gate, including across serverless instances. No in-memory counters.
    now = timezone.now()
    with transaction.atomic():
        gate, _ = LookupGate.objects.get_or_create(pk=1, defaults={"next_at": now})
        changed = LookupGate.objects.filter(pk=gate.pk, next_at__lte=now).update(
            next_at=now + timezone.timedelta(seconds=2)
        )
    if not changed:
        raise LookupError


def fetch(path, params=None):
    reserve_request()
    url = "https://openlibrary.org" + path
    if params:
        url += "?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "RumiLibrary/1.0", "Accept": "application/json"})
    try:
        with build_opener(NoRedirect).open(request, timeout=4) as response:
            # Total deadline as well as per-socket timeout, no compressed response requested.
            deadline = time.monotonic() + 5
            body = bytearray()
            while True:
                chunk = response.read(16384)
                body.extend(chunk)
                if len(body) > 512 * 1024 or time.monotonic() > deadline:
                    raise LookupError
                if not chunk:
                    break
            result = json.loads(body)
            if not isinstance(result, dict):
                raise LookupError
            return result
    except (HTTPError, URLError, TimeoutError, socket.timeout, ValueError, OSError, RecursionError) as error:
        raise LookupError from error


def clean_text(value, maximum):
    if isinstance(value, dict):
        value = value.get("value", "")
    if not isinstance(value, str):
        return ""
    return strip_tags(value[: maximum * 2]).strip()[:maximum]


def strings(value):
    return [item for item in value[:5] if isinstance(item, str)] if isinstance(value, list) else []


def suggestion(record, *, isbn=""):
    if not isinstance(record, dict):
        return None
    key = record.get("key", "")
    if not isinstance(key, str) or not re.fullmatch(r"/(?:works/OL\d+W|books/OL\d+M)", key):
        return None
    title = clean_text(record.get("title"), 300)
    if not title:
        return None
    publishers = strings(record.get("publishers", record.get("publisher", [])))
    date = clean_text(record.get("publish_date"), 100)
    year = record.get("first_publish_year")
    match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", date)
    if match:
        year = int(match[0])
    if type(year) is not int or not 1 <= year <= 9999:
        year = ""
    isbns = strings(record.get("isbn_13", record.get("isbn", [])))
    candidate = isbn or next((x for x in isbns if re.fullmatch(r"\d{9}[\dX]|\d{13}", x)), "")
    cover = record.get("cover_i")
    if not cover:
        covers = record.get("covers", [])
        cover = covers[0] if isinstance(covers, list) and covers else None
    cover_url = (
        f"https://covers.openlibrary.org/b/id/{cover}-M.jpg"
        if type(cover) is int and 0 < cover < 10**12
        else ""
    )
    return {
        "fields": {
            "title": title,
            "isbn": candidate,
            "publisher": clean_text(publishers[0], 200) if publishers else "",
            "year": str(year),
            "summary": clean_text(record.get("description"), 6000),
            "cover_url": cover_url,
        },
        "contributors": [clean_text(x, 200) for x in strings(record.get("author_name", []))],
        "date": date or str(year),
        "source": "https://openlibrary.org" + key,
        "retrieved": timezone.now().isoformat(),
    }


def lookup(data):
    isbn = data["lookup_isbn"]
    if isbn:
        # Books API avoids ISBN endpoint redirects. Never follow returned links.
        payload = fetch("/api/books", {"bibkeys": "ISBN:" + isbn, "format": "json", "jscmd": "details"})
        entry = payload.get("ISBN:" + isbn, {})
        record = entry.get("details", {}) if isinstance(entry, dict) else {}
        if isinstance(record, dict):
            authors = record.get("authors", [])
            record["author_name"] = (
                [a.get("name", "") for a in authors[:5] if isinstance(a, dict)]
                if isinstance(authors, list)
                else []
            )
        result = suggestion(record, isbn=isbn)
        return [result] if result else []
    params = {
        "title": data["lookup_title"],
        "limit": 5,
        "fields": "key,title,author_name,publisher,first_publish_year,isbn,cover_i",
    }
    if data["lookup_author"]:
        params["author"] = data["lookup_author"]
    docs = fetch("/search.json", params).get("docs", [])
    if not isinstance(docs, list):
        raise LookupError
    return [result for record in docs[:5] if (result := suggestion(record))]


def signed_result(result, user):
    return signing.dumps({"user": user.pk, "result": result}, salt=SALT, compress=True)


def read_result(token, user, max_age=3600):
    payload = signing.loads(token, salt=SALT, max_age=max_age)
    if payload["user"] != user.pk:
        raise signing.BadSignature
    return payload["result"]


def draft_action(request):
    """Return draft POST data and preview context, never save inventory."""
    posted = request.POST.copy()
    context = {"lookup_form": LookupForm(request.POST or None)}
    intent = posted.get("intent")
    if intent == "lookup":
        form = context["lookup_form"]
        if form.is_valid():
            try:
                results = lookup(form.cleaned_data)
                context["lookup_results"] = [
                    {
                        **result,
                        "token": signed_result(result, request.user),
                        "choices": [
                            (name, value, not bool(posted.get(name)))
                            for name, value in result["fields"].items()
                            if value
                        ],
                    }
                    for result in results
                ]
                if not results:
                    context["lookup_message"] = ui("lookup_empty")
            except LookupError:
                context["lookup_message"] = ui("lookup_unavailable")
    elif intent == "apply_metadata":
        try:
            result = read_result(posted.get("suggestion", "")[:20000], request.user)
            selected = set(posted.getlist("approve")) & FIELDS.keys()
            replacing = any(
                posted.get(name) and posted.get(name) != result["fields"][name] for name in selected
            )
            if replacing and posted.get("replace_confirm") != "on":
                context["lookup_message"] = ui("lookup_replace")
            else:
                for name in selected:
                    posted[name] = result["fields"][name]
                if selected:
                    posted["metadata_token"] = posted["suggestion"]
                context["lookup_message"] = ui("lookup_applied")
        except (signing.BadSignature, KeyError, TypeError, ValueError):
            context["lookup_message"] = ui("lookup_expired")
    return posted if request.method == "POST" else None, context
