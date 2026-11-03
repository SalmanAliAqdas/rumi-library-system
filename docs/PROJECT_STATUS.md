# Project status — Phase 2

Date: November 3, 2026 (Asia/Karachi). Scope: local implementation only. No infrastructure provisioned, no Neon/Vercel projects touched, no deployment configuration created.

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

No offline/PWA support, metadata lookup, WhatsApp, QR labels, CSV, sitemap or deployment. Basic private loans remain editable in admin; the comfortable issue/return UI is Phase 4. External cover images may contact their host but send no referrer; missing/failed images use local placeholders. No upload storage has been introduced. Submission receipts are private, contain accessions and a librarian reference only, and are never exposed publicly. Fresh create forms intentionally allow additional copies; replay protection applies to the same submitted token.

Production requires explicit environment values, PostgreSQL and HTTPS; Vercel without explicit production mode fails startup. Review actual Vercel proxy/static/runtime behavior and free-plan allowances in Phase 5. Official references are linked in README. No unverified deployment file is supplied.

Local SQLite data will not appear in Neon. Before full collection entry, follow the private backup/export/import and accession-sequence validation plan in README; avoid mixing samples and real inventory.

## Exact next phase

Implement **Phase 3 only** when requested: offline public browsing and searching. Add a PWA manifest/service worker and IndexedDB; explicitly download/update the entire public catalogue with original and normalized text. Publish a new snapshot only after complete successful download. Show connection state and last successful update. Support local search/filters/details and optional cover caching with placeholders. Never cache librarian/admin/authentication responses, loans, receipts or borrower data. First download requires internet and browser storage may be cleared. Editing/lending remain online. Do not begin custom lending, WhatsApp, QR, metadata lookup or deployment in this phase.

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
