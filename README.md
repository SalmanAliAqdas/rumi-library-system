# Rumi Library · رومی لائبریری

A personal home library, built with Django templates, local CSS and modest vanilla JavaScript. Public browsing needs no login. The librarian uses a private mobile-friendly dashboard, with Django admin still available. A RumiWare portfolio project; one library per installation.

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

Open http://127.0.0.1:8000/ publicly, http://127.0.0.1:8000/librarian/ for management, or http://127.0.0.1:8000/admin/ for advanced administration. There is no default password or public registration. No activation script is required. Fonts are already included with their OFL licenses. No runtime font or styling CDN is used.

The seed command explicitly creates 20 fictional editions and 23 copies, including duplicates, three volumes and multilingual books. Rerunning does not duplicate records. It refuses production and non-SQLite databases. Four editable example shelves include an empty shelf; these are not a room map. Use a separate local checkout/database for real records; do not mix your full collection with demo content.

## Upgrade an existing Phase 1 checkout

Keep your existing `.env` and database. No dependency changes are required.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The additive migrations create private submission receipts and add missing English,
Urdu and Arabic language reference records without changing existing language names
or inventory. Phase 1 migrations and records are preserved. Do not seed or reset a
real collection as part of upgrading.

## Daily use in Phase 2

Sign in at **http://127.0.0.1:8000/librarian/** with the superuser you created.
The dashboard counts all editions and physical copies (including hidden ones),
available copies and active loans. Public counts still include public copies only.
There is no public registration or default password. Logout is a CSRF-protected POST.

1. **Add a book:** enter the original title and its language, choose author(s) or
   explicitly mark the author unknown, select one or more book languages, categories
   and a shelf. Unknown creates no fake contributor. ISBN and cover are optional.
   Expand optional details for publisher/year/edition, summary, cover URL, one alias
   per line, translators, editors and commentators. Save creates the edition, its
   credits and first physical copy atomically and shows the permanent accession.
   **Save and add another** returns to a fresh form with the last successfully saved
   shelf/categories suggested. Defaults belong to the current login session, are
   not applied to edits and never modify existing records silently.
2. **Missing metadata:** use the shelf/category/contributor links beside the form.
   They open small add screens in new tabs. Save there, return to the original tab
   and click **Refresh choices (keep draft)**. All entered values remain; refresh
   does not create a book. Multiple-select fields accept more than one item. On
   desktop, use the platform's Ctrl/Command selection; mobile uses native selection.
3. **Add another copy:** open the edition in Manage books, choose Add another copy,
   set shelf/optional volume/visibility and save. This creates another physical copy
   of the same metadata, with a different permanent number.
4. **Add volumes:** choose a range such as 1–10, a shared shelf and visibility, then
   Preview volumes. Adjust the labels one per line, then Confirm and create volumes.
   The cap is 25 per batch; labels must be distinct within that batch and at most
   80 characters. Each volume gets its own accession, and the whole batch is atomic.
   A completed POST retried or refreshed returns the original receipt rather than
   making duplicates. Opening a fresh form intentionally starts a new submission.
   Use a separate edition if a volume has different metadata.
5. **Edit edition** changes title/metadata/credits for all its copies. **Edit this
   copy** changes only its shelf, volume designation or visibility; the accession
   cannot be edited. To hide a copy on active loan, first record its return in admin.
6. **Manage shelves, categories and contributors:** list/search/add/edit from the
   dashboard. Empty shelves are valid. Correct referenced records by editing them;
   these screens offer no deletion. Django protects referenced shelves/contributors,
   copies and editions. Category/language deletion is disabled in admin and referenced
   tags are also protected against ORM deletion. Existing loan rules remain intact.

Keep staff access private. The documented superuser has all required permissions.
For a restricted staff user, explicitly grant the relevant catalogue model
permissions in admin: dashboard requires view edition/copy/loan; lists/details need
view edition/copy; new books need add edition/copy/contribution; edition editing needs
change edition plus add/delete contribution; copy creation needs add copy and view
edition; copy editing needs change copy and view edition. Metadata screens check
view/add/change on their own model. Login/logout require staff plus view edition/copy.
Every endpoint also checks active staff status. Hiding navigation is never the
permission boundary; requests without model permissions receive 403.

Loan issue/return remains in Django admin; the custom loan workflow is planned for
Phase 4. Public pages and search never expose borrower records. The management area
sets no-store/private cache headers. Display mode still hides the librarian link on
public pages and supports user-triggered fullscreen.

Public search now ranks exact accession/ISBN first, exact title/alias next, then
partial titles, aliases, contributors/categories and summary. ISBN ignores spaces
and hyphens. Category, book-language and availability filters combine. English,
Urdu, Arabic and mixed-script queries use the same conservative normalization.
Original text is untouched. `Bukhari` matches `بخاری` only through recorded aliases
or other matching text; this is not translation. See [search rules](docs/SEARCH.md).
Interface language changes labels/RTL, never the book-language filter. Save a book
draft before changing interface language. All fonts and styling remain local.

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
# Phase 2 browser flow: starts its own isolated test server/database, no local records used:
$env:RUMI_BROWSER_TESTS = '1'
.\.venv\Scripts\python.exe manage.py test tests.test_browser
Remove-Item Env:RUMI_BROWSER_TESTS
# Optional Phase 1 public smoke, against a separate local DEMO runserver:
.\.venv\Scripts\python.exe scripts/browser_smoke.py
```

The Phase 2 browser test creates temporary fictional users and books only in Django's test database. The standalone Phase 1 public smoke assumes the fictional demo catalogue. Screenshots are written to ignored `test-results/`. Tests cover direct GET/POST permissions, CSRF/login/logout, atomic creation/rollback, retries, copy/edition edit scope, batch validation, metadata protection, multilingual normalization/ranking/filtering/pagination, privacy and Phase 1 behavior. Browser tests are opt-in; PostgreSQL concurrency skips on SQLite. Public translations use a Python label catalogue, so gettext compilation is not required; completeness checks run as tests. SQLite results do not establish PostgreSQL concurrency behavior. Run the same suite against a disposable, separate PostgreSQL test database before production; Django needs permission to create its test database. Never run tests against another project's database. No cloud database has been provisioned in Phase 1.

## Database and deployment path

Local `db.sqlite3` is separate from a future Neon database. Git excludes databases, secrets, backups and generated assets. Before full real entry, validate the private backup/restore/transfer procedure below against a dedicated production-like database. Keep local trials small until that verification is complete; local SQLite is not automatically synchronized with Neon. The Django ORM and checked-in migrations are the only schema authority.

Migration procedure for a future phase:

1. Stop writes and make a private, verified copy of SQLite. Remove sample data from a separate copy if necessary; never delete real records to reset a demo.
2. Export application records privately: `python manage.py dumpdata catalog --exclude catalog.submission --natural-foreign --natural-primary --indent 2 --output backups/catalog.json`. This includes **private borrower data**. Never commit it or publish it as a public export. Language natural keys use codes, so existing reference languages are reused even if their IDs differ between databases.
3. Provision a separate Neon project/database only when explicitly authorized. Set `DATABASE_URL` privately, run `migrate`, then `loaddata backups/catalog.json`. Restore `AccessionSequence` along with copies so the next number is greater than all imported accessions. Django deserialization preserves accessions. Do not bulk-create new copies or use QuerySet updates to change accession identifiers; new records must use model save/admin.
4. Validate counts, visibility, multilingual text, availability, next accession generation and the PostgreSQL constraint/concurrency tests on a disposable database. Recreate the superuser with `createsuperuser`; this application-only export does not transfer credentials/sessions. Submission receipts are excluded because they reference local users and are only short-lived retry protection; full private backups still retain them. Stop all writes/old forms during transfer and use a fresh production SECRET_KEY so old signed forms cannot be replayed. Retain the private backup until restoration has been verified.

Production requires `DJANGO_ENV=production`, a strong SECRET_KEY, a PostgreSQL DATABASE_URL, explicit ALLOWED_HOSTS, HTTPS CSRF_TRUSTED_ORIGINS and HTTPS SITE_URL. Missing settings fail startup; SQLite is never a production fallback. The optional WhatsApp setting is reserved for Phase 4. Do not use local filesystem uploads on Vercel.

Official references checked on November 3, 2026: [Django supported releases](https://www.djangoproject.com/download/) (5.2 LTS supported through April 2028) and [Vercel Django guide](https://vercel.com/docs/frameworks/full-stack/django). No deployment configuration or account changes are made in Phase 1. Recheck official entrypoint, static asset, Python runtime and free-plan requirements before Phase 5 deployment; run migrations as a controlled release action, never on every request. Run `check --deploy` with real production settings before launch. No paid services are enabled.

## Roadmap

Phase 1 is the working foundation: models, migrations, private admin, welcome, basic paginated search/filters/details, initial translations, display mode, fictional samples and tests.

- **Phase 2 — completed, librarian workflow and search:** mobile dashboard and forms; save/add another; copy duplication and bulk volumes; remember shelf/category; manage shelves/contributors/categories; ranked search; tested Urdu/Arabic normalization; exact accession/ISBN and partial matching; recorded Roman Urdu aliases; deterministic SQLite/PostgreSQL search without a fuzzy extension. Fuzzy matching is not translation.
- **Phase 3 — offline public catalogue:** PWA manifest, service worker, IndexedDB, explicit full public catalogue download/update, original and normalized text, offline filters/details, connection and last-success status, atomic snapshot publication, optional covers/placeholders. Never cache auth, admin, loans or borrower data. First download needs internet; browser storage can be cleared. Offline browsing only; edits/lending need internet.
- **Phase 4 — practical extras:** custom private issue/return workflow, validated optional WhatsApp enquiry links with title/accession/URL, stable copy QR destinations across translated routes, private printable labels, public catalogue CSV export and a separate documented private backup process.
- **Phase 5 — assistance, launch and polish:** optional Open Library/Google Books metadata suggestions with server timeouts/limits/validation/error handling, explicit approval and source attribution, no silent overwrite and no blocking browsing/manual entry; SEO, public-only sitemap/metadata/security; verify current free-plan allowances and permitted usage; production verification on dedicated Neon/PostgreSQL and Vercel. Never enable paid services.

Phase 2 custom book/copy/volume entry, metadata screens and deterministic multilingual search are complete. Offline support, custom loan screens, WhatsApp, QR/CSV, metadata lookup and deployment remain **planned**. See [project handoff](docs/PROJECT_STATUS.md).

## GitHub

The project repository is [SalmanAliAqdas/rumi-library-system](https://github.com/SalmanAliAqdas/rumi-library-system). The local `origin` points to its HTTPS URL. After each completed and verified phase, review the changes for secrets/private data, commit and push. Preserve existing history; do not force-push.

```powershell
git status
git fetch origin
git push origin main
```

`main` tracks `origin/main` after the initial push. The GitHub repository is public; no database, secrets or private borrower records belong in its source or history. See `AGENTS.md` for the continuing phase workflow.
