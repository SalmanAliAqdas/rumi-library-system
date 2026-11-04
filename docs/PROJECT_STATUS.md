# Project status — Phase 6 live deployment

November 5, 2026 (Asia/Karachi). User authorized this deployment. Public catalog:
**https://rumi-library.vercel.app/**. Private login:
**https://rumi-library.vercel.app/librarian/login/**. Room display: `/?display=1`.
Offline catalog: `/offline/`. Public browsing needs no Vercel authentication.
The librarian account was created through the user's private interactive terminal;
no default credentials or password disclosure. A separate temporary restricted
staff account verifies login/logout, metadata drafts and CSV, then is removed.

## Actual resources and data outcome

- Neon Free organization `org-cold-feather-57890093`; dedicated project
  `noisy-bread-19614503` (rumi-library), PostgreSQL 18 database `rumi_library`.
  Production branch `br-wild-credit-az43c4d3`; isolated verification branch
  `br-dry-truth-azak0pak`. Both small computes capped at 0.25 CU.
- Dedicated Vercel Hobby project `prj_jzs3N8jR34Lecm28HUmm7wVp2Kul` (rumi-library)
  in team `rumiware1`, linked to SalmanAliAqdas/rumi-library-system, branch main.
  Stable short alias verified as belonging to this project. Secondary owned alias
  rumi-library-rumiware1.vercel.app points to it through canonical metadata.
- Production launched with **0 editions, 0 copies and 0 loans**. Local SQLite
  remains **20 fictional editions / 23 copies / 0 loans**; every edition was marked
  demo and matched the known seed titles/keys. No samples were transferred/deleted.
  No real-data transfer/source backup was needed. Production reference languages
  en/ur/ar were created by migrations. Enter actual shelves and books live.
- SchoolOS, Rumi Enquiry Assistant and other resources were not modified. No paid
  service, billing activation, card-required feature, domain purchase or custom DNS.

## Deployed configuration and fixes

- Reviewed migrations explicitly applied once to verified empty production and
  isolated verification targets: 22 Django migration records, catalog through 0004.
  No build/startup/request migrations, seed or automatic administrator creation.
- Runtime uses pooled `rumi_web`, scoped read/write, with 15-second statement
  timeout; administrative helper uses direct `rumi_owner`. Actual client checks
  confirm TLS with verify-full and no create-database/create-role/superuser runtime
  privileges. Credentials are Vercel sensitive variables and ignored private local
  env files. Existing development .env retained; nothing secret tracked.
- Vercel's first build revealed that Ruff-only pyproject.toml shadowed
  requirements.txt. Ruff moved to ruff.toml. Build logs then confirmed Python 3.13,
  Django 5.2.19, requirements installation, collectstatic and successful deployment.
- Live database reads initially failed because libpq lacked usable trust roots in
  the Vercel runtime. Pinned Certifi 2026.10.23 supplies portable Mozilla roots;
  full certificate/hostname verification remains enforced. Safe error categories
  provide diagnostics without exception bodies, credentials or borrower data.
- Explicit short/secondary allowed hosts and HTTPS CSRF origins; canonical SITE_URL
  is https://rumi-library.vercel.app. HTTP → HTTPS 308 verified. HSTS is deliberately
  3600 seconds with no subdomain inheritance/preload, applied on the final rebuild.
- Production snapshot cap is 4 MiB, below the 4.5 MB function-response ceiling;
  existing friendly failure/old-snapshot preservation remains. Development is 20 MiB.
  Static fonts/icons/manifest and scoped service worker work on the actual CDN.
- Final vercel.json enables Git production deployments only for main; other
  branches do not auto-deploy and have no production credentials. Final pushed
  commit/deployment correspondence is checked using Vercel Git metadata after push.
  No migration automation. A malformed trailing dot in this repository's author
  email was corrected for new commits only; existing history was preserved.

## Checks actually completed

- Full SQLite suite after runtime/TLS changes: **100 tests, 97 passed and 3
  PostgreSQL-only skipped**. All **7 isolated Chromium cases passed**, including
  populated lending/return/availability, QR preview/print PDF, multilingual CSV,
  missing-cover placeholders, metadata approval, mobile RTL and offline flows.
- **29 tests passed on the separate PostgreSQL verification branch, no skips**:
  concurrent accessions, competing loans/retries/returns, shared provider gate,
  private permissions/CSRF, dates/constraints, CSV/formula safety, labels, public
  visibility/privacy/stable URLs, snapshot availability/limits/resources and fixture
  language/audit round trips. Django's disposable test database was destroyed;
  production was never a test target. Initial two failures came from TestCase's
  already-open transaction conflicting with snapshot repeatable-read setup; those
  tests now use TransactionTestCase, preserving production transaction guarantees.
- Follow-up SQLite tests cover the changed transaction harness, log privacy,
  production settings and offline bounds. Ruff lint/format, Django checks,
  migration consistency, applied-migration checks, pip dependency check, Node
  syntax and **5 Node offline tests** passed. Translation completeness/parity passed;
  Python label catalogs require no gettext compilation.
- Production collectstatic passed (147 unchanged files, 400 post-processed).
  `check --deploy` exits 0; only intentional W005/W021 remain for disabled HSTS
  subdomain inheritance/preload. No unresolved dependency, migration or TLS error.
- **Actual live HTTPS Chromium checks passed** in fresh storage: homepage/health,
  canonical/Open Graph, all local fonts/assets/icons/manifest, English/Urdu/Arabic,
  mobile RTL and 1920px display; empty search/filter/page states, sitemap/robots,
  safe production 404, anonymous private redirects and CSRF rejection. Display
  screenshot visually reviewed. Catalog counts are truly zero, no invented stats.
- Live temporary-account login/logout, secure/HttpOnly session cookie, private
  no-store, loans/issue/labels empty pages, authenticated BOM CSV and **real Open
  Library ISBN suggestion** succeeded. Manual draft title preserved, no book saved.
  WhatsApp remains hidden/unconfigured; no message or external submission sent.
- Live empty catalog downloaded with counts/timestamp, reloaded/searchable offline
  in en/ur/ar; private GET/POST unavailable offline. Reconnect/update passed;
  interrupted update retained the previous revision. Worker JavaScript/no-cache and
  cache allowlist verified, excluding snapshots/private pages. Populated unvisited
  book offline behavior was tested in isolation, not by publishing fake inventory.

## Handoff and remaining manual checks

See **docs/LIVE_OPERATIONS.md** for actual IDs, private admin commands, future
main pushes/migrations, errors, free limits, backup/restore/rollback and Samsung/LED
steps. README links the live site. docs/DEPLOYMENT.md links the current operations
guide; earlier phase notes below are historical. The first verified live code is
0906db1; the final documentation/config commit is verified after publishing it.

Daily real entry should use the live librarian area. SQLite is separate; GitHub,
CSV and browser downloads do not back up Neon records. Back up regularly and before
schema changes. No full pg_dump/pg_restore drill was performed: matching client
tools/private backup storage and a separate empty restore target remain required
for that operational exercise, especially before full collection entry.

Shared application throttles and default platform DDoS protection are active. A
custom WAF login rule remains optional/unpublished; the exact free dashboard setup
is in the deployment guide. Physical Samsung/other browsers, OS install,
native-speaker review and actual LED/print/QR scanning remain manual. An empty live
catalog cannot verify real-copy detail/QR content; those populated flows passed
isolated tests. The preview conservatively warns on any vercel.app host; retain
this verified stable alias and inspect one printed destination before a batch.
No additional phase begins automatically.

# Historical Phase 5 handoff

Date: November 5, 2026 (Asia/Karachi). Phase 5 implemented locally. No services
provisioned, accounts inspected, hosted databases accessed, deployment, real
lending, messages, real exports/backups or restores performed. Earlier phase notes
below are historical. Launch is a separately authorized next action.

## Completed

- Optional Open Library ISBN/title/author lookup inside Add a book/Edit edition,
  bounded to one ISBN edition or five work suggestions; multilingual inputs,
  fixed server endpoints, no redirects/arbitrary URL fetches, socket/deadline/byte
  limits, sanitized plain descriptions, validated numeric cover IDs and shared
  database request reservations. Google Books remains disabled, no API keys/billing.
- Explicit field preview/selection; empty fields preselected, nonempty replacement
  requires confirmation, Apply changes only the draft and Save validates normally.
  Contributors are reviewed and added/selected manually with existing role controls.
  Copies/accessions/shelves/volumes/visibility/loans cannot be changed by lookup.
  Last source/retrieval time retained privately; fields remain editable. Manual
  entry works through outages. See docs/METADATA.md for edition/licensing caveats.
- Configured-origin canonical and page-specific multilingual metadata/Open Graph,
  local fallback image, paginated public-only sitemap/index and robots, private
  noindex/no-store and noindex for query variants. Cookie language selection shares
  URLs, so no invented hreflang routes. Existing 404 retained; minimal translated
  production 500 and database-independent health endpoint added. No fabricated
  structured ratings/reviews/inventory. Existing QR URLs preserved.
- Django upgraded to 5.2.19 LTS; production validates required settings and rejects
  SQLite, wildcard hosts/origins and invalid SITE_URL. Psycopg TCP with short-lived
  connections, pooling-compatible cursors and certificate verification/system trust.
  Vercel-only trusted HTTPS proxy, deliberate opt-in HSTS, bounded form bodies,
  CSP/referrer/permissions headers, privacy-filtered application error logging.
- Both login forms share database-backed username-bucket throttles; no claims about
  in-memory counters. Provider reservations are also shared. Exact optional free
  Vercel WAF rule and limitations documented. PostgreSQL concurrency still gated.
- Native Vercel Django configuration with Python 3.13, 30s function duration, static
  asset collection/CDN, bundle exclusions and **Git auto-deployment disabled**.
  No request/build migrations, seeds, default admin or filesystem persistence.
- Concrete schema-aware SQLite to separate PostgreSQL procedure in docs/TRANSFER.md:
  private source backup, natural language keys, preserved identifiers/relationships,
  fresh permissions, PK sequence versus AccessionSequence handling, dry rehearsal,
  full record hashes/counts, visibility/loan checks and untouched-source rollback.
  `audit_catalog` is read-only and emits no borrower details. No transfer write
  command added; deliberate migrate/loaddata remains an operator action.
- docs/DEPLOYMENT.md covers exact account/env/release/static/admin/domain/backup
  steps, free-plan limits checked November 5, 2026, eligibility caveats, remaining
  WAF setup and post-deployment checks. A commercial RumiWare promotion may not
  qualify for Hobby; verify before launch, never silently enable billing.

## Verification actually completed

- Full browser-enabled Django suite: **99 discovered, 96 passed on SQLite,
  3 PostgreSQL-only tests skipped**. All **7 Chromium browser cases passed**:
  existing management, lending/return/public availability/labels/CSV and offline
  cases plus new login → add draft → mocked lookup → missing-field approval →
  preserve manual title → save → public search/detail. New lookup preview also
  checked at a 390px mobile viewport in Urdu/Arabic RTL, without overflow.
  Public mobile and Urdu preview screenshots visually reviewed. Mocked providers
  are deliberate; this is not live provider availability/quota verification.
- After final sitemap pagination/logging changes, **17 targeted server/translation
  tests passed**, including a new 1,004-URL sitemap boundary test and log privacy.
  Total current discovery is 100 tests; the 99-test full run preceded that added
  regression. All final changes were covered by targeted checks.
- Django system checks, migration consistency, applied-migration check, Ruff lint/
  formatting, pip dependency consistency, Node JS syntax and **5 Node offline tests**
  passed. Translation completeness/parity tests passed; Python label catalogs need
  no gettext compilation. Local fonts/PWA assets retained.
- Safe synthetic production configuration: `check --deploy` exit 0 with the single
  expected **security.W004** warning because HSTS is deliberately zero; production
  `collectstatic` passed (128 copied, 19 unchanged, 437 post-processed). Synthetic
  settings tests verify missing requirements/SQLite rejection and connection policy;
  no real PostgreSQL connection was attempted for these checks.
- Additive migration 0004 applied locally without changing existing inventory
  counts: **20 editions, 23 copies, 0 loans, 4 shelves, 3 contributors**. No reset,
  seed or earlier migration replacement. Local data remains separate from Neon.
- Initial new browser failures were missing test reference-language setup and an
  overly exact accessible-link selector; corrected, then targeted and full browser
  runs passed. Initial logging startup import ordering was corrected before checks.

## Remaining launch gates and continuation

No separate authorized PostgreSQL test target/client tools are available here.
SQLite cannot establish PostgreSQL concurrency, pooling, TLS, sequence restoration
or hosted behavior. Run all three PostgreSQL cases (accessions, loans, provider
reservation), full target migrations and private restore rehearsal before launch.
Actual Vercel build/CDN/proxy/HTTPS/WAF and Neon account allowances remain unverified.
Physical phones, other browsers, OS install, actual print/QR scan and native-speaker
review remain manual. Offline downloads cannot be remotely revoked; rank search
still scans a home-size catalogue in Python. Logs deliberately omit exception
bodies; platform access logs need private retention/access settings.

Next user inputs/actions: separate launch authorization, confirmation of personal
noncommercial use, separate Rumi Neon/Vercel targets and final public address.
Provide credentials directly in private environment/account settings, never chat.
Use docs/DEPLOYMENT.md and docs/TRANSFER.md; do not touch other Neon projects.
Real books can be entered gradually. Wait for the final public SITE_URL before
permanent QR labels. No later phase or automatic deployment is started.

Local commands: install requirements-dev.txt, `python manage.py migrate`,
`python manage.py check`, `python manage.py runserver` using .venv/Scripts/python.exe.
The local migration is already applied in this workspace. Existing .env is retained.
Git completion is recorded by the Phase 5 commit and remote branch; inspect history
rather than embedding a self-referential commit hash in this document.

# Historical Phase 4 handoff

Date: November 3, 2026 (Asia/Karachi). Phase 4 only; no deployment, infrastructure,
real lending, messages, backups or restores performed. Earlier phase notes below
are historical.

## Phase 4 completed

- `/librarian/loans/`: private searchable/paginated active loans, overdue filter,
  searchable copy picker, issue form, confirmed POST return and paginated private
  history at `/librarian/copies/<accession>/loans/`. History links also appear in
  Manage books. The existing Loan model, partial unique active-loan constraint,
  signed user/action retry receipts and atomic transactions are reused. PostgreSQL
  copy row locking serializes competing issues; database uniqueness remains the
  final safeguard. Returns use one atomic conditional UPDATE, avoiding SQLite
  read-to-write lock upgrades. Dates use Asia/Karachi; admin shares date validation.
  Returns retain history; repeated returns and same-token issue retries are safe.
- Staff/model permissions on every GET/POST; CSRF and no-store headers retained.
  Loan lists/history require view edition/copy/loan; issue also requires add loan,
  return also requires change loan. Labels/CSV require view edition/copy. Existing
  superusers already have permissions. Borrowers/contacts remain private.
- Immutable accession routes `/copies/<accession>/`, independent of language/title/
  shelf, public visibility checks and saved offline edition links. Absolute URLs
  use validated SITE_URL origins, never request Host headers. Public book URLs and
  snapshot schema remain compatible; public availability comes from active loans.
- Optional WhatsApp links on public book/copy pages use the existing library setting
  with the existing environment fallback. Missing/invalid numbers hide links. Each
  copy has its own translated, encoded title/accession/volume/canonical-URL message.
  International shape validation cannot verify a real WhatsApp account. Links never
  automatically send or reserve. Internet requirements appear online and offline.
- `/librarian/labels/`: shelf/search selection, 1–24 distinct visible copies per
  preview, generated SVG QR codes (Segno 1.6.6, BSD, no transitive dependencies),
  black/white, four-module quiet zones, 34 mm QR size, explicit destinations,
  multilingual titles and A4 browser print/PDF CSS. Local/private IP and known
  preview addresses warn; unconfigured SITE_URL warns. Set a stable domain before
  permanent labels. Arbitrary temporary custom domains cannot be recognized.
- `/librarian/public-catalog.csv`: explicitly public-catalog-only data, one visible
  copy per row, UTF-8 BOM, proper CSV quoting and apostrophe formula protection.
  Hidden copies, loan history, borrower data and private settings are excluded.
  This is not a database backup. Navigation and dashboard describe its purpose.
- All new labels/errors/empty states in English, Urdu and Arabic. Local fonts,
  visible focus, labelled field validation, mixed-script identifiers and responsive
  forms retained. Offline code still caches only its explicit public allowlist;
  labels, exports, lending/auth and all mutations remain network-only. Update the
  saved snapshot explicitly to refresh historical availability.
- No schema changes or migrations. Existing migrations/inventory preserved. Run
  `python -m pip install -r requirements-dev.txt`, `python manage.py migrate`, then
  `python manage.py runserver` using `.venv\Scripts\python.exe` on Windows. Keep
  existing `.env`; fill in SITE_URL and optional WhatsApp number yourself.

Usage/configuration: README Phase 4 section. Separate private backup/restore plan:
`docs/BACKUPS.md`, with official Neon guidance checked November 3, 2026. SQLite
stopped-copy procedure and future direct PostgreSQL dumps to a separate empty test
target are documentation only. Provider history is plan-limited and not a substitute
for private backups; no hosted database or account was accessed.

## Phase 4 verification and limits

- Full suite with Chromium enabled: **82 tests discovered, 80 passed on SQLite,
  2 PostgreSQL concurrency tests skipped**. All six browser cases passed: the
  existing librarian flow, four offline cases and the new Phase 4 flow. The new
  browser case uses isolated fictional records, checks login → issue → public
  borrowed state → confirmation/return → public available state, inspects the
  WhatsApp destination without opening it, exercises Urdu/Arabic mobile forms,
  previews labels, generates an A4 PDF and downloads multilingual UTF-8 CSV.
- Meaningful new server tests cover direct GET/POST permission checks, CSRF,
  dates/application timezone and admin model validation, signed tokens/retries,
  active-loan database uniqueness, transaction rollback, overdue/search/pagination,
  stable/hidden copy links, public/snapshot/export borrower privacy, snapshot
  availability updates, WhatsApp encoding/settings, canonical URLs, label batch
  validation/QR destination and SVG view box, CSV safety and worker exclusions.
- Django system checks, migration consistency and applied-migration checks passed;
  no migration changes. Ruff lint/format, pip dependency check, static collection,
  Node syntax for the changed script and all **5 Node offline tests** passed.
  Translation completeness and generated JS parity pass in the Django suite;
  no gettext compilation applies to this Python label catalogue. Generated offline
  labels were rebuilt with `scripts/build_offline_assets.py`.
- Browser checks initially caught mobile RTL search sizing and visual QR scaling;
  both were fixed. Original copy-edit link ordering was preserved for compatibility.
  The offline cover fixture now supplies an explicit mismatched CORS origin because
  mocked responses can otherwise receive a permissive header. Final tests passed
  with the genuine CORS rejection behavior retained. Print/mobile screenshots and
  test PDF are ignored artifacts; the label print screenshot was visually reviewed.

PostgreSQL is not available locally: SQLite cannot establish production concurrency.
Two gated PostgreSQL tests cover accession allocation and competing issue/token
retries; both must run against a separately authorized disposable database before
production. Physical print/scanning, native speaker review, physical phones and
non-Chromium browsers remain manual checks. No actual WhatsApp message was sent.
Browser PDF generation verifies layout, not a physical printer or phone camera.

## Historical next-phase note

**Phase 5: metadata assistance, SEO, launch hardening and deployment preparation.**
Keep suggestions optional, attributed and explicitly approved before overwriting
metadata. PostgreSQL concurrency, private restore drills and production checks
remain required before launch. Provisioning and deployment require separate user
authorization. Do not begin Phase 5 automatically.

## Historical Phase 3 handoff

Date: November 3, 2026 (Asia/Karachi). Scope: local implementation only. No infrastructure provisioned, no Neon/Vercel projects touched, no deployment configuration created.

## Phase 3 completed

- Dedicated `/offline/` public PWA interface; local manifest, code-drawn 192/512 PNG icons, standalone start URL, explicit download/update/remove, progress/cancellation, successful timestamps/counts and freshness/storage/installation notices in English, Urdu and Arabic. A native install button appears only when the browser supplies a prompt. Service workers require HTTPS or device-local localhost.
- `/catalog/public-snapshot.json` exports the complete public collection with explicit field allowlists, normalized/original text, stable detail URLs, public copy/shelf/volume/availability and schema metadata. It shares Phase 2 visibility logic and uses a coherent database transaction. Safety caps return an explicit error, never truncation. No borrower/user/loan/receipt/private-settings fields are included.
- IndexedDB schema version 1 stores public text and optional covers. Full validation precedes an atomic revision-checked replacement. Quota, invalid/network response, transaction abort and competing-tab failures keep the previous download. Removal tombstones prevent in-flight resurrection. Blocked/full/cleared storage and empty snapshots have recoverable states.
- Offline ranked search/filter/pagination and previously unvisited detail/deep-link refresh work after download. Python and JS share fixtures and a generated casefold/whitespace table. Text renders with DOM text nodes, not executable HTML. Offline availability is explicitly historical. Display/fullscreen remains user-triggered.
- Worker scope is only `/offline/`; an explicit public shell/assets allowlist is cached. Snapshots and all private/server-rendered management pages are network-only. Non-GETs are never queued/replayed. No skipWaiting, clients.claim or forced reload; upgrades wait for old offline tabs to close and clean only this app's obsolete caches.
- Optional covers download separately with CORS/no credentials/no referrer, three concurrent requests, per-image timeout/2 MiB bound, 100-image/20 MiB stored limits and placeholders. Covers can be removed without text loss and are cleared only after a successful core replacement. There is no proxy, upload storage or external metadata lookup.
- No new migrations or dependencies. Existing inventory and Phase 1/2 migration files are unchanged. Local SQLite remains separate from future Neon; keep the private transfer procedure in README and verify it before full real entry.

## Phase 3 verification and limits

- Final full suite with browser enabled: **64 tests discovered, 63 passed on SQLite, 1 PostgreSQL concurrency test skipped**. This includes the original librarian browser flow and four new offline Chromium tests, all with isolated test databases/contexts.
- Five Node tests passed: shared Unicode/ranking fixtures, schema rejection, empty/invalid filters, streamed byte bounds, and ten 1,000-edition searches (about half a second total on this host; not a phone benchmark).
- Actual browser verification: clean storage → entire 20-edition/21-public-copy snapshot → offline reload → English/Urdu/Arabic and alias search → combined filters → unvisited deep link/refresh/shelves → offline language switching/mobile RTL → private GET/POST network failure → online update → failed/invalid update rollback → confirmed removal/empty state. Separate browser cases verify quota/transaction abort rollback, two real tabs, stale-after-removal rejection, blocked storage, empty snapshots, safe catalogue text and independent cover success/404/CORS failure/removal.
- Django system/migration consistency checks, Python lint/format, static collection and dependency checks passed. Public label completeness and generated JS parity tests replace gettext compilation; no gettext catalogue was added. Node syntax checks passed for authored JS modules. Screenshots are ignored and the Arabic mobile offline detail screenshot was visually reviewed.
- Early test failures were fixture ambiguity and Playwright harness issues (CSP string evaluation, restoring a native method, and a convenience single-page context); these were corrected without weakening CSP and the final full suite passed.
- Physical Samsung, Samsung Internet, Firefox, Safari, OS installation, deployment and PostgreSQL snapshot/concurrency behavior remain unverified. Chromium tests use a desktop browser with a mobile viewport. README documents trusted HTTPS or USB localhost forwarding for manual Samsung checks; plain LAN HTTP is insufficient.
- Browser storage is not permanent or a backup. Old public downloads cannot be remotely erased when a record is hidden/deleted online. Only `/offline/` is available offline; normal public/admin/librarian URLs remain online. Worker upgrades require old offline tabs/windows to close. Optional external covers depend on CORS. Snapshot schema/Unicode versions must remain coordinated on future changes.

Architecture, cache policy and verification details: `docs/OFFLINE.md`. Rebuild local icons/Unicode/labels with `python scripts/build_offline_assets.py` after intentional label changes.

## Phase 2 completed

- Private `/librarian/` dashboard, Django login and POST logout, model/staff permissions on every management route, no-store headers, private edition/copy/availability/active-loan counts, searchable paginated book list and links to public catalogue/admin.
- Atomic edition plus first-copy entry, explicit unknown author without fake people, multiple languages/categories/contributors and roles, optional metadata, save/add another, draft-preserving metadata creation in separate tabs and refresh choices. Session defaults remember the last successfully saved shelf/categories for new records only.
- Separate edition and copy edit forms explain their scope. Duplicate copies and editable-label volume batches have separate permanent accessions. Volume ranges are capped at 25 and require a signed preview before confirmation. UUID submission receipts enforce idempotency inside the same transaction as the edition/copy writes. Tokens are scoped to user/action and expire after 24 hours.
- Shelves (including empty ones), translated categories and contributors have private list/search/add/edit screens. Custom screens do not offer deletion. Category/language deletion is disabled in admin; model signals also protect referenced tags. Existing foreign-key/loan protections are retained. A public copy on an active loan cannot be hidden until its return is recorded in admin.
- Deterministic multilingual ranked search, exact accession/ISBN, one alias per line, category/language/availability filters, conservative tested normalization and stable pagination. Search reads only public copies and never borrower data. No stored normalized fields, no backfill/index sync requirement and no PostgreSQL-specific extension. Detailed rules and scale tradeoff are in `docs/SEARCH.md`.
- English, Urdu and Arabic labels/validation messages use the existing Python catalogue plus Django built-in form translations. Local fonts, focus controls and mobile/RTL layouts retained. All custom errors and new labels have translations; no gettext compilation is needed for this catalogue.

## Phase 2 migrations and data safety

`0002_submission` adds the private retry receipt model and its user dependency.
`0003_reference_languages` adds missing en/ur/ar reference languages with get_or_create,
without replacing existing names. `0001_initial` is unchanged. Applying migrations
locally preserved all 20 existing editions, 23 copies, 0 loans and 4 shelves. No
seed/reset or real-record writes were performed. Automated browser records/users
exist only in the separate Django test database and are destroyed after the run.

No dependencies changed. Existing `.env` and SQLite records remain valid; run
`python manage.py migrate` before starting the upgraded app. Local SQLite remains
separate from future Neon. Validate the private transfer procedure before entering
the full collection. README now excludes user-linked submission receipts from the
application-only transfer fixture; full private backups still include them.

## Phase 1 foundation retained

- Django 5.2.18 LTS, Python 3.13, pinned dependencies, SQLite development, PostgreSQL URL configuration, WhiteNoise static assets and production startup validation. Git exclusions cover secrets, databases, backups and generated files.
- Models/migrations for singleton library settings, empty shelves, translated categories, languages, contributor roles, editions, physical copies/volumes, accession sequence and private loans. Protected foreign keys preserve referenced editions/shelves/contributors/copies. Category/language tags are editable many-to-many metadata.
- Accession allocation uses an atomic counter UPDATE and insert in one transaction; unique constraint prevents duplicates. Numbers are immutable in normal model/admin saves, independent of shelf labels. Direct ORM updates/bulk_create bypass model logic and must not be used for accession allocation; restore fixtures through Django loaddata. PostgreSQL concurrency test is included and gated to PostgreSQL.
- Partial unique active-loan constraint and issue/due/return checks. Admin uses built-in auth, CSRF, model permissions and constraint validation. No registration or default credentials.
- Public welcome, category browse, recent editions, correct edition/copy/language counts, paginated basic search (title/aliases/contributors/categories/ISBN/public accession), combined filters and detail pages showing only public copies. No public borrower fields or loan endpoints.
- Ivory/walnut/gold/green responsive UI, local licensed Newsreader/Noto Naskh Arabic/Noto Nastaliq Urdu fonts, mixed-script titles, translated public labels, RTL layouts, page/query-preserving language cookies and display/fullscreen controls. Placeholder covers are generated in CSS from actual titles; no invented inventory image.
- Explicit idempotent seed: 20 visibly fictional editions, 23 copies, duplicate copies, a three-volume set, two multilingual editions and an empty example shelf. Never seeded by startup/build. Command refuses production or remote PostgreSQL.

## Verification

- Django system check: passed.
- Initial migrations applied locally; migration consistency: passed.
- Final full suite with browser enabled: 50 tests discovered, 49 passed on SQLite including the isolated Chromium flow; 1 PostgreSQL-only concurrent allocation test skipped as expected. The standard browser-disabled run skips that optional browser test as well.
- Ruff lint/format and pip dependency checks: passed.
- Static collection: passed, including locally served fonts and Django admin assets.
- Browser smoke script covers welcome/search/details, duplicate copies, interface-language preservation, Urdu RTL/mobile overflow, Arabic and display mode. Passed in Chromium; desktop and Urdu mobile screenshots were visually reviewed. No JavaScript errors or horizontal mobile overflow. Screenshots are in ignored test-results/.
- Production startup failure probes: missing required environment and SQLite production URL both rejected as intended.
- Initial test run revealed missing manifest entries under the development test runner; fixed by using plain static storage in development and manifest storage in production.
- Phase 2 browser flow passed against an isolated SQLite test database: login, new multilingual book, new contributor tab/draft refresh, extra copy, preview/confirm adjusted volume labels, public normalized search, individual shelf edit, Urdu mobile and Arabic layouts, no JavaScript errors or mobile horizontal overflow. Screenshots were visually reviewed in ignored `test-results/`.
- Additive migrations passed with unchanged existing inventory counts. First Phase 2 runs found a reference-language fixture conflict, a method decorator error in auth views and Playwright's event-loop restriction on synchronous test ORM reads. These were corrected and targeted checks rerun.
- Language natural-key fixture import and immediate alias-search availability were verified. Migrations remain consistent, dependency checks and static collection pass. Translation completeness is tested directly against all three Python catalogue entries; no gettext compiler is required.

## Known limits and decisions

No PostgreSQL server or dedicated test connection is available locally. SQLite does not verify production concurrency or PostgreSQL behavior. The PostgreSQL-only concurrent allocation test and common constraint suite must pass against a separately authorized disposable database before launch. No external database was accessed or provisioned.

Search intentionally scans the filtered, prefetched catalogue in Python before pagination, suitable for this small installation but linear in catalogue size. There is no fuzzy or transliteration path; Roman Urdu requires recorded aliases. Public UI labels use `catalog/templatetags/library_ui.py` plus `catalog/management_labels.py`, database branding/categories and Django built-in translations. Native speaker review remains useful. More book languages remain configurable in admin; new scripts may require suitable local fonts. Session defaults do not persist across logout. Changing interface language reloads forms; the UI advises saving drafts first. The restricted initial librarian is the existing superuser; README lists permissions for other staff accounts.

Offline/PWA public browsing was completed in Phase 3. Phase 4 now adds private loan screens, WhatsApp, QR labels and CSV. Metadata lookup, sitemap and deployment remain planned. External covers are optional; missing/failed images use local placeholders. No upload storage has been introduced. Submission receipts are private and never exported offline. Fresh create forms intentionally allow additional copies; replay protection applies to the same submitted token.

Production requires explicit environment values, PostgreSQL and HTTPS; Vercel without explicit production mode fails startup. Review actual Vercel proxy/static/runtime behavior and free-plan allowances in Phase 5. Official references are linked in README. No unverified deployment file is supplied.

Local SQLite data will not appear in Neon. Before full collection entry, follow the private backup/export/import and accession-sequence validation plan in README; avoid mixing samples and real inventory.

## Historical next-phase note

The Phase 3 handoff requested Phase 4. Phase 4 is now complete; the current next
phase is Phase 5 as described at the top of this document.

## GitHub and continuing workflow

The user authorized connecting and pushing to the public repository
`https://github.com/SalmanAliAqdas/rumi-library-system.git`. It was empty when
inspected. Preserve the original Phase 1 commit `27d4c29`; no history rewrite is
needed. The initial audit scanned all 46 tracked paths and the complete existing
commit history for sensitive paths and common credential patterns. No secrets,
actual environment files, local databases or private record exports were found;
`.env.example` contains placeholders and the record values in tests/demo seeding
are fictional. Ignore checks confirmed environment files, the local SQLite
database and backup exports are excluded.

After every completed and verified phase, commit and push to this repository.
This continuing user instruction is also recorded in `AGENTS.md`. Fetch and inspect
remote changes before integration; preserve unrelated work and existing commits.
Do not start the next phase automatically. Push results and any blockers are
reported in the session handoff.
