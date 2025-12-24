# Ops / Production Checklist (Phase 6.3)

## Configuration
- Rate limits: enable in prod
  - `RATE_LIMIT_ENABLED=true`
  - `RATE_LIMIT_PER_MINUTE_DEFAULT` (e.g., 120)
  - `RATE_LIMIT_BURST_DEFAULT` (e.g., 30)
- WebSocket limits:
  - `WS_LIMITS_ENABLED=true`
  - `WS_MAX_SOCKETS_PER_USER` (e.g., 3)
  - `WS_MAX_SOCKETS_PER_DRAFT` (e.g., 100)
  - `WS_MAX_SOCKETS_GLOBAL` (e.g., 1000)
  - `WS_MAX_MESSAGE_BYTES` (e.g., 4096)
  - `WS_ALLOWED_ORIGINS` (comma list; no `*` in prod)
- Audit logging:
  - `AUDIT_ENABLED=true`
  - `AUDIT_SAMPLE_RATE` (1.0 for full, <1.0 to sample)

## Monitoring & Logs
- All REST/WS requests carry `X-Request-Id`; correlate logs by `request_id`.
- Log events use `log_event(...)` with safe truncation; secrets are not logged.
- Expect structured JSON logs in production (Pretty logs in dev).

## Rate Limiting Behavior
- REST: token-bucket per user (or IP fallback) per-route; mutations stricter than reads.
- Headers on 429: `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Default OFF for tests/dev; enable in staging/prod.

## WebSocket Controls
- Origin check enforced when WS limits enabled (set explicit allowlist).
- Limits enforced per user, per draft room, and global.
- Oversized WS messages rejected with `code=payload_too_large` and close code 1008.
- Error responses before close: `{ "type": "error", "code": "ws_limit" | "payload_too_large", ... }`.

## Audit Logging
- Table: `audit_events` (ts, request_id, user_id, action, draft_id, metadata, ip, user_agent).
- Safe truncation applied to metadata/user_agent.
- Falls back to in-memory buffer if DB unavailable (not recommended for prod).

## Deployment Notes
- Ensure database reachable if audit logging is enabled.
- In-memory rate limiter is best-effort; for multi-instance deployments, move to Redis-backed limiter.
- Keep WS limits conservative to prevent abuse; tune per traffic patterns.
- Validate env files in CI with the new knobs present.

## Runbook
- If 429s spike: check rate limit headers, adjust defaults, or raise burst for specific routes.
- If WS connects rejected: inspect logs for `ws_limit` messages and adjust max sockets/origins.
- If audit writes fail: logs emit `Audit event write failed`; verify DB connectivity and schema.

## Health & Readiness (Phase 6.4)
- `/healthz` liveness (no dependencies) and `/readyz` readiness (DB reachable + core tables present).
- Set `CONFIG_STRICT=true` in prod to fail fast on missing secrets; keep `false` in dev/tests to log warnings.

## Smoke & CI (Phase 6.4)
- CI runs: frontend (`pnpm lint`, `pnpm test -- --run`, `pnpm typecheck`) and backend (`python -m pytest backend/tests -q`) on PR + main.
- Smoke: `python scripts/smoke_test.py` with `BASE_URL`, `SMOKE_USER_ID`, `SMOKE_COLLAB_ID` set.
- Pre-commit helpers: `scripts/pre-commit.sh` / `.ps1` run lint/typecheck/tests and skip backend tests if `DATABASE_URL` is unset.
