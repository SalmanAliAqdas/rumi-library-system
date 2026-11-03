"""Bounded, deterministic catalogue search; original display text is never mutated."""

import re
import unicodedata


def normalize(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    # Only Arabic-script marks; retain Latin accents and distinct Arabic letters.
    value = "".join(
        c
        for c in value
        if c != "ـ"
        and not (
            unicodedata.category(c).startswith("M")
            and (
                0x0610 <= ord(c) <= 0x061A
                or 0x064B <= ord(c) <= 0x065F
                or ord(c) == 0x0670
                or 0x06D6 <= ord(c) <= 0x06ED
            )
        )
    )
    value = value.translate(str.maketrans({"ك": "ک", "ي": "ی", "\u200c": " ", "\u200d": ""}))
    return " ".join(value.split())


def isbn_key(value):
    return re.sub(r"[\s\-‐‑–—]", "", unicodedata.normalize("NFKC", value or "")).upper()


def rank(edition, query, copies):
    if not query:
        return 0
    title = normalize(edition.title)
    aliases = [normalize(alias) for alias in edition.aliases.splitlines() if alias.strip()]
    accessions = [normalize(copy.accession) for copy in copies]
    isbn = isbn_key(edition.isbn)
    query_isbn = isbn_key(query)
    if query in accessions or (isbn and query_isbn and query_isbn == isbn):
        return 0
    if query == title or query in aliases:
        return 1
    if query in title:
        return 2
    if any(query in alias for alias in aliases):
        return 3
    contributors = [normalize(credit.contributor.name) for credit in edition.credits.all()]
    subjects = [
        normalize(getattr(category, field))
        for category in edition.categories.all()
        for field in ("name", "name_ur", "name_ar")
    ]
    if any(query in text for text in contributors + subjects):
        return 4
    if any(query in value for value in accessions) or (isbn and query_isbn and query_isbn in isbn):
        return 5
    if query in normalize(edition.summary):
        return 6
    return None


def ranked_books(books, query="", *, availability="", shelf="", visibility=""):
    query = normalize(query)
    matches = []
    for book in books:
        copies = list(book.search_copies if hasattr(book, "search_copies") else book.visible_copies)
        if shelf:
            copies = [copy for copy in copies if str(copy.shelf_id) == str(shelf)]
        if visibility:
            copies = [copy for copy in copies if copy.is_public == (visibility == "public")]
        # Availability and copy-level filters must refer to the same physical copy.
        if availability:
            copies = [copy for copy in copies if copy.on_loan == (availability == "on_loan")]
        if not copies and (availability or shelf or visibility):
            continue
        score = rank(book, query, copies)
        if score is not None:
            matches.append((score, normalize(book.title), book.pk, book))
    return [item[3] for item in sorted(matches, key=lambda item: item[:3])]
