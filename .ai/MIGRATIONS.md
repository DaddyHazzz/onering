Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# Database Migrations

## Current Approach
- Schema defined via SQLAlchemy metadata in `backend/core/database.py`.
- Tables created idempotently with `create_all_tables()`; lightweight upgrades applied in `apply_schema_upgrades()`.
- Phase 6.3 introduced `audit_events`; table is included in metadata and created automatically.

## Strategy Going Forward
- Prefer additive, backward-compatible changes (new columns nullable/defaulted, new tables) to allow zero-downtime deploys.
- For structural changes, adopt Alembic (recommended) to generate/version migrations and run them as part of deploys.
- Until Alembic is adopted, document manual SQL changes alongside code changes and gate deployments on `/readyz`.

## Manual Migration Steps (temporary)
1) Ensure `DATABASE_URL` points to target DB and backups are current.
2) Run `python -c "from backend.core.database import create_all_tables; create_all_tables()"` to apply metadata-defined tables.
3) Apply any ad-hoc SQL patches (if required) using `apply_schema_upgrades()` patterns (idempotent `ALTER TABLE ... IF NOT EXISTS`).
4) Verify critical tables exist: `drafts`, `draft_segments`, `draft_collaborators`, `ring_passes`, `audit_events` (also checked by `/readyz`).

## Migration Safety
- Always deploy app code that tolerates old and new schemas during rollout.
- Keep destructive operations (drops/renames) for scheduled maintenance with explicit backups and restore plan.
- Capture migration run logs and tie to `request_id`/deployment identifier.

## Phase 10.1 Enforcement Readiness
- Ensure `audit_agent_decisions` exists before enabling `ONERING_ENFORCEMENT_MODE=advisory|enforced`.
- Recommended preflight:
  - `python -c "from backend.core.database import create_all_tables; create_all_tables()"` on deployment host.

## Phase 10.2 Publish Integration
- Ensure `publish_events` exists before enabling token issuance modes.
- If using manual migrations, run `create_all_tables()` after deploying updated metadata.

## Phase 10.2 Ledger-Truth Migration (Dec 26, 2025)
- Apply SQL migration: `prisma/migrations/20251226_phase10_2_ledger_truth/migration.sql`
  - Adds indices for `publish_events`, `ring_ledger`, `ring_pending`
  - Adds tables: `ring_clerk_sync`, `publish_event_conflicts`
- Run ledger backfill/validator (dry-run default):
  - `python -m backend.workers.backfill_ring_ledger --dry-run`
  - Use `--live` only after reviewing report and taking a backup.
- Optional: run Clerk sync worker (dry-run default):
  - `python -m backend.workers.sync_clerk_ring_balance --dry-run`

Notes:
- Ledger is the source of truth in shadow/live; avoid direct writes to `users.ringBalance` outside the ledger service.

