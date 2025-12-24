## Phase 6.4 — Deployment Readiness Spec

### CI Plan (PR vs main)
- **Triggers:** `pull_request` + `push` to `main`.
- **Jobs:**
  - **frontend:** Node 18+, install via `pnpm install`, run `pnpm lint`, `pnpm test -- --run`, `pnpm typecheck`.
  - **backend:** Python 3.11, install `backend/requirements.txt`, run `python -m pytest backend/tests -q`.
- **Caching:** node_modules/pnpm store and pip cache to speed repeat runs (optional, best-effort).
- **Failure gates:** Any job fail → CI fails; no deploy.
- **Local all-tests:** `pnpm test -- --run && python -m pytest backend/tests -q` (PowerShell uses same syntax).

### Health Checks Strategy
- **/healthz (liveness):** unauthenticated, returns `{ "status": "ok" }`. No dependencies.
- **/readyz (readiness):** unauthenticated, returns `{ "status": "ok" }` when DB reachable and required tables exist (drafts, audit_events). On failure: `{ "status": "error", "detail": "..." }` with HTTP 503.
- **Startup validation:** `validate_config(strict: bool)` guarded by `CONFIG_STRICT`; strict mode raises on missing required prod secrets, non-strict logs warnings.

### Smoke Test Plan (REST + WS)
- Script: `scripts/smoke_test.py` driven by `BASE_URL` (default `http://localhost:8000`).
- Steps: create draft → add collaborator → append segment → WS connect `/v1/ws/drafts/{id}` (wait for event/ping) → pass ring → assert 200s and payloads contain `data`.
- Auth: uses `X-User-Id` header (simple non-secret header) only.
- Output: clear PASS/FAIL; non-zero exit on failure; no secret logging.

### Rollback Approach
- **Application rollback:** redeploy previous image/artifact; configs stay intact.
- **Database:** no destructive migrations in 6.4; audit_events already present. Future migrations: prefer backward-compatible additive changes; keep old code path until rollout complete.
- **Feature flags/env toggles:** rate limits, WS limits, audit, config strictness all env-controlled; disable limits in incident to stabilize.
- **Verification post-rollback:** hit `/healthz`, `/readyz`, run smoke script; monitor logs for request_id-correlated errors.

### Scope Notes
- No API shape changes allowed; new endpoints are additive and unauthenticated (health). Default behavior unchanged in dev/test (strict checks off, limits off).