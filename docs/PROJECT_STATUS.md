# Project status — Phase 3

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

Offline/PWA public browsing is complete in Phase 3. Metadata lookup, WhatsApp, QR labels, CSV, sitemap and deployment remain planned. Basic private loans remain editable in admin; the comfortable issue/return UI is Phase 4. External covers are optional; missing/failed images use local placeholders. No upload storage has been introduced. Submission receipts are private and never exported offline. Fresh create forms intentionally allow additional copies; replay protection applies to the same submitted token.

Production requires explicit environment values, PostgreSQL and HTTPS; Vercel without explicit production mode fails startup. Review actual Vercel proxy/static/runtime behavior and free-plan allowances in Phase 5. Official references are linked in README. No unverified deployment file is supplied.

Local SQLite data will not appear in Neon. Before full collection entry, follow the private backup/export/import and accession-sequence validation plan in README; avoid mixing samples and real inventory.

## Exact next phase

Implement **Phase 4 only** when requested: basic private issue/return workflow; optional validated WhatsApp enquiries containing title/accession/URL (hidden without a valid number); stable copy QR destinations across interface languages and private printable labels; public-only CSV export plus a documented separate private backup procedure. Keep loan/borrower data out of offline snapshots/caches and public exports. Editing/lending remain online. Do not begin metadata enrichment or production deployment/provisioning in Phase 4.

The full five-phase roadmap and PowerShell setup, checks, private migration path and GitHub steps are in README.md.

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
