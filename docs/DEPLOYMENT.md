# Deployment guide

Phase 6 live installation: **https://rumi-library.vercel.app/**. See
[LIVE_OPERATIONS.md](LIVE_OPERATIONS.md) for actual project IDs, account setup,
release, backup and device steps. The production dependency manifest is
requirements.txt; Ruff settings now live in ruff.toml. TLS uses pinned Certifi CA
roots with verify-full, replacing the unverified system-store assumption below.
Git deployment is now enabled for main only. The Phase 5 preparation notes below
are retained as a checklist, with actual outcomes in PROJECT_STATUS.md.

Prepared and updated November 5, 2026 (Asia/Karachi). Phase 6 provisioned the
dedicated resources, applied migrations and verified the live empty catalog.
Reuse the Rumi resources listed in LIVE_OPERATIONS.md; do not create duplicates.
The procedure below also covers future fresh installations and schema releases.

## Account and free-plan decisions

Use a **separate Rumi Library project** in your existing Neon account and a separate
Vercel project, never another application's database. Create a disposable empty
test database first. Keep all account credentials in a password manager and the
provider's environment settings; never paste them into chat or command arguments.
Do not enable billing, paid integrations, Auth, storage or AI services.

Official allowances checked November 5, 2026:

- [Vercel Hobby](https://vercel.com/docs/plans/hobby): personal noncommercial use;
  100 GB fast transfer, 10 GB origin transfer, one million CDN requests and function
  invocations, four active CPU hours and 360 GB-hours provisioned memory monthly.
  Exceeding limits can pause service. A personal home-library demonstration appears
  consistent with this purpose; this is an inference, not account approval. If
  RumiWare uses the site to promote commercial services, confirm eligibility with
  Vercel before launch. Do not silently upgrade or enable billing.
- [Neon Free](https://neon.com/pricing): no payment card required; currently 100
  projects, 100 CU-hours per project per month, 1 GB database storage per project,
  compute up to 2 CU. Verify your account's remaining allowances before creating
  anything. Free history retention is limited; maintain independent private backups.
- [Vercel WAF rate limiting](https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting):
  Hobby permits one rate-limit rule within three custom rules, a fixed window of
  10 seconds–10 minutes and one million included allowed requests. No rule was
  created here. Recheck free availability in your dashboard before enabling it.

## Production configuration

Keep the pinned free/open-source requirements. Python **3.13** is selected in
`.python-version`; Django is **5.2.19 LTS**, the current 5.2 patch checked against
[Django's supported versions](https://www.djangoproject.com/download/).

Set these separately for each environment, using your actual Rumi values:

```dotenv
DJANGO_ENV=production
SECRET_KEY=<new-unique-random-value-at-least-50-characters>
DATABASE_URL=postgresql://<role>:<password>@<rumi-pooled-host>/<database>?sslmode=verify-full&channel_binding=require
ALLOWED_HOSTS=<final-host>,<explicit-preview-host-if-needed>
CSRF_TRUSTED_ORIGINS=https://<final-host>,https://<explicit-preview-host-if-needed>
SITE_URL=https://<final-host>
HSTS_SECONDS=0
WHATSAPP_NUMBER=
```

These are placeholders, not usable credentials. Do not use wildcard hosts/origins.
`SITE_URL` is an HTTPS origin with no path, credentials, query or fragment; it
controls canonical, sitemap, WhatsApp and QR URLs independently of request Host.
Language selection uses cookies on the same URLs, so there are no separate
translated routes and no invented hreflang alternatives. Search/filter variants
are noindex. No Book structured data is emitted; no ratings/inventory are invented.

The existing psycopg 3 binary driver uses TCP; do not install a JavaScript Neon
driver. Use Neon's **pooled** URL for web requests and **direct** URL for migrations,
data loading and backups. Connections close after requests (`CONN_MAX_AGE=0`),
server-side cursors are disabled for transaction pooling, and connection timeout
is five seconds. See [Neon Django](https://neon.com/docs/guides/django).
Production enforces `sslmode=verify-full` with `sslrootcert=certifi.where()`.
Pinned [Certifi](https://pypi.org/project/certifi/) supplies Mozilla CA roots across
Windows and Vercel; relying on libpq's system store failed in the actual runtime.
TLS was verified without weakening encryption or hostname checks. Recheck it
after dependency/runtime changes. [Neon secure connections](https://neon.com/docs/connect/connect-securely).

The release operator should set `statement_timeout` to 15 seconds on the separate
Rumi web role using the Neon SQL editor (`ALTER ROLE <rumi_web_role> SET
statement_timeout = '15s';`), then reconnect and verify it. This avoids unsupported
startup options with poolers. Select only the Rumi role/database; do not apply
this to other projects. Migrations use a separate direct owner connection.

Vercel supplies `VERCEL=1`; only then is its forwarded HTTPS header trusted.
Other hosts must configure trusted proxy handling deliberately. DEBUG is false,
cookies are secure, HTTPS redirects are enabled. Start with HSTS disabled; after
the final domain's certificate/redirects work, use `HSTS_SECONDS=3600`, then
increase deliberately to `31536000`. Subdomain HSTS and preload remain disabled.
`check --deploy` warns while HSTS is intentionally disabled; do not ignore other
warnings. Application error logs omit request data, SQL and exception bodies;
platform access logs still need private access/retention management. `/health/`
is public liveness only, not a database readiness check.

## Deliberate future release procedure

1. Rehearse [SQLite transfer](TRANSFER.md), PostgreSQL tests and private
   [backup/restore](BACKUPS.md) on the separate disposable target. Do not use a
   production database as Django's test target. Obtain a role allowed to create
   the disposable Django test database, then run the full suite including the
   PostgreSQL concurrency cases. Do not use `--keepdb` against real inventory.
2. With writes stopped and the **direct Rumi destination** selected privately,
   install `requirements-dev.txt`, run `python manage.py migrate --plan`, review,
   then `python manage.py migrate`. No migration, seed or administrator creation
   runs in the build or web startup. Load verified real records only deliberately.
3. Run `python manage.py createsuperuser` interactively against that same Rumi
   database. There is no default password, public signup or automatic superuser.
   Recreate restricted staff permissions explicitly; source sessions are not moved.
4. Run `python manage.py check --deploy`, `python manage.py makemigrations --check
   --dry-run`, `python manage.py collectstatic --noinput`, and the transfer audit.
   Do not start the old SQLite writer after cutover.
5. Import this repository into a **new Rumi Vercel project**, root directory at
   repository root, Django framework, Python 3.13. Configure environment variables
   before building. The current [Vercel Django integration](https://vercel.com/docs/frameworks/full-stack/django)
   detects `manage.py`, resolves `config.wsgi.application`, and automatically runs
   `collectstatic`, serving the local fonts, icons, manifest and assets on its CDN.
   WhiteNoise remains compatible locally. Leave install/build overrides empty;
   requirements are installed normally. `vercel.json` caps the function at 30s.
   No filesystem uploads or persistent SQLite are used. Missing production
   configuration aborts startup/build instead of selecting SQLite.
6. Phase 6 enables Git auto-deployment **only for main** in `vercel.json`.
   Reviewed main pushes build production code; other branches do not auto-deploy.
   Database migrations remain a separate deliberate action, never a build step.
   [Vercel Git configuration](https://vercel.com/docs/project-configuration/git-configuration).
   The dedicated project selects sin1 near the Neon Singapore database.
7. Configure the final domain and SITE_URL before permanent labels. For an initial
   preview, use its exact HTTPS origin/host, protect it, then switch to the final
   domain and rebuild. Do not print permanent labels for a preview address.

## Throttling and final verification

Application throttles use shared database conditional updates, not instance memory:
outgoing Open Library requests have one reservation every two seconds; both login
forms share ten attempts per five-minute hashed username bucket. There are 256
bounded buckets, no stored usernames/IPs; collisions can temporarily throttle
another user. This limits password guessing across instances, but not distributed
traffic costs or username lockout abuse. Test PostgreSQL reservations before launch.

In Vercel **Firewall → Configure → New Rule**, create one rate-limiting rule with
condition `Request Path equals /librarian/login/ OR Request Path equals /admin/login/`
and `Request Method equals POST`, key **IP**, fixed **60-second** window, limit
**20**, action **Deny (429)**. Confirm the Hobby included allowance before saving;
never accept an upgrade prompt. Verify with isolated requests, then restore normal
access. Shared application throttles remain active even without this rule. The
one free rule cannot separately protect every expensive public endpoint. Monitor
search/snapshot usage; ranked multilingual search still scans a home-size catalog
in Python, as documented in [SEARCH.md](SEARCH.md). Platform DDoS controls do not
replace permissions or CSRF.

On the protected preview and final site, verify login → new fictional test book →
lookup → selected fields → save → public search → issue/return → labels/CSV →
download/update → real offline reload/search. Remove only the explicit test records
under a deliberate cleanup plan; never alter actual inventory for tests. Check
English/Urdu/Arabic and RTL, local fonts and covers, empty states, hidden-record
404s, no borrower leakage, security headers, sitemap, canonical and robots.
Inspect `/offline/sw.js` (JavaScript, no-cache, scope `/offline/`), manifest/icons
and worker upgrades after old offline tabs close. Verify no private page or POST
enters CacheStorage/IndexedDB. Offline downloads cannot be remotely erased.
Check `/health/`, real database reads and logs separately. Complete the PostgreSQL
restore drill, TLS checks, physical print/scan and phone/browser checks before
calling the site production-verified. None of these hosted checks is claimed here.
