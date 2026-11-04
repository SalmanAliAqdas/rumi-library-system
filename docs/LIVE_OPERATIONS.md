# Rumi Library live operations

Launch date: November 5, 2026 (Asia/Karachi).

- Public catalog: **https://rumi-library.vercel.app/**
- Private login: **https://rumi-library.vercel.app/librarian/login/**
- Room display: **https://rumi-library.vercel.app/?display=1**
- Offline catalog: **https://rumi-library.vercel.app/offline/**
- Liveness: **https://rumi-library.vercel.app/health/**

The public site needs no Vercel login. Management requires your private Django
staff account. Account creation was completed through an interactive local
terminal; its password is never stored in the repository or handoff. There is no
default password or public registration. A separate temporary restricted account
is used for browser verification and removed afterward.
The checked-in `scripts/live_smoke.py --expect-empty` repeats public checks without
creating inventory or accounts. Its optional authenticated mode uses an explicitly
prepared temporary `.vercel/smoke-account.json`; it never uses your password and
does not create that account automatically. Do not publish browser auth artifacts.

## Resources and data

| Resource | Identifier |
| --- | --- |
| GitHub repository / production branch | SalmanAliAqdas/rumi-library-system / main |
| Vercel team | rumiware1 / team_jK5Na6S1S89cbaOCiUQAbwO1 |
| Vercel project | rumi-library / prj_jzs3N8jR34Lecm28HUmm7wVp2Kul |
| Neon organization / plan | org-cold-feather-57890093 / Free |
| Neon project | rumi-library / noisy-bread-19614503 |
| Production branch | production / br-wild-credit-az43c4d3 |
| Isolated verification branch | verification / br-dry-truth-azak0pak |
| Database | rumi_library / PostgreSQL 18 |
| Runtime role | rumi_web, scoped read/write in public schema |
| Administrative role | rumi_owner, direct connection, never in the web runtime |

Only these dedicated resources were changed. SchoolOS, the enquiry assistant and
other account projects were left untouched. Production launched with **0 editions,
0 copies and 0 loans**. Local SQLite retains **20 fictional editions / 23 copies**;
all matched the marked seed records, so no sample inventory was published or
deleted. No real-data transfer or source backup was needed/performed.

Local SQLite and live Neon are separate. Do daily real book entry in the **live
librarian area**, gradually. Add actual shelves/categories/contributors there;
the production database contains only the three migration-created reference
languages initially. A public edition needs at least one visible copy. Hidden
copies stay private. Keep the chosen Vercel address stable: permanent QR labels
will use `https://rumi-library.vercel.app/copies/<accession>/`. Test one physical
print/scan before a batch. A future custom subdomain is optional; none was purchased
and no custom DNS was changed.
The label preview conservatively warns on all vercel.app addresses, including this
production alias. Inspect the actual destination and keep this alias/project stable.

## Configuration and releases

Production uses `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings`,
secure cookies, DEBUG=False, explicit canonical hosts/origins and HTTPS redirect.
After the actual HTTPS site and HTTP 308 redirect were verified, HSTS was set to
3600 seconds, without subdomain inheritance or preload.
Deployment checks consequently retain only W005/W021 for deliberately disabled
subdomain inheritance/preload; do not enable these blindly on a hosted subdomain.
`SITE_URL=https://rumi-library.vercel.app`. The secondary owned alias
`rumi-library-rumiware1.vercel.app` is explicitly allowed and canonicals point to
the shorter address. No wildcard hosts, sample seeding or filesystem database.
WhatsApp and Google Books remain disabled. Open Library needs no API key.

Database credentials and SECRET_KEY are Vercel **sensitive** variables, production
only. Runtime uses a pooled URL; migrations/admin use the direct owner URL. Full
TLS hostname verification uses pinned Certifi Mozilla CA roots on both Windows
and Vercel. This fixes the runtime's missing OpenSSL trust store without disabling
verification. Connections close after each request; runtime role statement timeout
is 15 seconds. Native Django builds use Python 3.13 and pinned requirements.txt,
run collectstatic, then serve local assets from the CDN. Ruff configuration lives
in ruff.toml so it cannot shadow dependency installation. Function cap is 30s.
Production public snapshots have a 4 MiB response cap, below Vercel's 4.5 MB
function-response ceiling; oversized downloads use the existing friendly failure
path and preserve the prior saved catalog. Local development retains its 20 MiB cap.

`vercel.json` enables Git deployments **only for main**. A reviewed GitHub push to
main triggers production; other branches have deployment disabled. Preview writes
have no production credentials. To test a preview, explicitly configure a separate
test database and preview-only secrets/hosts first. Migrations never run in builds,
requests or function startup. Git deployment is code deployment, not data migration.

Before a schema release:

1. Review the migration and make a private full PostgreSQL backup. Rehearse it on
   a separate test target, including restore and catalog audit.
2. Keep existing code/schema compatible during rollout. Stop writes for changes
   that require it. Use the direct Rumi production owner connection deliberately.
3. In this prepared workstation, run:

   ```powershell
   .\.venv\Scripts\python.exe scripts/production_manage.py migrate --plan
   .\.venv\Scripts\python.exe scripts/production_manage.py migrate
   .\.venv\Scripts\python.exe scripts/production_manage.py check --deploy
   .\.venv\Scripts\python.exe scripts/production_manage.py audit_catalog
   ```

   The helper verifies the exact Rumi host/database before operating, loads
   `.env.phase6.production.local` privately and never prints credentials. On a new
   workstation, recreate that ignored file using the environment key names in
   [DEPLOYMENT.md](DEPLOYMENT.md), with the **direct owner** URL obtained privately
   from this Rumi Neon project. Do not copy a URL from another project. Keep the
   private file protected and out of sync/public folders; never commit it.
4. Run checks locally, review/stage only relevant source, commit and push main.
   Inspect the actual Vercel build and verify the live alias reports that commit.
5. Recheck health, public reads, private authentication, visibility, static assets,
   canonical/sitemap and offline update. Health checks liveness, not database health.

The same helper supports `createsuperuser` and `changepassword <username>`
interactively if deliberately needed. Do not recreate/reset an existing working
account. Passwords must never appear in arguments or chat. Tests are refused on
the production target. The isolated branch can run:

```powershell
.\.venv\Scripts\python.exe scripts/production_manage.py --target verification test tests.test_postgres tests.test_practical tests.test_imports --noinput
```

## Backups and rollback

GitHub backs up **code**, not Neon records. Public CSV and browser downloads cannot
restore private loans, accounts or settings. Follow [BACKUPS.md](BACKUPS.md) for
private direct `pg_dump` custom-format backups, matching PostgreSQL clients and
`pg_restore --no-owner --no-privileges --exit-on-error --single-transaction` to a
separate empty test database. Use private libpq service/password files; no database
passwords in shell history. Keep dated backups, hashes, app commit and migration
version outside the checkout, with another protected copy. Back up before schema
changes and regularly once real entry starts. The six-hour provider history window
is not an independent backup. A full pg_dump/restore drill still needs the matching
client tools; it has not been claimed as completed by this launch.

Code rollback: in this **Rumi project**, redeploy/promote a known-good deployment
whose code supports the current schema; verify before routing traffic. The earlier
packaging/TLS-failed deployments are not rollback candidates. Database rollback is
separate: stop writes, preserve the current database/backup, restore a verified dump
to a **new isolated database**, compare counts/hashes/relationships/visibility/loans
with audit_catalog, then switch credentials and redeploy deliberately. Never restore
over the original or blindly reverse migrations. Reconcile post-backup writes.

## Free limits, errors and remaining device checks

Checked November 5, 2026: accounts report Neon Free and Vercel Hobby. No paid plan,
billing activation, payment card service or paid integration was enabled. Hobby
permits personal noncommercial use; keep this a home-library project. Recheck
eligibility before using it to sell/promote commercial services.
[Vercel allowances](https://vercel.com/docs/plans/hobby): one million monthly CDN
requests/function invocations, 100 GB transfer, 10 GB origin transfer, 4 CPU-hours
and 360 GB-hours provisioned memory. [Neon Free](https://neon.com/pricing): 100
CU-hours per project/month, 1 GB database storage, up to 100 projects. The two Rumi
computes are capped at 0.25 CU; the provider enforces Free idle behavior. Monitor
account usage: the display and repeated searches can keep compute active, and Free
limits can suspend service. Do not silently upgrade if a quota is reached.

Shared database login and outgoing-provider throttles are active across instances.
Vercel's default DDoS protection remains active. No custom WAF rule was published;
the optional one-free-rule login configuration in [DEPLOYMENT.md](DEPLOYMENT.md)
remains a dashboard action. Verify its free allowance and review conditions before
publishing. Never weaken account-wide protections or enable paid extras.

Inspect errors in Vercel → rumi-library → Deployments → selected build/runtime logs.
Application logs emit safe categories such as `tls_verification`, not exception
contents, SQL, credentials or borrower forms. Keep platform logs/screenshots private;
avoid public authenticated traces. A failed/missing book uses a friendly production
404, not a debug traceback. Do not turn on DEBUG on the public deployment.

On your Samsung phone: visit `/offline/` over the live HTTPS address, download the
catalog, confirm counts/timestamp, then use airplane mode and reload the same page.
Search/open a saved book once real entries exist. Switch English/Urdu/Arabic, then
reconnect and update. Installation depends on the browser's offered Install/Add to
Home screen action. Private management and mutations require internet.

On the room laptop/LED: open `/?display=1`, set the desired language, use the site's
Fullscreen button, and inspect readability at the actual display resolution. Test
one real QR label with the phone. Physical phones, Samsung Internet/other browsers,
native-speaker review, OS installation and physical print/scan remain manual checks.
