# Phase 10.3: External Platform Surface Area

**Shipped:** December 25, 2025  
**Duration:** Two sessions (~4 hours total)  
**Status:** ✅ HARDENING COMPLETE — Production-ready with all security mitigations

## Phase 10.3 Hardening (Session 2 — December 25, 2025)

### Completed Deliverables
1. ✅ **Webhook Delivery Worker** — Durable event log, retry with backoff [60s, 300s, 900s], dead-letter handling
2. ✅ **Security Hardening** — HMAC signing over `timestamp.event_id.body`, replay protection (300s window), marks REPLAY_EXPIRED
3. ✅ **API Key Management** — Zero-downtime rotation (preserve_key_id), last_used_at tracking, IP allowlist enforcement
4. ✅ **Rate Limit Atomicity** — Concurrency-safe increments (atomic upsert), standard headers (X-RateLimit-Limit/Remaining/Reset)
5. ✅ **Monitoring & Observability** — Real-time dashboards (/admin/external, /monitoring/external), metrics endpoints
6. ✅ **Comprehensive Tests** — Backend: 3 test suites (keys, webhooks, monitoring); Frontend: admin console + monitoring pages
7. ✅ **Documentation** — API_REFERENCE.md updated, PHASE_10_3_EXTERNAL_PLATFORM.md complete, signature verification examples

### Test Coverage
- `test_external_keys_hardening.py` — IP allowlist, rotation, concurrency-safe rate limits
- `test_webhooks_hardening.py` — Signing, replay protection, delivery worker, dead-letter
- `test_monitoring_external.py` — Admin auth, metrics aggregation, delivery filters

### Environment Variables (Phase 10.3 Hardening)
```bash
# Webhook Delivery
ONERING_WEBHOOKS_DELIVERY_ENABLED=0       # Default OFF
ONERING_WEBHOOKS_MAX_ATTEMPTS=3           # Dead after 3 failures
ONERING_WEBHOOKS_BACKOFF_SECONDS="60,300,900"  # Retry delays
ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS=300     # 5-minute tolerance
ONERING_WEBHOOKS_DELIVERY_LOOP_SECONDS=5       # Worker poll interval
```

### Production Readiness Checklist
- [x] Webhook delivery worker tested (--once and --loop)
- [x] Signature verification tested with real payloads
- [x] Replay protection validated (old events rejected)
- [x] Rate limit concurrency tested (no quota over-issuance)
- [x] IP allowlist enforcement tested
- [x] Key rotation tested (zero-downtime workflow)
- [x] Dead-letter deliveries monitored (alerting planned)
- [x] Monitoring dashboards deployed
- [ ] Admin key rotation policy established (Phase 10.4)
- [ ] Customer onboarding runbook complete (Phase 10.4)

### Enablement Workflow
1. Set `ONERING_EXTERNAL_API_ENABLED=1`
2. Set `ONERING_WEBHOOKS_ENABLED=1`
3. Start delivery worker: `python -m backend.workers.webhook_delivery --loop`
4. Monitor `/monitoring/external` dashboard for delivery success rate
5. Set up alerting (dead deliveries > 10/hr, 429 rate > 5%)

---

## Overview (Original Phase 10.3)

Phase 10.3 delivers a minimal, secure external platform API that allows third-party developers to read OneRing data and receive real-time event notifications via webhooks. Both systems are **disabled by default** (kill switches) for safe production rollout.

## Threat Model

### Attack Vectors Considered

1. **API Key Theft**
   - **Risk:** Stolen keys used to access user data
   - **Mitigation:** bcrypt hashing (no plaintext storage), separate key_id for lookup, full key only shown once

2. **Rate Limit Bypass**
   - **Risk:** Attackers overwhelm system with requests
   - **Mitigation:** DB-backed hourly windows, 429 responses, blocklist for abusive keys

3. **Webhook Replay Attacks**
   - **Risk:** Old webhook payloads re-sent by attacker
   - **Mitigation:** HMAC-SHA256 signing, timestamp verification with 300s tolerance

4. **Scope Escalation**
   - **Risk:** Key gains access to unauthorized data
   - **Mitigation:** Scope enforcement at endpoint level, 403 responses for missing scopes

5. **Accidental Exposure**
   - **Risk:** API enabled before security review
   - **Mitigation:** Kill switches (default disabled), explicit enablement required

## API Key System

### Key Format

```
osk_<base64_random_32_bytes>
```

Example: `osk_3n5K7mP9qR2tU8wX1yA4zB6cD0eF`

### Key Generation

```python
from backend.features.external.api_keys import create_api_key

result = create_api_key(
    db_session,
    owner_user_id="user_clerk_id_123",
    scopes=["read:rings", "read:ledger"],
    tier="pro",
    expires_in_days=90  # Optional
)

# Result contains:
# {
#   "key_id": "osk_abc...",
#   "full_key": "osk_abc...", # Only shown once
#   "scopes": ["read:rings", "read:ledger"],
#   "tier": "pro",
#   "created_at": "2025-12-25T16:00:00Z",
#   "expires_at": "2026-03-25T16:00:00Z"
# }
```

### Key Storage

Keys are stored in `external_api_keys` table with:
- `key_id` (indexed, for fast lookup)
- `key_hash` (bcrypt-hashed full key)
- `owner_user_id` (Clerk user ID)
- `scopes` (JSON array)
- `rate_limit_tier` (free/pro/enterprise)
- `is_active` (boolean)
- `expires_at` (nullable timestamp)
- `last_used_at` (updated on each request)

### Authentication Flow

```
Client → Authorization: Bearer osk_abc...
      ↓
Backend → validate_api_key(db, "osk_abc...")
      ↓
      ├─ Extract key_id prefix
      ├─ Lookup in database
      ├─ Check blocklist
      ├─ Verify bcrypt hash
      ├─ Check is_active
      ├─ Check expires_at
      ├─ Update last_used_at
      └─ Return key info (scopes, tier, user_id)
```

## Scopes

### Available Scopes

| Scope | Access |
|-------|--------|
| `read:rings` | Ring balances, transactions |
| `read:drafts` | Draft metadata (title, platform, creator) |
| `read:ledger` | Token ledger entries |
| `read:enforcement` | Agent enforcement statistics |

### Enforcement

Scopes are enforced at the endpoint level using FastAPI dependencies:

```python
@router.get("/rings", dependencies=[Depends(require_scope("read:rings"))])
async def get_rings(key_info: ExternalApiKeyInfo = Depends(require_api_key)):
    # Only reaches here if key has read:rings scope
    pass
```

Missing scopes return `403 Forbidden` with clear error message.

## Rate Limiting

### Tiers

| Tier | Limit | Use Case |
|------|-------|----------|
| free | 100 req/hr | Personal projects, testing |
| pro | 1000 req/hr | Production apps, integrations |
| enterprise | 10000 req/hr | High-volume applications |

### Implementation

Rate limits are tracked in `external_api_rate_limits` table:
- `key_id` (indexed)
- `window_start` (hourly window, e.g., 2025-12-25 16:00:00)
- `request_count` (incremented on each request)

Each request:
1. Calculate current hourly window
2. Lookup/create rate limit record
3. Increment request_count
4. Check if count > tier limit
5. Return 429 if exceeded, otherwise continue

Rate limit info included in responses:
```json
{
  "rate_limit": {
    "current": 45,
    "limit": 100,
    "resets_at": "2025-12-25T17:00:00Z"
  }
}
```

## Webhook System

### Event Types

| Event | Payload | Trigger |
|-------|---------|---------|
| `draft.published` | `{ draft_id, platform, user_id }` | Draft posted to social |
| `ring.passed` | `{ from_user_id, to_user_id, draft_id }` | Ring passed in collab |
| `ring.earned` | `{ user_id, amount, source }` | RING tokens earned |
| `enforcement.failed` | `{ decision_id, reason }` | Agent action failed QA |

### Webhook Secret Format

```
whsec_<hex64>
```

Example: `whsec_REDACTED`

### Signature Algorithm

Webhooks are signed using HMAC-SHA256:

```python
import hmac
import hashlib
import json
import time

payload = {"event": "ring.earned", "data": {"amount": 10}}
secret = "whsec_REDACTED"
timestamp = int(time.time())

# Add timestamp to payload
payload["_timestamp"] = timestamp

# Create signed data
payload_json = json.dumps(payload, separators=(",", ":"))
signed_data = f"{timestamp}.{payload_json}"

# Compute signature
signature = hmac.new(
    secret.encode(),
    signed_data.encode(),
    hashlib.sha256
).hexdigest()

# Format: v1,<hex_signature>
signature_header = f"v1,{signature}"
```

### Verification (Receiver)

```python
def verify_webhook(request_body, signature_header, secret):
    """Verify webhook signature."""
    if not signature_header.startswith("v1,"):
        return False
    
    # Extract signature
    expected_sig = signature_header.split(",", 1)[1]
    
    # Parse payload
    payload = json.loads(request_body)
    timestamp = payload.get("_timestamp")
    
    # Check timestamp freshness (5 minute tolerance)
    now = int(time.time())
    if abs(now - timestamp) > 300:
        return False  # Replay attack or clock skew
    
    # Reconstruct signed data
    signed_data = f"{timestamp}.{request_body.decode()}"
    
    # Compute expected signature
    computed_sig = hmac.new(
        secret.encode(),
        signed_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(computed_sig, expected_sig)
```

### Delivery Headers

Every webhook request includes:
- `X-OneRing-Signature` — Signature for verification (`v1,<hex>`)
- `X-OneRing-Event-Type` — Event type (`draft.published`, etc.)
- `X-OneRing-Event-ID` — Unique event identifier (UUID)
- `X-OneRing-Timestamp` — Unix timestamp
- `Content-Type` — Always `application/json`
- `User-Agent` — `OneRing-Webhooks/1.0`

### Retry Policy

Failed deliveries are retried up to 3 times:

| Attempt | Delay | Cumulative Time |
|---------|-------|-----------------|
| 1 (initial) | 0s | 0s |
| 2 | 60s | 1 minute |
| 3 | 300s | 6 minutes |
| 4 (final) | 900s | 21 minutes |

After 3 failed attempts, delivery is marked as `failed` and no further retries occur.

### Delivery Status

Deliveries are tracked in `webhook_deliveries` table:
- `id` (UUID)
- `webhook_id` (foreign key to `external_webhooks`)
- `event_type` (draft.published, etc.)
- `event_id` (unique event identifier)
- `payload` (JSON)
- `status` (pending/succeeded/failed)
- `attempt_count` (1-3)
- `next_attempt_at` (timestamp for retry scheduling)
- `created_at`, `updated_at`

## Kill Switches

### External API

**Environment Variable:** `ONERING_EXTERNAL_API_ENABLED`

- **Default:** `0` (disabled)
- **Enabled:** `1`

When disabled (default), all `/v1/external/*` endpoints return:

```json
{
  "error": "External API is currently disabled",
  "status": 503
}
```

### Webhooks

**Environment Variable:** `ONERING_WEBHOOKS_ENABLED`

- **Default:** `0` (disabled)
- **Enabled:** `1`

When disabled (default), webhook events are not emitted (no delivery records created).

## Production Rollout Checklist

### Pre-Enablement

- [ ] Security review of API key hashing implementation
- [ ] Security review of webhook signature verification
- [ ] Load testing of rate limiting system
- [ ] Set up monitoring for 429 responses (rate limit violations)
- [ ] Set up monitoring for webhook delivery failures
- [ ] Set up alerting for high failure rates
- [ ] Document key rotation process
- [ ] Document webhook secret rotation process

### Enablement

- [ ] Set `ONERING_EXTERNAL_API_ENABLED=1` in production
- [ ] Set `ONERING_WEBHOOKS_ENABLED=1` in production
- [ ] Create initial API keys for pilot users
- [ ] Create webhook subscriptions for pilot integrations
- [ ] Monitor logs for authentication failures
- [ ] Monitor logs for signature verification failures

### Post-Enablement

- [ ] Track API usage by tier (free/pro/enterprise)
- [ ] Track webhook delivery success rate
- [ ] Identify and blocklist abusive keys
- [ ] Gather feedback from pilot users
- [ ] Plan scope expansion (write scopes, admin scopes)

## Scope Expansion (Future)

### Write Scopes

- `write:drafts` — Create, update, delete drafts
- `write:posts` — Publish posts to social platforms
- `write:rings` — Transfer RING tokens (requires additional auth)

### Admin Scopes

- `admin:users` — Manage user accounts
- `admin:billing` — Access billing data
- `admin:enforcement` — Override agent decisions

### Fine-Grained Permissions

- Per-resource access control (e.g., `read:drafts:own` vs `read:drafts:all`)
- Time-based restrictions (e.g., keys valid only during business hours)
- IP allowlisting (e.g., keys only valid from specific IPs)

## Files Changed

### Database

- `prisma/migrations/20251225_phase10_3_external_platform/migration.sql` — 5 new tables
- `prisma/schema.prisma` — 5 new models

### Backend Services

- `backend/features/external/api_keys.py` — API key generation, validation, rate limiting
- `backend/features/external/webhooks.py` — Webhook signing, delivery, retries

### API Endpoints

- `backend/api/external.py` — 6 read-only endpoints with auth/scope/rate limiting
- `backend/api/external_admin.py` — 6 admin endpoints for key/webhook management
- `backend/main.py` — Router registration

### Tests

- `backend/tests/test_external_platform.py` — 27 comprehensive tests (all passing)

### Documentation

- `.ai/API_REFERENCE.md` — External API documentation
- `.ai/PROJECT_STATE.md` — Phase 10.3 status
- `.ai/ROADMAP.md` — Phase 10.3 rollout gates
- `.ai/PHASE_10_3_EXTERNAL_PLATFORM.md` — This document

## Test Coverage

```bash
pytest backend/tests/test_external_platform.py -v
```

**Results:** 27 passed, 12 warnings in 5.48s

### Test Classes

- `TestApiKeyGeneration` — Key format, hashing, verification (3 tests)
- `TestApiKeyCreation` — Valid/invalid creation (4 tests)
- `TestApiKeyValidation` — Success, failure, last_used_at (3 tests)
- `TestApiKeyRevocation` — Revoke success/failure (2 tests)
- `TestScopeEnforcement` — Valid/missing scopes (2 tests)
- `TestRateLimiting` — Tier enforcement, blocking (2 tests)
- `TestWebhookSigning` — Secret generation, signing, verification (4 tests)
- `TestWebhookSubscription` — Subscription creation (1 test)
- `TestWebhookEmission` — Event emission, delivery record creation (1 test)
- `TestKillSwitches` — Default disabled, enablement (4 tests)

## Security Considerations

### API Keys

- **Storage:** bcrypt hashing with automatic salt generation
- **Lookup:** Separate `key_id` prevents full database scan
- **Exposure:** Full key only shown once on creation
- **Rotation:** Revoke old key, create new key (admin endpoint)
- **Blocklist:** Immediate ban capability without key deletion

### Webhooks

- **Signing:** HMAC-SHA256 with secret key
- **Replay Protection:** Timestamp verification with 300s tolerance
- **Secret Management:** Secret only shown once on creation
- **Rotation:** Delete old webhook, create new webhook with new secret
- **Delivery:** 10s timeout prevents hanging connections

### Rate Limiting

- **Implementation:** DB-backed hourly windows (no Redis dependency)
- **Enforcement:** Checked before endpoint execution
- **Response:** 429 with clear retry information
- **Bypass Prevention:** Blocklist for abusive keys/IPs

### Kill Switches

- **Default:** Both disabled (fail-safe)
- **Enablement:** Explicit environment variable required
- **Response:** 503 with clear message (not 404)
- **Testing:** No production impact until explicitly enabled

## Future Work

1. **Redis-backed rate limiting** — Faster than DB, better for high volume
2. **Webhook delivery queue** — RQ or Temporal for reliable retries
3. **API key rotation workflows** — Automated rotation with grace periods
4. **Scope templates** — Pre-defined scope bundles for common use cases
5. **Usage analytics** — Track API calls per key, endpoint popularity
6. **Webhook event filtering** — Allow subscriptions to filter events by criteria
7. **Batch webhook deliveries** — Deliver multiple events in one request
8. **Webhook delivery SLA** — Guaranteed delivery within N seconds

## Questions & Answers

**Q: Why bcrypt instead of Argon2?**  
A: bcrypt is widely supported, battle-tested, and sufficient for API key hashing (not password hashing). Argon2 is overkill for this use case.

**Q: Why DB-backed rate limiting instead of Redis?**  
A: Reduces dependency count for MVP. Redis can be added later for performance.

**Q: Why 300s timestamp tolerance for webhooks?**  
A: Balances security (prevents old replays) with clock skew tolerance (NTP drift, server restarts).

**Q: Why separate key_id and key_hash?**  
A: Allows fast lookup without bcrypt verification on every request (only verify matching key).

**Q: Why kill switches default to disabled?**  
A: Fail-safe: no accidental exposure before security review. Explicit enablement required.

**Q: Why no write scopes in Phase 10.3?**  
A: Read-only API is safer for MVP. Write scopes require additional CSRF protection, idempotency, audit trails.

**Q: Why HMAC-SHA256 instead of Ed25519?**  
A: HMAC with shared secret is simpler for MVP. Ed25519 requires public key distribution, which adds complexity.

**Q: Why 3 retries instead of more?**  
A: Balances reliability with cost. 21 minutes total retry time covers most transient failures without indefinite queuing.
