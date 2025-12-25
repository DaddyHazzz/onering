Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# Deploy Runbook

## Preflight
- Verify required env vars set: Clerk keys, Stripe keys, DATABASE_URL, GROQ_API_KEY, REDIS_URL, RATE_LIMIT_* (if enabled), WS_* (if enabled), AUDIT_* (if enabled), CONFIG_STRICT.
- Run `pnpm test -- --run`, `pnpm typecheck`, `python -m pytest backend/tests -q` locally.
- Review latest CI run (frontend + backend jobs) on the branch to deploy.

## Deploy Steps
1) Build/publish artifact or container.
2) Apply config/secret updates in the target environment.
3) Deploy to staging; run smoke test (`python scripts/smoke_test.py` with `BASE_URL` set to staging).
4) Check health:
   - `GET /healthz` → `{ "status": "ok" }`
   - `GET /readyz` → `{ "status": "ok" }` (DB reachable, tables present)
5) Promote to production once staging is green.

## Post-Deploy Verification
- Monitor logs for `request_id`-tagged errors during first 15 minutes.
- Validate rate-limit/audit flags match intended settings (often disabled in dev, enabled in prod).
- Confirm WebSocket connect/disconnect counts are stable (no immediate limit blocks).

## Rollback
- Redeploy previous known-good artifact.
- If database migrations were applied, ensure they are backward-compatible (Phase 6.4 has no destructive migrations).
- Re-run health checks and smoke test after rollback.

## Logs & Observability
- Backend logs: structured JSON in production; correlate via `request_id`.
- WS/log events use `log_event(...)` with safe truncation; secrets not logged.
- Rate limit rejections return 429 with headers; WS limit errors emit `ws_limit` events before close.

## Safety Knobs
- `CONFIG_STRICT=false` to avoid startup crash on missing secrets (use only in non-prod).
- `RATE_LIMIT_ENABLED`, `WS_LIMITS_ENABLED`, `AUDIT_ENABLED` can be toggled via env; disable during incident to stabilize traffic.
