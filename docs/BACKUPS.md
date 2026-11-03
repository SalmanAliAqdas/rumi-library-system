# Private backup and restore procedure

Public CSV and the browser's offline catalog contain public catalogue fields only.
Neither can restore borrowers, loans, users, permissions, settings, retry receipts
or the full database. Keep backups private, encrypted where possible, with access
restricted to the librarian. Keep a second protected copy on a separate device.
Choose a backup frequency matching how much new work you can afford to lose.

Use a directory **outside the checkout**, static files and public downloads, such as
`C:\PrivateLibraryBackups`. Never send backups to GitHub. The repository also ignores
`backups/`, `exports/`, database files, CSVs and dump archives as a secondary guard.
Preserve the app version, migration files and dependencies with each backup, and
store necessary configuration/credentials separately in a password manager.

## Local SQLite

1. Stop `runserver` and all other processes that can write this database (including
   admin sessions, scripts and another server). Confirm they are stopped. Keep them
   stopped until copying finishes; copying a live database file is unsafe.
2. Create the private directory yourself. Choose a **new** dated destination. In
   PowerShell, from the project directory, after confirming `db.sqlite3` is the
   actual configured database:

   ```powershell
   $backupPath = 'C:\PrivateLibraryBackups\rumi-YYYYMMDD-HHMM.sqlite3'
   if (Test-Path -LiteralPath $backupPath) { throw 'Choose a new backup filename' }
   Copy-Item -LiteralPath '.\db.sqlite3' -Destination $backupPath -ErrorAction Stop
   Get-FileHash -LiteralPath $backupPath -Algorithm SHA256
   ```

   Use this simple copy procedure only after a clean shutdown, with no outstanding
   `db.sqlite3-wal` file. If WAL files remain or stopping writers is impractical,
   use SQLite's supported online backup API instead of copying individual files;
   see [SQLite backup API](https://www.sqlite.org/backup.html) and
   [Python sqlite3 backup](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup).
3. Verify the backup by opening a **copy** in a separate private test checkout with
   its own configuration. Use a new destination, never overwrite the working DB.
   Point that checkout at the copied file (its own `db.sqlite3` with no DATABASE_URL),
   run `python manage.py check`, and run SQLite `PRAGMA integrity_check` on the copy.
   Record a clean result and confirm inventory/loan counts and multilingual text.
4. In that test checkout, sign in privately, check borrower/return history, visibility,
   accessions, availability and permissions. Verify that creating an isolated test
   copy allocates the next accession correctly. Test records belong only there.
   Restart the original server after the backup is safely copied.

## Future Neon / PostgreSQL

Documentation only: no database was provisioned, exported or restored in Phase 4.
Use a PostgreSQL client version matching the server. Obtain **direct, unpooled**
source and separate, empty test-target connections from the provider. Confirm their
hostnames/database names independently before running a restore. Do not point the
application or restore command at production accidentally.

Prefer libpq service definitions in a private `pg_service.conf` plus a protected
password file, rather than putting passwords in commands/history. The following
names and paths are placeholders, not configured services:

```powershell
pg_dump --dbname='service=RUMI_SOURCE_DIRECT' --format=custom --file='C:\PrivateLibraryBackups\rumi-YYYYMMDD-HHMM.dump'
pg_restore --list 'C:\PrivateLibraryBackups\rumi-YYYYMMDD-HHMM.dump'
# Only against a separately authorized, empty TEST database:
pg_restore --dbname='service=RUMI_EMPTY_TEST_DIRECT' --no-owner --no-privileges --exit-on-error --single-transaction 'C:\PrivateLibraryBackups\rumi-YYYYMMDD-HHMM.dump'
```

Define services privately with `host=<DIRECT_HOST>`, `dbname=<DATABASE>`,
`user=<ROLE>`, `sslmode=require` and provider-required connection options; keep
passwords out of this repository. Check command exit codes. A custom-format dump
is a consistent database snapshot even with concurrent writers, but later writes
are absent. Stop writes for a controlled transfer. `pg_dump` is database-scoped;
cluster roles/global objects require a separate administrator plan. The test
restore deliberately does not restore original ownership/grants; assign and verify
appropriate permissions on the test target separately.

Check integrity, migrations (`showmigrations`, then `migrate --plan`), counts,
multilingual text, private loans/returns, public visibility, next accession and
active-loan constraints. Run the full suite against a **disposable test database**
with permission for Django to create its test DB, including concurrency tests.
Retain a written restore result and backup hash. Never test restoration by
overwriting the source. Dumps contain private records and authentication data.

Official provider guidance checked November 3, 2026:
[Neon pg_dump/pg_restore](https://neon.com/docs/manage/backup-pg-dump) recommends
direct connections and matching client versions. Its
[history window documentation](https://neon.com/docs/postgres/backup-restore/history-window)
currently lists Free retention as **6 hours, capped at 1 GB of history**. Check the
actual project settings and current plan before relying on restoration; setting
history to zero disables it. Do not assume multi-day free recovery or paid backup
schedules. Keep independent private dumps for longer retention.
[PostgreSQL connection services](https://www.postgresql.org/docs/current/libpq-pgservice.html)
and [password files](https://www.postgresql.org/docs/current/libpq-pgpass.html)
describe credential handling.

This procedure has not been executed on a hosted database. Production backup,
restore and PostgreSQL concurrency verification remain required before launch.
