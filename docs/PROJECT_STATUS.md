# Project status — Phase 1

Date: November 3, 2026 (Asia/Karachi). Scope: local implementation only. No infrastructure provisioned, no Neon/Vercel projects touched, no deployment configuration created.

## Working foundation

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
- Final suite: 16 tests discovered, 15 passed on SQLite, 1 PostgreSQL-only concurrent allocation test skipped as expected.
- Ruff lint/format and pip dependency checks: passed.
- Static collection: passed, including locally served fonts and Django admin assets.
- Browser smoke script covers welcome/search/details, duplicate copies, interface-language preservation, Urdu RTL/mobile overflow, Arabic and display mode. Passed in Chromium; desktop and Urdu mobile screenshots were visually reviewed. No JavaScript errors or horizontal mobile overflow. Screenshots are in ignored test-results/.
- Production startup failure probes: missing required environment and SQLite production URL both rejected as intended.
- Initial test run revealed missing manifest entries under the development test runner; fixed by using plain static storage in development and manifest storage in production.

## Known limits and decisions

No PostgreSQL server or dedicated test connection is available locally. SQLite does not verify production concurrency or PostgreSQL behavior. The PostgreSQL-only concurrent allocation test and common constraint suite must pass against a separately authorized disposable database before launch. No external database was accessed or provisioned.

Basic substring search only. Urdu/Arabic normalization, fuzzy ranking and recorded Roman Urdu entry workflow belong to Phase 2. Public UI labels currently use a small explicit translation catalogue in `catalog/templatetags/library_ui.py`, database branding/categories and Django built-in admin translations. Native speaker review remains useful; locale/ reserves space for gettext expansion. More book languages are possible through Language records; arbitrary original language codes require suitable local fonts if extended.

No offline/PWA support, custom librarian dashboard, metadata lookup, WhatsApp, QR labels, CSV, sitemap or deployment. Basic private loans are editable in admin; the comfortable issue/return UI is Phase 4. External cover images may contact their host but send no referrer; missing/failed images use local placeholders. No upload storage has been introduced.

Production requires explicit environment values, PostgreSQL and HTTPS; Vercel without explicit production mode fails startup. Review actual Vercel proxy/static/runtime behavior and free-plan allowances in Phase 5. Official references are linked in README. No unverified deployment file is supplied.

Local SQLite data will not appear in Neon. Before full collection entry, follow the private backup/export/import and accession-sequence validation plan in README; avoid mixing samples and real inventory.

## Exact next phase

Implement **Phase 2 only** when requested: mobile-friendly private dashboard/forms; save/add another; add another physical copy; bulk volumes; remember sensible shelf/category defaults; manage metadata; improve ranked search with tested Urdu/Arabic normalization, exact accession/ISBN matching, partial matching and recorded Roman Urdu aliases. PostgreSQL fuzzy matching is optional and must retain SQLite functionality. Keep permissions server-side and borrower data private. Do not begin offline/deployment work as part of Phase 2.

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
