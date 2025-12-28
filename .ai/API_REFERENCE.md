
Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# API Reference (Canonical)

This document summarizes stable API contracts. For implementation details, see backend route files under backend/api/.

Last Updated: December 25, 2025

## Authentication
- All endpoints require Clerk-authenticated user unless stated as public.
- Pass `X-User-Id` header in tests to simulate authenticated user.

## Collaboration

- POST /api/collab/drafts
  - Create a new draft
  - Body: { title: string, platform: "x"|"ig"|"tiktok" }
  - Returns: { id, creator_id, ring_state, created_at }

- GET /api/collab/drafts/{draft_id}
  - Get draft by id
  - Returns: CollabDraft

- POST /api/collab/drafts/{draft_id}/segments
  - Add a segment
  - Body: { text: string }
  - Returns: updated draft

- POST /api/collab/drafts/{draft_id}/ring/pass
  - Pass ring to another collaborator
  - Body: { target_user_id: string }
  - Returns: { success: true, to_user_id }

## Analytics

- GET /api/collab/drafts/{draft_id}/analytics
  - Draft analytics snapshot
  - Query: optional now (ISO8601) for deterministic tests
  - Returns: { data: { views, contributors, ring_passes, ... }, computed_at }

- GET /v1/analytics/leaderboard
  - Leaderboard across users
  - Query: optional now
  - Returns: [{ user_id, ring_earned, posts }]

## Insights

- GET /api/insights/drafts/{draft_id}
  - Draft insights, recommendations, alerts

  ## External Platform API (Phase 10.3)

  ### Authentication
  - All `/v1/external/*` endpoints require Bearer token authentication
  - Format: `Authorization: Bearer osk_<key>`
  - API keys created via admin endpoints (see below)
  - Keys have scopes and rate limit tiers

  ### Available Scopes
  - `read:rings` — Access ring balances and transactions
  - `read:drafts` — Access draft metadata
  - `read:ledger` — Access token ledger entries
  - `read:enforcement` — Access enforcement statistics

  ### Rate Limit Tiers
  - **free:** 100 requests per hour
  - **pro:** 1000 requests per hour
  - **enterprise:** 10000 requests per hour

  ### External Endpoints

  - GET /v1/external/me
    - Whoami endpoint
    - Returns: { key_id, scopes, rate_limit: { current, limit, resets_at } }

  - GET /v1/external/rings
    - List rings for authenticated user
    - Requires: `read:rings` scope
    - Returns: [{ id, balance, earned, staked }]

  - GET /v1/external/rings/{ring_id}
    - Ring detail with ownership check
    - Requires: `read:rings` scope
    - Returns: { id, balance, earned, staked, transactions: [] }

  - GET /v1/external/drafts
    - List draft metadata
    - Requires: `read:drafts` scope
    - Query: limit, offset (pagination)
    - Returns: { drafts: [], total }

  - GET /v1/external/ledger
    - Token ledger entries
    - Requires: `read:ledger` scope
    - Query: limit, offset (pagination, default limit=20)
    - Returns: { entries: [{ id, amount, balance_before, balance_after, timestamp }], total }

  - GET /v1/external/enforcement
    - Enforcement statistics
    - Requires: `read:enforcement` scope
    - Returns: { pass_count, fail_count, pass_rate }

  ### Admin Endpoints (API Key Management)

  - POST /v1/admin/external/keys
    - Create API key
    - Requires: Admin auth (X-Admin-Key header)
    - Body: { owner_user_id, scopes: string[], tier: "free"|"pro"|"enterprise", expires_in_days?: number, ip_allowlist?: string[] }
    - Returns: { key_id, full_key, scopes, tier, created_at, expires_at, ip_allowlist }
    - **Note:** Full key only returned once

  - POST /v1/admin/external/keys/{key_id}/rotate
    - Rotate API key (Phase 10.3)
    - Requires: Admin auth
    - Body: { preserve_key_id?: bool (default true), ip_allowlist?: string[], expires_in_days?: number }
    - Returns: { key_id, full_key, scopes, tier, expires_at, ip_allowlist }
    - **Note:** Full key only returned once; old secret invalidated immediately

  - POST /v1/admin/external/keys/{key_id}/revoke
    - Revoke API key
    - Requires: Admin auth
    - Returns: { success: true }

  - GET /v1/admin/external/keys/{owner_user_id}
    - List user's API keys
    - Requires: Admin auth
    - Returns: [{ key_id, scopes, tier, is_active, created_at, last_used_at, expires_at, ip_allowlist, rotated_at }]

  - POST /v1/admin/external/webhooks
    - Create webhook subscription
    - Requires: Admin auth
    - Body: { owner_user_id, url, events: string[] }
    - Returns: { id, url, secret, events, created_at }
    - **Note:** Secret only returned once

  - GET /v1/admin/external/webhooks/{owner_user_id}
    - List user's webhooks
    - Requires: Admin auth
    - Returns: [{ id, url, events, is_active, created_at }]

  - DELETE /v1/admin/external/webhooks/{webhook_id}
    - Delete webhook subscription
    - Requires: Admin auth
    - Returns: { success: true }

  ### Webhook Events

  Events emitted when enabled (ONERING_WEBHOOKS_ENABLED=1):
  - `draft.published` — Draft published to platform
  - `ring.earned` — RING tokens earned from issuance
  - `ring.spent` — RING tokens spent via ledger
  - `ring.drift_detected` — Ledger vs balance drift detected during reconciliation
  - `enforcement.failed` — Agent enforcement action failed (QA reject, receipt invalid, etc.)

  ### Webhook Delivery (Phase 10.3)

  - **Worker:** `python -m backend.workers.webhook_delivery --loop`
  - **Retry backoff:** Configurable via `ONERING_WEBHOOKS_BACKOFF_SECONDS` (default "60,300,900")
  - **Max attempts:** `ONERING_WEBHOOKS_MAX_ATTEMPTS` (default 3)
  - **Dead-letter:** After max attempts, deliveries marked as `dead` with last_error persisted
  - **Replay protection:** Events outside `ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS` (default 300) marked as REPLAY_EXPIRED

  ### Webhook Signature Verification (Phase 10.3)

  **CRITICAL SECURITY NOTE:** The webhook secret (`whsec_*`) is **NEVER stored in git**. It is:
  - Set only via environment variables in production (GitHub Secrets)
  - Generated fresh in Stripe Dashboard and copied to `.env` (git-ignored) for local development
  - Rotated immediately if accidentally exposed (see [SECURITY_SECRETS_POLICY.md](SECURITY_SECRETS_POLICY.md))

  Webhooks are signed with HMAC-SHA256 over `timestamp.event_id.raw_body_bytes`. Verify using:

  ```python
  import hmac
  import hashlib

  def verify_webhook(secret, signature_header, timestamp, event_id, body_bytes):
      """Verify OneRing webhook signature."""
      # Extract v1 signature from header
      provided = None
      for part in signature_header.split(','):
          if part.strip().startswith('v1='):
              provided = part.strip().split('=', 1)[1]
              break
      if not provided:
          return False
    
      # Replay protection
      now = int(datetime.now(timezone.utc).timestamp())
      if abs(now - timestamp) > 300:  # 5-minute window
          return False
    
      # Compute expected signature
      signed_content = f"{timestamp}.{event_id}.".encode() + body_bytes
      expected = hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
    
      return hmac.compare_digest(provided, expected)
  ```

  Headers sent with webhooks:
  - `X-OneRing-Signature` — HMAC signature (format: `t=<timestamp>,e=<event_id>,v1=<hex>`)
  - `X-OneRing-Event-Type` — Event type (draft.published, ring.earned, enforcement.failed)
  - `X-OneRing-Event-ID` — Unique event identifier
  - `X-OneRing-Timestamp` — Unix timestamp (for replay protection)

  Payload structure:
  ```json
  {
    "event_id": "evt_abc123",
    "event_type": "ring.earned",
    "timestamp": 1735150800,
    "data": {
      "user_id": "user_123",
      "amount": 10,
      "mode": "shadow",
      "ledger_id": "ledger_456",
      "reason_code": "ISSUED"
    }
  }
  ```

  ### Rate Limit Headers (Phase 10.3)

  All external API responses include standard rate-limit headers:
  - `X-RateLimit-Limit` — Maximum requests per hour for this tier
  - `X-RateLimit-Remaining` — Remaining requests in current window
  - `X-RateLimit-Reset` — Unix timestamp when window resets

  Rate limits are enforced atomically with concurrency-safe increments (prevents quota over-issuance).

  429 Response on Rate Limit Exceeded:
  ```json
  {
    "detail": "Rate limit exceeded (101/100 requests this hour)"
  }
  ```
  Headers included in 429 response for client retry logic.

  ### IP Allowlist Enforcement (Phase 10.3)

  API keys can specify an `ip_allowlist` array. When set, validation checks `X-Forwarded-For` (proxy) or `request.client.host`:
  - If client IP not in allowlist → 401 Unauthorized
  - Empty allowlist → all IPs allowed

  Admin can update allowlist via rotate endpoint without changing key secret.

  ### API Key Rotation (Phase 10.3)

  Best practices for zero-downtime rotation:
  1. Create new key with `preserve_key_id=true` (keeps key_id, issues new secret)
  2. Update client configs with new secret
  3. Test new secret in staging
  4. Deploy to production
  5. Old secret invalidated immediately (no grace window)

  For new key_id rotation:
  - Set `preserve_key_id=false`
  - Old key_id deactivated, new key_id issued
  - Update all references to key_id + secret

  ### Monitoring Endpoints (Phase 10.3)

  - GET /v1/monitoring/external/keys
    - Requires: Admin auth (X-Admin-Key)
    - Returns: { totals: [{ tier, active, revoked }], total_active, total_revoked, last_used_at }

  - GET /v1/monitoring/webhooks/metrics
    - Requires: Admin auth
    - Returns: { delivered, failed, dead, pending, delivering, retrying }

  - GET /v1/monitoring/webhooks/recent
    - Requires: Admin auth
    - Query: status?, event_type?, webhook_id?, limit (default 20, max 100)
    - Returns: { deliveries: [{ id, webhook_id, event_id, event_type, status, attempts, last_status_code, last_error, created_at, next_attempt_at }] }

  ### Kill Switches

  Both external API and webhooks are disabled by default for safety:
  - `ONERING_EXTERNAL_API_ENABLED=0` (default) — External API returns 503
  - `ONERING_WEBHOOKS_ENABLED=0` (default) — No webhook events emitted
  - `ONERING_WEBHOOKS_DELIVERY_ENABLED=0` (default) — Delivery worker exits immediately

  Enable explicitly when ready for production use.

  **Phase 10.3 Hardening Checklist Before Enablement:**
  1. ✅ Webhook delivery worker tested (--once and --loop modes)
  2. ✅ Signature verification tested with real consumer
  3. ✅ Replay protection validated (events outside window rejected)
  4. ✅ Rate limit concurrency tested (no quota over-issuance)
  5. ✅ IP allowlist enforcement tested
  6. ✅ Key rotation tested (zero-downtime workflow)
  7. ✅ Dead-letter deliveries monitored (alerting set up)
  8. ✅ Monitoring dashboards deployed (/monitoring/external, /admin/external)
  9. ⏸️ Admin key rotation policy established
  10. ⏸️ Customer onboarding runbook complete
  - Auth: Collaborators only (creator + invited collaborators)
  - Query: optional `now` (ISO8601) for deterministic tests
  - Returns:
    ```json
    {
      "draft_id": "draft-123",
      "insights": [
        {
          "type": "stalled|dominant_user|low_engagement|healthy",
          "severity": "critical|warning|info",
          "title": "string",
          "message": "string",
          "reason": "string (for explainability)",
          "metrics_snapshot": { /* context-specific metrics */ }
        }
      ],
      "recommendations": [
        {
          "action": "pass_ring|invite_user|add_segment|review_suggestions",
          "target_user_id": "string (optional)",
          "reason": "string",
          "confidence": 0.0-1.0
        }
      ],
      "alerts": [
        {
          "alert_type": "no_activity|long_ring_hold|single_contributor",
          "triggered_at": "ISO8601",
          "threshold": "string (e.g. '72h+ no activity')",
          "current_value": "number|string",
          "reason": "string (why alert triggered)"
        }
      ],
      "computed_at": "ISO8601"
    }
    ```

Invariants:
- All insights computed deterministically from draft state
- Alerts based on current state (no averages), works with zero ring passes
- LONG_RING_HOLD: uses `ring_state.passed_at` for current holder duration
- NO_ACTIVITY: threshold 72h since last activity
- SINGLE_CONTRIBUTOR: <2 contributors with 5+ segments
- Access: 403 if not collaborator

## Generation

- POST /v1/generate/content/
  - Streams Groq tokens (SSE) for content generation
  - Body: { prompt: string, userId: string }
  - Returns: SSE stream of tokens
  - Optional (Phase 10.1): when enforcement enabled, a final SSE event `event: enforcement`
    includes `{ request_id, mode, receipt, decisions, qa_summary, would_block, required_edits, audit_ok }`.
  - `qa_summary.status` is canonicalized as `PASS` or `FAIL`.
  - Non-streaming responses include optional `enforcement` field with the same shape.

**Client Responsibilities (Phase 10.1):**
- If `enforcement.mode` is not `off`, persist `enforcement.request_id` and `enforcement.receipt.receipt_id`.
- When posting, include `enforcement_request_id` and/or `enforcement_receipt_id` in the request body.
- Receipts expire after `ONERING_ENFORCEMENT_RECEIPT_TTL_SECONDS` (default 3600s); regenerate on expiry.

### Enforcement Metadata (Phase 10.1)

Optional metadata may be attached to generation responses (non-breaking). In advisory mode, content is never blocked; metadata provides visibility.

- `enforcement` object (optional, advisory/enforced modes only):
  ```json
  {
    "status": "off|advisory|enforced",
    "workflowId": "uuid",
    "policyVersion": "2025-12-25",
    "checks": ["profanity", "tos_compliance", "length"],
    "warnings": ["tweet length near 280 chars"]
  }
  ```

Backward compatibility guarantees:
- Field is optional; omission means enforcement disabled.
- Existing streaming token contract remains unchanged; metadata may be sent as initial JSON envelope or terminal summary event (implementation detail).

### Phase 10.1 Enforcement (Canonical)

- **Flags (canonical names + defaults):**
  - `ONERING_ENFORCEMENT_MODE`: `off` (default) | `advisory` | `enforced`
  - `ONERING_AUDIT_LOG`: `"1"` (default enabled; `"0"` disables writes)
  - `ONERING_TOKEN_ISSUANCE`: `off` (default) | `shadow` | `live` (shadow only in 10.1)
- **Mode effects:**
  - `off`: Generation/posting unchanged; no enforcement payloads emitted; posting does not require receipts.
  - `advisory`: Generation emits SSE `event: enforcement` and non-streaming `enforcement` payload; `would_block` is informational only; posting accepts/ignores payload.
  - `enforced`: Generation emits enforcement payload; posting MUST validate server-side QA receipt (request_id + decision/workflow IDs) and may block on QA/Audit failure.
- **Generation SSE canonical payload (`event: enforcement`):**
  - Required fields: `request_id` (string|null), `mode` ("off"|"advisory"|"enforced"), `decisions` (array), `qa_summary` (object), `would_block` (bool), `required_edits` (array), `audit_ok` (bool)
  - Optional fields: `warnings` (array of strings)
  - Decision entry: `{ agent_name: string, status: "PASS"|"FAIL", violation_codes: string[], required_edits: string[], decision_id: string }`
  - QA summary: `{ status: "PASS"|"FAIL", violation_codes: string[], risk_score: number }`
  - **Status casing:** canonical `PASS` / `FAIL` (uppercase) everywhere (decisions + qa_summary) for clients.
- **Canonical QA violation codes (Phase 10.1):**
  - `PROFANITY`: Content contains banned terms (word-boundary matched)
  - `HARMFUL_CONTENT`: Self-harm or abusive language patterns
  - `TOS_VIOLATION`: Platform-specific terms of service violations (e.g., impersonation, explicit content)
  - `LENGTH_EXCEEDED`: Content exceeds platform character limits per line/post
  - `NUMBERING_NOT_ALLOWED`: Leading numbering or bullets (e.g., "1/5", "Tweet 1:")
  - `POLICY_TAGS_MISSING`: Required policy_tags field is empty
  - `CITATIONS_REQUIRED`: Citations required but not provided
- **Canonical enforcement error taxonomy (response error shape):**
  ```json
  {
    "error": {
      "code": "QA_BLOCKED",
      "message": "QA rejected content",
      "suggestedFix": "Resolve required edits and regenerate",
      "details": {"violation_codes": ["NUMBERING_NOT_ALLOWED"], "required_edits": ["Remove numbering"], "request_id": "..."}
    }
  }
  ```
  - Codes: `QA_BLOCKED`, `ENFORCEMENT_RECEIPT_REQUIRED`, `AUDIT_WRITE_FAILED`, `POLICY_ERROR`, `ENFORCEMENT_DISABLED`, `RATE_LIMITED`, `CIRCUIT_BREAKER_TRIPPED`.
- **SSE example (advisory):**
  ```
  event: enforcement
  data: {"request_id":"req-123","mode":"advisory","decisions":[{"agent_name":"QA","status":"PASS","violation_codes":[],"required_edits":[],"decision_id":"hash123"}],"qa_summary":{"status":"PASS","violation_codes":[],"risk_score":0.1},"would_block":false,"required_edits":[],"audit_ok":true,"warnings":[]}
  ```
- **Posting failure example (enforced):**
  ```json
  {
    "success": false,
    "error": "QA blocked publishing",
    "code": "QA_BLOCKED",
    "suggestedFix": "Resolve required edits and regenerate content through the enforcement pipeline.",
    "details": {
      "required_edits": ["Remove numbering", "Shorten line 1"],
      "violation_codes": ["NUMBERING_NOT_ALLOWED"],
      "request_id": "req-123"
    }
  }
  ```
- **Backward compatibility guarantees:**
  - `off` mode behavior is unchanged (no enforcement payloads required or emitted).
  - All new fields are optional; clients may ignore them safely in `off`/`advisory` modes.
  - `enforced` mode requires a valid QA receipt (request_id + QA PASS + audit_ok=true) for posting; failures use the canonical error taxonomy.

### Enforcement Failure Error Shape

In enforced mode, failures include actionable `suggestedFix`.

Example:
```json
{
  "error": {
    "code": "QA_REJECTED",
    "message": "Content contains banned terms",
    "suggestedFix": "Remove profanity and re-generate. See brand safety policy.",
    "details": {
      "banned": ["fuck", "shit"],
      "check": "profanity"
    }
  }
}
```

Additional examples:
- `HARMFUL_CONTENT`: "Detected self-harm phrasing" → suggestedFix: "Refocus on growth/resilience; use provided redirection topic."
- `CIRCUIT_BREAKER_TRIPPED`: "Optimizer failed 3x" → suggestedFix: "Proceed with writer draft; retry later."

Notes:
- Error shape is additive; does not alter HTTP status conventions.
- `suggestedFix` follows existing patterns (see X 403 credential guidance).

## Payments

- POST /api/stripe/checkout
  - Creates Stripe Checkout Session
  - Returns: { sessionUrl }

- POST /api/stripe/webhook (public)
  - Verifies signature and updates user metadata
  - On success: set verified=true, award RING

## Posting

- POST /api/post-to-x
  - Posts a thread to X (Twitter)
  - Splits on newlines; chains replies; rate-limited 5 per 15m
  - Returns: { urls: string[] }
  - Optional (Phase 10.2): on success includes `token_result`
    ```json
    {
      "token_result": {
        "mode": "shadow|live|off",
        "issued_amount": 0,
        "pending_amount": 10,
        "reason_code": "PENDING",
        "guardrails_applied": []
      }
    }
    ```
  - Optional (Phase 10.1): accepts `enforcement` payload from generation; enforced mode
    blocks publishing unless a valid QA receipt is provided.
  - Enforced mode requires one of:
    - `enforcement_request_id` (request_id returned in enforcement metadata)
    - `enforcement_receipt_id` (receipt.receipt_id returned in enforcement metadata)
  - Receipt expiry: receipts expire after `ONERING_ENFORCEMENT_RECEIPT_TTL_SECONDS` (default 3600s)

## Enforcement (internal)

- POST /v1/enforcement/receipts/validate
  - Body: { request_id?: string, receipt_id?: string }
  - Returns: { ok: true, receipt } or { ok: false, code, message }
  - Error codes:
    - `ENFORCEMENT_RECEIPT_REQUIRED`
    - `ENFORCEMENT_RECEIPT_INVALID`
    - `ENFORCEMENT_RECEIPT_EXPIRED`
    - `AUDIT_WRITE_FAILED`

## Tokens (Phase 10.2)

- POST /v1/tokens/publish
  - Persist publish event and issue tokens if eligible.
  - Body: { event_id, user_id, platform, content_hash, published_at?, platform_post_id?, enforcement_request_id?, enforcement_receipt_id?, metadata? }
  - Returns: { ok: true, event_id, token_result }

- POST /v1/tokens/spend
  - Ledger-backed spend (shadow/live only).
  - Body: { user_id, amount, reason_code, idempotency_key?, metadata? }
  - Returns: { ok: true, mode, ledger_id, balance_after, idempotent }

- POST /v1/tokens/earn
  - Ledger-backed earn (shadow/live only).
  - Body: { user_id, amount, reason_code, idempotency_key?, metadata? }
  - Returns: { ok: true, mode, ledger_id?, pending_id?, balance_after?, idempotent }

- GET /v1/tokens/summary/{user_id}
  - Canonical balance summary (ledger-first).
  - Query: limit (default 20) for recent ledger/publish lists.
  - Returns: { userId, mode, balance, pending_total, effective_balance, last_ledger_at, last_pending_at, guardrails_state, clerk_sync, ledger_entries, publish_events, reconciliation_status }
  - Use this for UI balances whenever ONERING_TOKEN_ISSUANCE=shadow|live.

Error codes:
- `LEGACY_RING_WRITE_BLOCKED`: legacy balance mutation attempted while token issuance is shadow/live.

## Monitoring (internal)

- GET /v1/monitoring/enforcement/recent
  - Query: `limit` (default 50, max 200), `since` (ISO8601)
  - Returns: { items: [{ request_id, receipt_id, mode, qa_status, violation_codes_count, audit_ok, created_at, expires_at, latency_ms, last_error_code, last_error_at }] }
- GET /v1/monitoring/enforcement/metrics
  - Returns: { window_hours: 24, metrics: { qa_blocked, enforcement_receipt_required, enforcement_receipt_expired, audit_write_failed, policy_error, p90_latency_ms } }

- GET /v1/monitoring/tokens/recent
  - Query: `limit` (default 50, max 200), `since` (ISO8601)
  - Returns: { items: [{ event_id, user_id, platform, enforcement_request_id, enforcement_receipt_id, token_issued_amount, token_pending_amount, token_reason_code, token_ledger_id, token_pending_id, created_at, last_clerk_sync_at, last_clerk_sync_error }] }
- GET /v1/monitoring/tokens/metrics
  - Returns: { window_hours: 24, metrics: { total_issued, total_pending, blocked_issuance, top_reason_codes, p90_issuance_latency_ms, reconciliation_mismatches, clerk_sync_failures_24h, idempotency_conflicts_24h } }

## Audit Retention (ops)

- Env vars:
  - `ONERING_AUDIT_RETENTION_DAYS` (default 30)
  - `ONERING_AUDIT_CLEANUP_DRY_RUN` (default "1")
- Cleanup job: `python -m backend.workers.cleanup_enforcement`

Notes:
- All time-based endpoints accept optional `now` for deterministic tests.
- See .ai/TESTING.md for examples.

### Backward Compatibility (Phase 10.1)

- Enforcement metadata is optional and non-breaking.
- Failure error shape adds fields under `error` without changing existing keys.
- Advisory rollout ensures content flow unaffected while instrumentation is verified.
