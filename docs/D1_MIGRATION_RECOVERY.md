# NCET VerifyFlow: PostgreSQL to Cloudflare D1 recovery and migration

Status: preparation only. Cloudflare D1 staging database created; no production cutover or source data export completed.

## 1. Preserve the source first
The Render PostgreSQL database was reported suspended after expiry on 2026-11-14. The read-only connectivity test failed. Restore access before the Render recovery window expires (expected 2026-11-28; confirm in dashboard). Do not delete or replace the source. No migration tool can recover inaccessible records. Obtain owner authorization before any paid upgrade. If a previous secure PostgreSQL backup exists, restore it into an isolated PostgreSQL database instead.

Use the existing settings encryption key (do not rotate during migration). Keep passwords, tokens, backups and student records outside Git and chat. Store archives on encrypted, access-restricted storage; on Windows explicitly restrict ACLs. A native pg_dump archive preserves PostgreSQL data and schema; any disk or object-store attachments require independent backups.

## 2. Run local preparation
Install the project requirements and matching PostgreSQL client tools (pg_dump and pg_restore). Set NCET_SOURCE_DATABASE_URL securely in the local shell from the restored database or isolated clone, with TLS for an external endpoint. Do not paste the URI into commands or Git.
Run from repository root:
    python scripts/d1_migration_preflight.py backup /secure/off-repo/backups
    python scripts/d1_migration_preflight.py inventory
    python scripts/d1_migration_preflight.py schema /secure/off-repo/ncet-candidate-schema.sql

The backup command creates a private native PostgreSQL archive, checks the archive catalog and computes SHA-256. It does not prove restoration; perform an actual restore drill. The inventory uses one read-only repeatable-read transaction; it reports counts and byte sizes, no student data. Freeze production writes for the final consistent snapshot and reconciliation. The schema command runs all current Alembic migrations against a disposable local SQLite database and extracts DDL only. It does not copy any rows, initialize D1, or mark Alembic revisions applied.

## 3. Required application changes BEFORE D1 import/cutover
Cloudflare D1 is SQLite over a remote API, not PostgreSQL or a local SQLite file. Do not point DATABASE_URL to the D1 HTTP URL or bypass the production validation in app/serve.py. Keep the existing Render deployment configuration intact until replacement is verified.

- Implement a reviewed D1 data-access layer with parameterized SQL, type conversion (timestamps, booleans, nullable values, JSON), transactional batches for writes, idempotency, and bounded retries. Do not emulate interactive ORM transactions by issuing separate HTTP calls.
- Replace with_for_update / SKIP LOCKED semantics in app/taskflow.py, app/worker.py, app/main.py and app/admin_cleanup.py with atomic conditional state transitions, unique claims, lease recovery and concurrency tests. Preserve authorization and audit events within the appropriate atomic operation.
- Move large binary fields to private object storage. Existing binary columns include attachments.bytes_content, task reference PDFs, task submission content, and student profile photos. app/storage.py already supports S3-compatible endpoints for attachment storage, but other binary models require explicit migration. Preserve names, MIME types, IDs and SHA-256; verify object integrity before nulling source BLOBs in a staging copy. No public bucket. R2 requires separate setup and quota/billing review; do not activate without authorization.
- Use explicit, versioned D1 migrations. Verify every source table and index against the SQLite candidate and reconcile PostgreSQL-specific semantics. Ensure foreign keys, uniqueness, nullable values, cascade behaviors, generated IDs and timezone handling match.
- Validate against D1 limits: 500 MB per free database; 2 MB per row/string/BLOB; 100 KB per SQL statement; 100 bound parameters. Inventory is not a capacity guarantee. Free tier also has 5 million rows read/day and 100,000 written/day.
- Export from an isolated restored copy; transform into D1-compatible SQL or bound batches, private objects separately. Do not import a raw PostgreSQL dump into D1. Import only into staging. Reconcile counts and deterministic per-table digests (including full original attachment digests), foreign keys, active admin access, encrypted integration settings, and audit logs. Never drop or skip a row silently.

## 4. Release gates
1. Restore and verify native backup; verify source rows and attachment inventory.
2. Run migration preflight and review actual source schema.
3. Implement and test D1 backend and private object storage against synthetic data.
4. Import a protected snapshot into staging and verify all counts, constraints and hashes.
5. Exercise login, role permissions, upload, AI review, HOD decisions, student profiles, notifications and concurrent worker claims; check restart durability and free quotas.
6. Freeze writes, capture final backup, reconcile again. Only then switch Render to the new backend, confirm /healthz and authenticated flows. Keep source and backup intact for rollback. Reconcile any new writes before rollback.

No changes to production configuration are included in this branch.
References: https://developers.cloudflare.com/d1/platform/limits/ ; https://developers.cloudflare.com/d1/platform/pricing/ ; https://developers.cloudflare.com/d1/best-practices/import-export-data/ ; https://render.com/docs/free#free-postgres
