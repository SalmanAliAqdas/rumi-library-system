# Phase 3 offline catalogue

Entry point: `/offline/`. Public snapshot: `/catalog/public-snapshot.json`.
Local detail route: `/offline/?book=<edition id>`. Stable normal online detail URLs
remain `/books/<edition id>/`; these server-rendered pages are not cached. Offline
links always use the offline route, so an unvisited saved book can open or refresh.
The manifest starts and scopes the installed experience to `/offline/`.

## Public snapshot and database consistency

`catalog/offline.py` explicitly constructs each record from shared `public_editions`
and `public_copies` queries. The only copy fields are accession, volume, shelf label
and availability boolean. Edition fields are public metadata, translated categories,
languages, contributor names/roles, aliases, normalized search data, demo indicator,
cover URL and stable public URL. No model dumps, borrower records/IDs/contacts,
users, submission receipts, shelf descriptions or library settings are exported.
Authentication does not personalize the response. Query parameters never filter the
download; it is always the whole public collection, including currently unvisited
books. The endpoint is GET/HEAD only, no-store, and is never put in CacheStorage.

Schema version 1 and normalization version 1 are explicit. A read transaction covers
the query and all prefetches. SQLite uses its transaction snapshot; PostgreSQL sets
REPEATABLE READ, READ ONLY at the start of a durable transaction. The view opts out
of request-wide atomic transactions to own that boundary. PostgreSQL behavior still
requires a dedicated pre-production test; Phase 3 was verified on SQLite only.

Configured safety bounds: 5,000 public editions, 10,000 public copies, 20 MiB UTF-8
JSON. Exceeding any bound returns 503 `snapshot_limit_exceeded`, never a partial
catalogue. Limits are Django settings; changing the schema/client limits requires
coordinated review. Client validation also bounds arrays/text, verifies unique IDs
and accessions, counts, required/unknown keys, URLs, types and normalized data.
Invalid/missing/future schema data is rejected without replacing a working copy.

## IndexedDB and concurrency

Database: `rumi-library-public-offline`, schema version 1. Stores: `state` and
`covers`. The active state is one bounded snapshot record with a local UUID revision,
download time and cover revision. Downloads use credentials omitted, redirect errors,
no HTTP cache, a 45-second abort timeout, bounded streamed byte reading, JSON decoding
and complete validation **before** any replacement transaction.

A readwrite transaction compares the local base revision and writes the entire new
state and clears old covers atomically. Competing tabs serialize through IndexedDB:
only one write from the same base revision can succeed; the other gets a recoverable
conflict. Removal writes a new empty revision/tombstone, so an in-flight old download
cannot resurrect removed data. Failed network/validation/quota/transaction updates
leave the previous snapshot and timestamp intact. Transaction completion is awaited,
not just individual put success. Timeouts/storage-blocked errors are recoverable;
there is no permanent spinner. BroadcastChannel and focus refresh synchronize
views across tabs. No private data or offline mutations/synchronization are stored.

Storage can be evicted or cleared, including installed PWAs. A browser/OS crash or
disk failure is not a database backup guarantee. The empty state explains how to
download again. Each device and origin (including different localhost ports) has
its own copy. Hiding/removing public records cannot retract earlier copies remotely.

## Search, rendering and assets

Python exports original display text alongside normalized strings. Browser queries
use the same normalization specification as `docs/SEARCH.md`, with a generated
Python Unicode casefold/whitespace table rather than assuming JavaScript lower-case
matches casefold. Unicode compatibility normalization is still provided by each
runtime; shared fixtures explicitly cover English, Urdu/Arabic marks/variants,
mixed script, full-width Latin, accents, Greek sigma and German sharp S. Unknown
future Unicode differences fail normalized-data validation rather than silently
accepting incompatible saved records. The table is generated from the Python
Unicode version recorded in `static/offline/unicode-data.js`.

Rank tiers, eligible-copy availability behavior and stable tie ordering match Python.
No fuzzy matching or translation is added. Aliases are recorded, not inferred.
Search is submit-driven and in memory; only twelve cards render at once. A test
exercises ten searches over 1,000 synthetic editions. This is a bounded home-library
catalogue, not an unlimited search index. All catalogue text renders through DOM
textContent/text nodes, never innerHTML. Public URL and image protocols are validated.

Icons are project-owned code drawings from `scripts/build_offline_assets.py`.
The helper also generates Unicode data and the offline English/Urdu/Arabic label
module from the existing Python label catalogues. To rebuild after translation
changes: `python scripts/build_offline_assets.py`. Commit intentional generated
interface assets; never commit browser screenshots, databases or private fixtures.
Existing OFL fonts are served and cached locally with their licenses preserved.

## Service worker, privacy and upgrades

Worker: `/offline/sw.js`, scope **only `/offline/`**. It intercepts GET only, with
an exact same-origin asset allowlist and a query-independent `/offline/` navigation
shell key. A plain non-personalized template is rendered without a request/context
processors: no CSRF token, auth/session content or private settings. Normal catalogue
pages, snapshots, private APIs, librarian/admin/login routes and all non-GET requests
are not cached, queued, replayed or given an offline public fallback.

Allowlisted assets include canonical JS module paths, manifest/icons, and the exact
static-storage CSS/font URLs (manifest-hashed in production). Installer fetches omit
credentials, reject errors/redirects and complete before worker activation. Cache
names hash the source interface/assets. Failed installation deletes only that new
cache and keeps the active worker/catalogue. Activation cleans only obsolete
`rumi-library-offline-shell-*` caches. There is no skipWaiting, clients.claim or forced
reload. Close old offline tabs/windows then reopen online to adopt a waiting worker.
An interface update does not automatically download inventory. Future schema
changes must preserve the previous IndexedDB record until replacement validation
and storage succeed; do not use destructive onupgradeneeded resets.

Registration occurs only on visiting the offline page, not management pages.
Installation prompts are browser-dependent; the button stays hidden without an
actual beforeinstallprompt event. HTTPS/localhost is required. Physical Samsung/OS
installation and browsers other than automated Chromium remain manual checks.

## Optional covers

Core browsing makes no external cover requests. Covers download only on a separate
click: up to 100 unique HTTP(S) URLs, three concurrent CORS requests, credentials
omitted, no referrer, no redirects, 12-second per-image timeout and 2 MiB per-image
limit. Only PNG/JPEG/WebP/GIF/AVIF MIME types are accepted. Stored covers are bounded
to 20 MiB total and checked transactionally, including across tabs. There can be
limited in-flight network overhead around byte caps. No server cover proxy exists.
CORS/network/MIME/size failures use placeholders and leave text untouched.

Covers live in IndexedDB, not arbitrary external CacheStorage entries. Display uses
revoked-on-rerender blob URLs without external fetches. Text updates atomically clear
old covers. Removing covers rotates their revision so in-flight requests in another
tab cannot restore them. Text remains usable if all images fail.

## Manual and automated verification

`RUMI_BROWSER_TESTS=1 python manage.py test tests.test_offline_browser` creates a
separate SQLite test database and Chromium contexts. It covers clean storage,
complete export counts/timestamp, offline reload/search/filter/detail navigation,
unvisited deep links, offline language/RTL/mobile layout, private GET/POST failure,
online update, network/invalid response/quota/transaction abort rollback, real
two-tab stale writes, removal tombstones, blocked storage, valid empty snapshots,
safe text rendering, optional cover success/404/CORS failure and cover removal.
`node --test tests/offline_core.test.mjs` checks shared normalization/ranking fixtures,
schema validation, byte bounds and 1,000-edition search. Django tests check snapshot
allowlists, privacy, hidden records, counts, limits, manifest/icons and worker policy.

For a laptop: download online, disable network in DevTools or stop the server,
reload `/offline/`, search in all scripts, combine filters, open an unvisited book,
verify shelf/copies, switch interface language, try private routes (must fail),
restore connectivity/update, force an unreachable update (old timestamp must remain),
and confirm removal shows an empty state. Check native installation separately.
For a Samsung phone, use an authorized trusted HTTPS origin, or USB localhost
forwarding documented in README. Stop/unplug that connection after download for a
real offline test. Plain LAN HTTP does not meet secure-context requirements.

References checked November 3, 2026:
[service workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers),
[IndexedDB transactions](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Using_IndexedDB),
[installability](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable),
[Android localhost access](https://developer.android.com/develop/ui/views/layout/webapps/access-local-server).
