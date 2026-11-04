# SQLite to separate PostgreSQL transfer rehearsal

This is a controlled application-data transfer, not a replacement for a full
private backup. No real export/import or hosted connection was made in Phase 5.
Rehearse before entering the full real collection; small gradual entry is fine.

1. Stop every SQLite writer and close old librarian forms. Follow [BACKUPS.md](BACKUPS.md)
   to make and verify a private stopped-source backup outside this checkout. Keep
   the source untouched and offline for the entire transfer. Rehearse from a copy
   in a separate private checkout with the **same commit and migrations**. Apply
   Phase 5's additive migration to that copy first. Check `PRAGMA integrity_check`.
2. In the source-copy checkout, with its SQLite configuration selected, run:

   ```powershell
   python manage.py check
   python manage.py audit_catalog > C:\PrivateLibraryBackups\source-audit.txt
   python manage.py dumpdata catalog --exclude catalog.submission --exclude catalog.lookupgate --natural-foreign --natural-primary --indent 2 --output C:\PrivateLibraryBackups\catalog.json
   Get-FileHash -LiteralPath C:\PrivateLibraryBackups\catalog.json -Algorithm SHA256
   ```

   Use fresh destination filenames; don't overwrite prior backups. The fixture
   contains **private borrowers and contacts** if loans exist. It includes library
   settings, shelves, categories/translations, contributors/roles, languages,
   editions/aliases/metadata attribution, copies/visibility/volumes, accessions,
   AccessionSequence and all loan dates/relationships. Keep it encrypted/private.
   The read-only audit emits only model counts and hashes, public/hidden counts,
   active loans and public availability. It checks foreign keys, accession shape,
   uniqueness, sequence floor and loan date relationships. Stop writes so separate
   export/audit commands observe the same state.
3. Create a **fresh, separate, empty Rumi PostgreSQL test database** only after
   authorization. Confirm host/database/role against the Rumi account console
   privately. In the destination checkout put the **direct** URL in private `.env`
   using an editor, not a password-containing shell command. A different existing
   database or existing Neon project is never a transfer target. Run:

   ```powershell
   python manage.py migrate --plan
   python manage.py migrate
   python manage.py loaddata C:\PrivateLibraryBackups\catalog.json
   python manage.py audit_catalog > C:\PrivateLibraryBackups\destination-audit.txt
   Compare-Object (Get-Content C:\PrivateLibraryBackups\source-audit.txt) (Get-Content C:\PrivateLibraryBackups\destination-audit.txt)
   ```

   Check exit codes after every command. Expect no audit differences. Investigate
   any mismatch before proceeding. Do not import into a populated target, flush
   production, or use bulk_create/normal Copy.save to replay preserved accessions.
   Django deserialization uses raw saves, preserving permanent primary keys and
   accessions; relational data is restored transactionally with constraints checked.
   Languages use natural code keys, reusing migration-created en/ur/ar even when
   their numeric IDs differ. Existing additive migrations are the schema authority.
4. Django auth/contenttypes/permissions/sessions are **not** transferred. Migrate
   recreates their correct content types and permissions for this installation;
   copying SQLite IDs could corrupt permission relationships. Recreate the admin
   interactively and grant staff permissions explicitly. Submission receipts are
   omitted because they reference local users and signed old forms; lookup/login
   throttles are ephemeral. Use a new production SECRET_KEY and expire old sessions.
   Full disaster-recovery backups still include these tables.
5. `loaddata` resets PostgreSQL auto-PK sequences for loaded models. Inspect
   `python manage.py sqlsequencereset catalog` if diagnosing sequence state; review
   its SQL before any deliberate execution. **AccessionSequence is different**:
   it is application data and must be restored. The audit rejects a value below
   imported accessions. On the disposable test target, create one new edition,
   contributor, shelf and copy through normal forms; verify fresh primary keys,
   the next unused accession, and relationships. Retire the rehearsal database
   rather than copying these extra fixtures to production. See
   [Django fixture commands](https://docs.djangoproject.com/en/5.2/ref/django-admin/#loaddata).
6. Compare the full per-model hashes, not just totals. These include identifiers,
   multilingual text, M2M membership, foreign keys, visibility and borrower/loan
   data without printing their contents. Also inspect private forms and public
   pages: hidden copies must 404 and be absent from sitemap, search, snapshot and
   CSV; editions with no public copies must be absent. Mixed visible/hidden
   editions expose only visible copies. Compare active/returned loans and public
   availability; issue and return an isolated fixture and check history. Run
   PostgreSQL concurrency tests on a separately disposable Django test database,
   including allocation, competing loans and lookup reservations.
7. Rehearse a full direct PostgreSQL dump/restore to another empty test target using
   [BACKUPS.md](BACKUPS.md). Record the audit/hash comparison and constraints results.
   Only then repeat the reviewed transfer against a new empty launch database,
   before accepting writes. Do not run seed_demo. Decide explicitly whether any
   clearly fictional source demo records should be included; never silently delete
   them or mix demo and full real inventory.

Rollback: keep Vercel traffic disabled/protected; abandon the failed destination,
preserve diagnostic reports privately, and resume the original SQLite source only
after confirming it was never modified. Restore only to another new target for a
retry. After the destination has accepted real writes, switching back would lose
those writes: stop and reconcile them deliberately before rollback. Never overwrite
the source or try to merge two independently edited collections automatically.
SQLite round-trip tests do not establish PostgreSQL sequence, TLS or concurrency
correctness. Those remain required before launch.
