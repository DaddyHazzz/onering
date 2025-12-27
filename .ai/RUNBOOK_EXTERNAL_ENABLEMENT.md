# OneRing Phase 10.3 — Enablement Launch Pack

**Status:** Production-ready for controlled rollout  
**Last Updated:** Dec 27, 2025  
**Maintainer:** Principal Engineer / TPM

---

## 🎯 Quick Start

### Prerequisites
- PostgreSQL with pgvector extension
- Redis for rate limiting
- Backend running: `uvicorn backend.main:app --reload --port 8000`
- Webhook delivery worker running: `python -m backend.workers.webhook_delivery --loop`

### Canary Launch (Safest Path)
1. **Enable canary-only mode:**
   ```bash
   export ONERING_EXTERNAL_API_ENABLED=1
   export ONERING_EXTERNAL_API_CANARY_ONLY=1  # Only canary keys allowed
   export ONERING_WEBHOOKS_ENABLED=1
   export ONERING_WEBHOOKS_DELIVERY_ENABLED=1
   ```

2. **Create canary test key:**
   ```bash
   # Use admin endpoint to create key with canary_enabled=true
   curl -X POST http://localhost:8000/v1/admin/external/keys \
     -H "Authorization: Bearer <admin_key>" \
     -H "Content-Type: application/json" \
     -d '{"tier": "pro", "scopes": ["read:rings"], "canary_enabled": true}'
   ```

3. **Run smoke tests:**
   ```bash
   # Terminal 1: Start webhook sink
   python tools/webhook_sink.py --port 9090 --secret whsec_smoke

   # Terminal 2: Run end-to-end smoke test
   python backend/scripts/external_smoke.py \
     --backend-url http://localhost:8000 \
     --admin-key <admin_key> \
     --webhook-sink http://localhost:9090/webhook
   ```

4. **Monitor metrics:**
   ```bash
   # Check real-time metrics
   curl http://localhost:8000/v1/monitoring/external/metrics
   curl http://localhost:8000/v1/monitoring/webhooks/metrics
   ```

### Full Production Rollout
```bash
export ONERING_EXTERNAL_API_ENABLED=1
export ONERING_EXTERNAL_API_CANARY_ONLY=0  # Allow all keys
export ONERING_WEBHOOKS_ENABLED=1
export ONERING_WEBHOOKS_DELIVERY_ENABLED=1
```

---

## 🔧 Environment Variables

### Kill Switches
```
ONERING_EXTERNAL_API_ENABLED=0|1          # External API enable/disable
ONERING_EXTERNAL_API_CANARY_ONLY=0|1      # Force canary-only mode
ONERING_WEBHOOKS_ENABLED=0|1              # Webhook creation/management
ONERING_WEBHOOKS_DELIVERY_ENABLED=0|1     # Delivery worker active
```

### Webhook Configuration
```
ONERING_WEBHOOKS_MAX_ATTEMPTS=3           # Max retry attempts
ONERING_WEBHOOKS_BACKOFF_SECONDS="60,300,900"   # Retry intervals (sec)
ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS=300     # Replay protection tolerance
ONERING_WEBHOOKS_DELIVERY_LOOP_SECONDS=5       # Worker poll interval
```

### Monitoring & Alerts
```
ONERING_ALERT_DEAD_LETTER_24H=10          # Dead-letter threshold
ONERING_ALERT_AUTH_FAILURES_24H=50        # Auth failure threshold
ONERING_ALERT_RATE_LIMIT_HITS_24H=100     # Rate limit hits threshold
ONERING_ALERT_REPLAY_REJECTED_24H=20      # Replay rejection threshold
ONERING_ALERT_LATENCY_P90_SECONDS=5.0     # Latency p90 threshold
```

---

## 📋 Pre-Launch Checklist

### Database
- [ ] Run migrations: `npx prisma migrate deploy`
- [ ] Verify `external_api_keys.canary_enabled` column exists
- [ ] Verify `webhook_deliveries` table has all columns (status, attempt_count, etc.)

### Backend Services
- [ ] FastAPI running: `uvicorn backend.main:app --port 8000`
- [ ] RQ worker running: `rq worker -u redis://localhost:6379 default`
- [ ] Webhook delivery worker: `python -m backend.workers.webhook_delivery --loop`

### Tests
- [ ] `pnpm gate --mode full` passes (zero skipped, zero failed)
- [ ] Backend pytest: `pytest backend/tests/ -v`
- [ ] Frontend vitest: `pnpm test`

### Documentation
- [ ] Ops runbook reviewed (this file)
- [ ] Alert thresholds configured for monitoring
- [ ] Incident playbook available
- [ ] Smoke test script verified

---

## 🚀 Enablement Steps (Controlled Rollout)

### Stage 1: External API Only (24 hours)
```bash
export ONERING_EXTERNAL_API_ENABLED=1
export ONERING_EXTERNAL_API_CANARY_ONLY=0  # Or 1 if starting conservative
export ONERING_WEBHOOKS_ENABLED=0
export ONERING_WEBHOOKS_DELIVERY_ENABLED=0
```

**Validate:**
- Create test API key
- Call `/v1/external/me` and verify rate limit headers
- Monitor `/v1/monitoring/external/metrics` for auth failures, rate limits
- Check logs for any errors

### Stage 2: Webhooks (24 hours)
```bash
export ONERING_WEBHOOKS_ENABLED=1
export ONERING_WEBHOOKS_DELIVERY_ENABLED=0  # Prepare worker, don't start yet
```

**Validate:**
- Create webhook subscription
- Query `/v1/monitoring/webhooks/metrics` (should show 0 deliveries)
- Verify webhook_deliveries table logs events

### Stage 3: Webhook Delivery (Continuous)
```bash
export ONERING_WEBHOOKS_DELIVERY_ENABLED=1
# Start delivery worker in production environment
```

**Validate:**
- Run smoke test (see Quick Start above)
- Monitor /metrics: should see DELIVERED, RETRYING, or DEAD statuses
- Check delivery latency: `/v1/monitoring/webhooks/metrics`
- Monitor dead-letter queue: alert if > threshold

### Stage 4: Full Production
All flags enabled. Monitor continuously.

---

## 🎚️ Canary Mode Specifics

### What is Canary Mode?
- Per-key flag: `canary_enabled`
- Canary keys get reduced rate limits: **10 requests/hour** (vs. tier limit)
- Extra logging for canary requests
- Can enforce canary-only mode with `ONERING_EXTERNAL_API_CANARY_ONLY=1`

### Create Canary Key
```bash
curl -X POST http://localhost:8000/v1/admin/external/keys \
  -H "Authorization: Bearer <admin_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "pro",
    "scopes": ["read:rings", "read:drafts"],
    "canary_enabled": true
  }'
```

Response includes secret (only shown once). Store securely.

### Test Canary Key
```bash
curl http://localhost:8000/v1/external/me \
  -H "Authorization: Bearer osk_<canary_secret>"
# Response headers show: X-Canary-Mode: true, X-RateLimit-Limit: 10
```

### Canary-Only Mode (Emergency)
If attack or bug detected:
```bash
export ONERING_EXTERNAL_API_CANARY_ONLY=1
# Reject all non-canary keys with 403 CANARY_ONLY_MODE
# Canary keys continue working with reduced limits
```

To disable:
```bash
unset ONERING_EXTERNAL_API_CANARY_ONLY
# Or restart with =0
```

---

## 🔄 Webhook Delivery Mechanics

### Signing & Verification
Every webhook includes HMAC-SHA256 signature:

**Headers:**
- `X-Webhook-Signature: t=<timestamp>,e=<event_id>,v1=<hex_digest>`
- `X-Webhook-Timestamp: <unix_timestamp>`
- `X-Webhook-Event-ID: <event_id>`

**Consumer verification:**
```python
import hmac, hashlib

# Construct signed content
timestamp = int(request.headers['X-Webhook-Timestamp'])
event_id = request.headers['X-Webhook-Event-ID']
body = await request.body()

signed = f"{timestamp}.{event_id}.".encode() + body
expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()

# Extract and compare
provided_sig = request.headers['X-Webhook-Signature'].split('v1=')[1]
assert hmac.compare_digest(provided_sig, expected)
```

### Retry Logic
1. **Attempt 1:** Immediately (0s)
2. **Attempt 2:** After 60s (1min)
3. **Attempt 3:** After 300s (5min)
4. **Dead-letter:** After 900s (15min), marked as DEAD

### Replay Protection
- Enforces 300-second tolerance (configurable)
- Rejects webhooks with timestamp >300s in past
- Status: REPLAY_EXPIRED

---

## 🚨 Incident Playbook

### Symptom: High Dead-Letter Rate

**Diagnosis:**
```bash
# Check metrics
curl http://localhost:8000/v1/monitoring/webhooks/metrics

# List recent dead deliveries
curl http://localhost:8000/v1/monitoring/webhooks/recent?status=DEAD
```

**Possible Causes:**
1. **Consumer endpoint down** — verify target URL is reachable
2. **Consumer returning 5xx** — check consumer logs
3. **Signature validation failing** — verify consumer secret matches
4. **Payload too large** — reduce event size
5. **Consumer slow (timeouts)** — increase webhook timeout or optimize endpoint

**Recovery:**
1. Fix consumer endpoint
2. Rotate webhook secret if compromised
3. Re-trigger events via `/v1/external/events` if critical

### Symptom: High Rate-Limit Hits

**Diagnosis:**
```bash
curl http://localhost:8000/v1/monitoring/external/metrics
```

**Possible Causes:**
1. **Consumer key stuck in loop** — disable key temporarily
2. **DDoS attack** — use canary-only mode, block IP
3. **Legitimate spike** — increase rate limit tier for key

**Recovery:**
```bash
# Disable key via admin endpoint
curl -X PATCH http://localhost:8000/v1/admin/external/keys/<key_id>/disable \
  -H "Authorization: Bearer <admin_key>"

# Re-enable after fix
curl -X PATCH http://localhost:8000/v1/admin/external/keys/<key_id>/enable
```

### Symptom: Webhook Replay Rejections Spiking

**Diagnosis:**
```bash
curl http://localhost:8000/v1/monitoring/webhooks/metrics  # Check replay_rejected_24h
```

**Possible Causes:**
1. **Clock skew** — sync server time with NTP
2. **Delivery worker delayed** — check worker logs, increase poll frequency
3. **Replay window too small** — adjust `ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS`

**Recovery:**
- If network partition caused queueing: increase replay window temporarily
- Restart delivery worker to resume processing

### Emergency: Kill Switch

**Disable everything:**
```bash
export ONERING_EXTERNAL_API_ENABLED=0
export ONERING_WEBHOOKS_ENABLED=0
export ONERING_WEBHOOKS_DELIVERY_ENABLED=0
# Restart services
```

**Re-enable carefully:**
1. Enable External API: `ONERING_EXTERNAL_API_ENABLED=1`
2. Monitor 10 minutes: check `/v1/monitoring/external/metrics`
3. Enable Webhooks: `ONERING_WEBHOOKS_ENABLED=1`
4. Monitor 10 minutes
5. Enable Delivery: `ONERING_WEBHOOKS_DELIVERY_ENABLED=1`
6. Monitor metrics and dead-letter queue

---

## 📊 Monitoring Dashboard

**Key Metrics:**
```
External API:
  - active_keys: # of active keys
  - auth_failures_24h: # failed auth attempts
  - rate_limit_hits_24h: # 429 responses
  - key_metrics_by_tier: breakdown by free/pro/enterprise

Webhooks:
  - delivered: # successful deliveries
  - failed: # failed (will retry)
  - dead: # dead-lettered
  - pending: # queued
  - retrying: # in retry state
  - replay_rejected_24h: # rejected by replay protection
  - avg_retry_count: avg attempts per delivery
  - delivery_latency_p90_sec: p90 latency
```

**Alerts:**
Check `/v1/monitoring/webhooks/metrics` response for `alerts` section. Alert if:
- `dead_letter_exceeded` = true
- `replay_rejected_exceeded` = true
- `latency_p90_exceeded` = true

---

## 🛠️ Troubleshooting

### Webhook Not Delivered
1. Check delivery worker running: `ps aux | grep webhook_delivery`
2. Check worker logs for errors
3. Verify webhook subscription exists and is active
4. Call smoke test (see Quick Start)

### Can't Create API Key
1. Verify admin key has `external:admin` scope
2. Check database: `SELECT COUNT(*) FROM external_api_keys;`
3. Verify migrations ran: `SELECT * FROM schema_migrations;`

### Signature Verification Fails
1. Verify consumer using same secret as webhook
2. Check timestamp tolerance (default 300s)
3. Verify consumer receiving raw request body (not parsed/re-encoded)

### Rate Limits Too Restrictive
1. Check key tier: `SELECT rate_limit_tier FROM external_api_keys WHERE key_id = ...;`
2. Check if in canary mode: `SELECT canary_enabled ...;`
3. Upgrade tier via admin endpoint to increase limit

---

## 📚 Related Docs

- [API_REFERENCE.md](.ai/API_REFERENCE.md) — Complete endpoint specs
- [PHASE_10_3_EXTERNAL_PLATFORM.md](.ai/PHASE_10_3_EXTERNAL_PLATFORM.md) — Design details
- [RUNBOOK_WEBHOOKS.md](./RUNBOOK_WEBHOOKS.md) — Webhook-specific runbook

---

## ✅ Sign-Off

- [ ] Enablement reviewed by TPM
- [ ] Rollout plan agreed with Ops
- [ ] Monitoring alerts configured
- [ ] On-call rotation established
- [ ] Incident playbook distributed

**Owner:** Principal Engineer  
**Escalation:** TPM / SRE Lead
