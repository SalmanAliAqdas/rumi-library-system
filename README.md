# Rumi Library · رومی لائبریری

A personal home library, built with Django templates, local CSS and modest vanilla JavaScript. Public browsing needs no login. Only the librarian uses Django admin. A RumiWare portfolio project; one library per installation.

## Windows PowerShell setup

Python 3.12+ is recommended (developed on Python 3.13). From this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Edit .env and replace SECRET_KEY; keep DJANGO_ENV=development.
.\.venv\Scripts\python.exe manage.py migrate
# Optional: fictional samples, only for local development:
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/. There is no default password or public registration. No activation script is required. Fonts are already included with their OFL licenses. No runtime font or styling CDN is used.

The seed command explicitly creates 20 fictional editions and 23 copies, including duplicates, three volumes and multilingual books. Rerunning does not duplicate records. It refuses production and non-SQLite databases. Four editable example shelves include an empty shelf; these are not a room map. Use a separate local checkout/database for real records; do not mix your full collection with demo content.

## Daily use in Phase 1

Create languages, shelves (including empty ones), categories and contributors in admin. Add an edition with languages, categories, contributor roles and physical copies. Each copy gets a permanent RL-000001 style number; shelf labels can change. ISBN belongs to an edition and is optional. A volume is a copy with a volume designation. Cover URLs are optional; no upload storage is configured. Hidden copies never appear in public search or totals. An edition appears publicly only when it has at least one public copy. Edition/copy counts are distinct; current loans determine availability.

Private loans can be recorded and returned through admin. Loan records, names and contacts never appear in public views. Keep librarian credentials private and do not grant other users staff permissions. Display mode hides the librarian link and enlarges the welcome screen. Fullscreen is offered only when supported and starts only on a click. Interface language preserves the page and query; it does not filter book languages. Public UI labels are in `catalog/templatetags/library_ui.py`; translated category names and Django's built-in admin translations supply the Phase 1 RTL foundation. Full editorial translation review remains desirable.

## Checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
# Optional browser tooling, once:
.\.venv\Scripts\python.exe -m playwright install chromium
# With runserver running in a second terminal, after optional demo seeding:
.\.venv\Scripts\python.exe scripts/browser_smoke.py
```

Browser smoke assumes the fictional demo catalogue. Screenshots are written to ignored `test-results/`. Tests cover privacy, access permissions, accessions, volume/copy records, loan constraints, basic search and language switching. SQLite results do not establish PostgreSQL concurrency behavior. Run the same suite against a disposable, separate PostgreSQL test database before production; Django needs permission to create its test database. Never run tests against another project's database. No cloud database has been provisioned in Phase 1.

## Database and deployment path

Local `db.sqlite3` is separate from a future Neon database. Git excludes databases, secrets, backups and generated assets. Before full real entry, decide whether to use a clean dedicated Neon development database or migrate local records. The Django ORM and checked-in migrations are the only schema authority.

Migration procedure for a future phase:

1. Stop writes and make a private, verified copy of SQLite. Remove sample data from a separate copy if necessary; never delete real records to reset a demo.
2. Export application records privately: `python manage.py dumpdata catalog --indent 2 --output backups/catalog.json`. This includes **private borrower data**. Never commit it or publish it as a public export.
3. Provision a separate Neon project/database only when explicitly authorized. Set `DATABASE_URL` privately, run `migrate`, then `loaddata backups/catalog.json`. Restore `AccessionSequence` along with copies so the next number is greater than all imported accessions. Django deserialization preserves accessions. Do not bulk-create new copies or use QuerySet updates to change accession identifiers; new records must use model save/admin.
4. Validate counts, visibility, multilingual text, availability, next accession generation and the PostgreSQL constraint/concurrency tests on a disposable database. Recreate the superuser with `createsuperuser`; this application-only export does not transfer credentials/sessions. Retain the private backup until restoration has been verified.

Production requires `DJANGO_ENV=production`, a strong SECRET_KEY, a PostgreSQL DATABASE_URL, explicit ALLOWED_HOSTS, HTTPS CSRF_TRUSTED_ORIGINS and HTTPS SITE_URL. Missing settings fail startup; SQLite is never a production fallback. The optional WhatsApp setting is reserved for Phase 4. Do not use local filesystem uploads on Vercel.

Official references checked on November 3, 2026: [Django supported releases](https://www.djangoproject.com/download/) (5.2 LTS supported through April 2028) and [Vercel Django guide](https://vercel.com/docs/frameworks/full-stack/django). No deployment configuration or account changes are made in Phase 1. Recheck official entrypoint, static asset, Python runtime and free-plan requirements before Phase 5 deployment; run migrations as a controlled release action, never on every request. Run `check --deploy` with real production settings before launch. No paid services are enabled.

## Roadmap

Phase 1 is the working foundation: models, migrations, private admin, welcome, basic paginated search/filters/details, initial translations, display mode, fictional samples and tests.

- **Phase 2 — librarian workflow and search:** mobile dashboard and forms; save/add another; copy duplication and bulk volumes; remember shelf/category; manage shelves/contributors/categories; ranked search; tested Urdu/Arabic normalization; exact accession/ISBN and partial matching; recorded Roman Urdu aliases; optional PostgreSQL fuzzy search without breaking SQLite. Fuzzy matching is not translation.
- **Phase 3 — offline public catalogue:** PWA manifest, service worker, IndexedDB, explicit full public catalogue download/update, original and normalized text, offline filters/details, connection and last-success status, atomic snapshot publication, optional covers/placeholders. Never cache auth, admin, loans or borrower data. First download needs internet; browser storage can be cleared. Offline browsing only; edits/lending need internet.
- **Phase 4 — practical extras:** custom private issue/return workflow, validated optional WhatsApp enquiry links with title/accession/URL, stable copy QR destinations across translated routes, private printable labels, public catalogue CSV export and a separate documented private backup process.
- **Phase 5 — assistance, launch and polish:** optional Open Library/Google Books metadata suggestions with server timeouts/limits/validation/error handling, explicit approval and source attribution, no silent overwrite and no blocking browsing/manual entry; SEO, public-only sitemap/metadata/security; verify current free-plan allowances and permitted usage; production verification on dedicated Neon/PostgreSQL and Vercel. Never enable paid services.

Offline support, custom entry/loan screens, WhatsApp, QR/CSV, metadata lookup and deployment are **planned**, not completed. See [project handoff](docs/PROJECT_STATUS.md).

## GitHub

The project repository is [SalmanAliAqdas/rumi-library-system](https://github.com/SalmanAliAqdas/rumi-library-system). The local `origin` points to its HTTPS URL. After each completed and verified phase, review the changes for secrets/private data, commit and push. Preserve existing history; do not force-push.

```powershell
git status
git fetch origin
git push origin main
```

`main` tracks `origin/main` after the initial push. The GitHub repository is public; no database, secrets or private borrower records belong in its source or history. See `AGENTS.md` for the continuing phase workflow.
