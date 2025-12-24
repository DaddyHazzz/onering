# Phase 6.3 — Production Hardening / Observability / Limits

**Objectives**
- Add robust rate limiting (REST + WS) with per-user + per-IP tiers.
- Add audit logging for sensitive actions (create / append / pass / add-collab).
- Add structured request tracing (request_id) across REST + WS events.
- Add production-grade error normalization (consistent error codes).
- Add WS connection limits + backpressure (per-draft rooms, per-user sockets).
- Add security hardening: origin checks, payload size limits, input validation.
- Add ops documentation and configuration knobs.

**Constraints (LOCKED)**
- REST/WS contracts remain unchanged; no response shape changes.
- Existing tests stay green; new tests isolated and opt-in via env.
- Defaults are safe for local dev/tests (features OFF unless enabled).
- Never log secrets; truncate potentially sensitive payloads.

---

## Request ID & Structured Logging
- **Middleware**: `backend/core/middleware/request_id.py`
  - Use `X-Request-Id` if provided; otherwise generate `uuid4`.
  - Attach to `request.state.request_id`; add `X-Request-Id` response header.
- **Logging helper**: `backend/core/logging.py`
  - `log_event(level, msg, *, request_id, user_id=None, draft_id=None, extra={})`
  - Safe truncation for content fields; no secret logging.
- **WS**:
  - On connect, assign `connection_id` and `request_id`.
  - Broadcast events carry `request_id` (from REST if present, else "n/a").

## Rate Limiting (REST)
- **Limiter**: token-bucket in-memory (`backend/core/ratelimit.py`).
  - Keys: `(user_id, route)` primary; fallback `(ip, route)`.
  - Config (env via `backend/core/config.py`):
    - `RATE_LIMIT_ENABLED` (default `false`)
    - `RATE_LIMIT_PER_MINUTE_DEFAULT` (default `120`)
    - `RATE_LIMIT_BURST_DEFAULT` (default `30`)
  - Policies: stricter for mutations (create draft, append, pass ring, add collab); looser for reads.
  - Response on exceed: 429 with `code="rate_limited"`; include `Retry-After` and rate headers when possible.
- **Middleware**: `backend/core/middleware/ratelimit.py` (no-op when disabled).
- **Tests**: `backend/tests/test_ratelimit.py` (env enables limiter; asserts 429 + headers; disabled state leaves existing tests unchanged).

## Rate Limiting (WS) & Connection Limits
- **Config (config.py)**:
  - `WS_LIMITS_ENABLED` (default `false`)
  - `WS_MAX_SOCKETS_PER_USER` (e.g., 3)
  - `WS_MAX_SOCKETS_PER_DRAFT` (e.g., 100)
  - `WS_MAX_SOCKETS_GLOBAL` (e.g., 1000)
  - `WS_MAX_MESSAGE_BYTES` (default `4096`)
  - `WS_ALLOWED_ORIGINS` (comma list; default `*` in dev)
- **Enforcement** (`backend/api/realtime.py` + `backend/realtime/hub.py`):
  - Validate `Origin` if enabled.
  - Reject oversized inbound messages; send final JSON `{type:"error", code:"payload_too_large"|"ws_limit", message:"..."}` then close with 1008.
  - Enforce per-user, per-draft, global socket limits; track active counts in hub.
- **Tests**: `backend/tests/test_ws_limits.py` (env enables limits; N sockets allowed, N+1 rejected).

## Audit Logging
- **Schema** (`backend/core/database.py` new table `audit_events`):
  - `id` (uuid or serial), `ts` (UTC), `request_id`, `user_id`, `action`, `draft_id` (nullable), `metadata` (json/text, truncated), `ip` (nullable), `user_agent` (nullable).
- **Service** (`backend/features/audit/service.py`):
  - `record_audit_event(...)` with safe truncation + PII guardrails.
- **Wiring** (`backend/features/collaboration/service.py`):
  - Log on `create_draft`, `append_segment` (segment_id, content_len, idempotency_key), `pass_ring` (from/to), `add_collaborator` (collaborator_id, role).
- **Config**:
  - `AUDIT_ENABLED` (default `false`)
  - `AUDIT_SAMPLE_RATE` (default `1.0`)
- **Tests**: `backend/tests/test_audit_logging.py` (enable audit, perform mutation, assert row inserted).

## Error Contract Hardening
- Standardize codes in `backend/core/errors.py` and handlers:
  - `rate_limited` for REST limiter 429
  - `ws_limit` for WS limit violations
  - `payload_too_large` for WS/REST body size violations
  - Existing codes remain unchanged (ring_required, forbidden, etc.)
- **Tests**: `backend/tests/test_error_contract.py` (add/adjust assertions as needed, without breaking existing ones).

## Security Hardening (WS + REST)
- Origin checks for WS (config-driven; allow `*` in dev).
- Payload size limits for WS messages; fail with `payload_too_large`.
- Input validation: reuse existing Pydantic models; ensure rate-limit middleware validates presence of user/ip before keying.
- No secret logging; truncate content fields in logs/audit.

## Ops Documentation & Env
- Update `.env.example` with all new knobs (RATE_LIMIT_*, WS_*, AUDIT_*).
- Add `docs/OPS_PROD_CHECKLIST.md` with recommended production settings, monitoring signals, expected logs, scaling notes, and in-memory limiter caveats (future Redis/DB-backed option).

## Testing Plan
- Run new targeted suites:
  - `python -m pytest backend/tests/test_request_id_middleware.py -q`
  - `python -m pytest backend/tests/test_ratelimit.py -q`
  - `python -m pytest backend/tests/test_ws_limits.py -q`
  - `python -m pytest backend/tests/test_audit_logging.py -q`
  - `python -m pytest backend/tests/test_error_contract.py -q`
- Full gate:
  - `python -m pytest backend/tests -q`
  - `pnpm test -- --run`

## Rollout Notes
- All features OFF by default (dev/test). Enable via env for staging/prod.
- In-memory implementations are acceptable for this phase; note need for Redis/DB-backed rate limits in future.
- Request IDs propagated across REST + WS; logs and audit include `request_id` for correlation.
- Limits and audits must never break existing clients; failures return existing envelope shapes with new `code` values only where specified.
