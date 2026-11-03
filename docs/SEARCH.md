# Phase 2 catalogue search

Search is deterministic Python over ORM-prefetched edition records. Category and
book-language filtering happens through the ORM first. Public queries start with
editions having public copies and prefetch **only public copies**. Copy availability
is an `Exists` expression over active loans; no borrower fields are read into the
search dataset. Management uses a separately permission-checked queryset that may
include hidden copies. It never searches borrower names or contacts.

At roughly 1,000 copies, scanning the selected catalogue in memory is a deliberate
tradeoff: the same behavior on SQLite/PostgreSQL, Unicode case folding independent
of database collation, no stored normalized fields, no backfill and no stale index
after admin, custom form, `loaddata`, relation edits or ORM imports. It is linear in
catalogue size, loads matching candidates before pagination and is not a design
for an unbounded public collection. Revisit indexing after measuring a larger
collection; no PostgreSQL-only extension or fuzzy path is introduced here.

## Normalization

`catalog/search.py` applies the same helper to queries and source text at read time.
Original stored titles, contributor names, categories, aliases and summaries never
change during search.

1. Unicode NFKC normalizes compatibility/presentation forms and full-width Latin.
2. Unicode casefold handles English/mixed-script case consistently.
3. Remove tatweel U+0640 and Arabic-script combining marks from U+0610–061A,
   U+064B–065F, U+0670 and U+06D6–06ED (only characters with Mark categories).
   This makes ordinary optional vocalization/shadda irrelevant to matching.
4. Arabic kaf `ك` maps to Urdu/Persian kaf `ک`; Arabic yeh `ي` maps to Urdu/Persian
   yeh `ی`. These are selected keyboard/script variants only.
5. ZWNJ becomes a space, ZWJ is removed, Unicode whitespace collapses to one space,
   and surrounding whitespace is removed.

We deliberately retain distinctions between `ة`/`ه`, `ے`/`ی`, `ى`/`ی`, `أ`/`ا`
and `ؤ`/`و`. Latin accents are retained. These conservative rules do not translate
or transliterate. `Bukhari` finds `بخاری` only if an appropriate recorded alias or
other matching catalogue text exists. Record alternative titles and Roman Urdu
aliases one per line so each can be ranked as an exact alias.

ISBN comparison additionally removes Unicode whitespace and common hyphens/dashes
and uppercases X. ISBN remains optional; this phase does not assert checksum
validity or ISBN uniqueness across editions/copies.

## Ordering and filters

Rank tiers, lowest first:

0. Exact visible accession or normalized ISBN.
1. Exact normalized title or one whole alias line.
2. Partial title.
3. Partial alias.
4. Contributor or category name in English, Urdu or Arabic.
5. Partial accession/ISBN.
6. Summary.

Ties sort by normalized title, then permanent edition primary key. Empty search
uses that same stable ordering. The welcome page retains its recent-additions
ordering. Each edition is returned once despite multiple copies, contributors,
categories or languages. The displayed count is editions, not individual copies.

Category, book language and availability combine. Available means at least one
eligible copy has no active loan; on-loan means at least one eligible copy has an
active loan. An edition with both can match either. For an exact accession and an
availability filter, that accession must belong to an eligible copy. Hidden copies
cannot supply public availability or accession matches. Management shelf and
visibility filters similarly operate on the same eligible physical copy.

The interface language cookie changes labels/RTL, never collection-language
filters. Search input is bounded to 200 characters, category identifiers to 50,
language codes to 12, and filter choices are validated. Invalid filters produce
labelled errors and zero results. Pagination inputs are bounded and out-of-range
pages use Django's safe paginator behavior. No raw SQL or user-supplied ordering
is used.

## Phase 3 offline parity

The offline snapshot exports original text and normalized fields, and the browser
uses equivalent query normalization/ranking in `static/offline/search.js`. Shared
fixtures live in `tests/fixtures/search_parity.json`; both Python and Node consume
them. A generated Python casefold/whitespace table handles runtime differences such
as German sharp S and Greek sigma; JavaScript lowercase alone is insufficient.
Offline tie sorting compares Unicode code points, matching Python rather than
locale-dependent ordering. Snapshot validation checks normalized fields against
display text before acceptance. `docs/OFFLINE.md` documents versions and limits.
