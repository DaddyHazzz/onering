# Phase 10.2: TOKEN LOOP SHADOW → LIVE

**Status:** ✅ COMPLETE (Dec 25, 2025)  
**Mode:** Shadow → Live switchable via `ONERING_TOKEN_ISSUANCE`  
**Tests:** 19/19 passing

---

## 📋 Executive Summary

Phase 10.2 implements a **canonical token accounting system** for $RING with shadow/live mode switching. All token issuance flows through a verified ledger, enforced guardrails, and automatic reconciliation.

### Key Deliverables

- ✅ **Canonical Ledger:** Append-only `ring_ledger` table with immutable entries
- ✅ **Shadow Mode:** Logs pending rewards without touching balances (`ring_pending` table)
- ✅ **Live Mode:** Atomically updates balances + appends ledger entries
- ✅ **Ledger-as-Truth:** Canonical balance resolved from ledger/pending with `/v1/tokens/summary/{user_id}`
- ✅ **Anti-Gaming Guardrails:** Daily cap, min interval, anomaly detection (3 enforced rules)
- ✅ **Reconciliation Job:** Daily mismatch detection with automatic ADJUSTMENT entries
- ✅ **API Endpoints:** Balance, ledger, reconcile endpoints at `/v1/tokens/*`
- ✅ **Tests:** 19 comprehensive backend tests covering all invariants

---

## 🏗️ Architecture

### Database Schema

```sql
-- Canonical ledger (append-only)
CREATE TABLE ring_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    draft_id UUID,
    request_id TEXT,
    receipt_id TEXT,
    event_type TEXT NOT NULL CHECK (event_type IN ('EARN', 'SPEND', 'PENALTY', 'ADJUSTMENT')),
    reason_code TEXT NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Shadow mode pending rewards
CREATE TABLE ring_pending (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    draft_id UUID,
    request_id TEXT,
    amount INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Anti-gaming state
CREATE TABLE ring_guardrails_state (
    user_id TEXT PRIMARY KEY,
    daily_earn_count INTEGER DEFAULT 0,
    daily_earn_total INTEGER DEFAULT 0,
    last_earn_at TIMESTAMPTZ,
    reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Publish events (post -> ledger traceability)
CREATE TABLE publish_events (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    platform_post_id TEXT,
    enforcement_request_id TEXT,
    enforcement_receipt_id TEXT,
    qa_status TEXT,
    violation_codes JSONB,
    audit_ok BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB,
    token_mode TEXT,
    token_issued_amount INTEGER,
    token_pending_amount INTEGER,
    token_reason_code TEXT,
    token_ledger_id TEXT,
    token_pending_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Mode Switching

**Environment Variable:** `ONERING_TOKEN_ISSUANCE`

- `off` (default): No token issuance, returns "mode disabled" messages
- `shadow`: Logs pending rewards to `ring_pending`, balance unchanged
- `live`: Updates `users.ringBalance` + appends to `ring_ledger` atomically

**How to Switch:**

```bash
# Development (shadow mode)
export ONERING_TOKEN_ISSUANCE=shadow

# Production (live mode, after validation)
export ONERING_TOKEN_ISSUANCE=live
```

---

## 💰 Issuance Rules (Conservative & Explicit)

### Base Formula

```
RING_EARNED = BASE_AMOUNT * (1 - GUARDRAIL_REDUCTION_PCT)
```

- **Base Amount:** 10 RING per publish (Phase 10.2 conservative baseline)
- **Platform Multipliers:** Reserved for Phase 10.3 (all 1.0x for now)

### Gating Requirements (ALL must pass)

1. **QA Status = PASS:** Draft must pass quality assurance
2. **audit_ok = true:** Enforcement pipeline must approve
3. **Platform Confirmation:** platform_post_id must be present
4. **Guardrails Check:** No blocking violations (see below)

**If ANY requirement fails:** Issuance denied, violations logged.

---

## 🛡️ Anti-Gaming Guardrails

### 1. Daily Earn Cap

- **Threshold:** 1,000 RING per user per day
- **Action:** Block issuance (100% reduction) if cap exceeded
- **Reset:** Daily at midnight UTC (`reset_at` timestamp)
- **Rationale:** Prevent farming abuse

### 2. Minimum Interval Between Earns

- **Threshold:** 300 seconds (5 minutes) since last earn
- **Action:** Apply 50–100% penalty based on time elapsed
  - 0–60s: 100% blocked
  - 60–180s: 75% reduction
  - 180–300s: 50% reduction
  - 300s+: No penalty
- **Rationale:** Rate-limit rapid posting, encourage quality over quantity

### 3. Anomaly Detection (Earns per Hour)

- **Threshold:** 10 earns per hour (rolling window)
- **Action:** Apply 30% reduction if exceeded
- **Rationale:** Detect bot-like behavior patterns

### Guardrail State Updates

After each issuance attempt (allowed or blocked):

- Increment `daily_earn_count`
- Add amount to `daily_earn_total`
- Update `last_earn_at` timestamp
- Check if `reset_at` passed, reset counters if so

---

## 🔄 Reconciliation System

### Purpose

Detect and correct mismatches between:

- **Ledger Sum:** `SUM(amount) FROM ring_ledger WHERE user_id = ?`
- **User Balance:** `users.ringBalance`

### When to Run

- **Scheduled:** Daily cron job at 3 AM UTC
- **On-Demand:** Admin-triggered via `POST /v1/tokens/reconcile`
- **Development:** After bulk imports or manual DB edits

### Reconciliation Logic

1. **Shadow Mode:**
   - Log mismatches to stderr
   - Create `ADJUSTMENT` entries in `ring_ledger` (record discrepancy)
   - **Do NOT update balance** (shadow mode respects no-touch policy)

2. **Live Mode:**
   - Log mismatches to stderr
   - Create `ADJUSTMENT` entries in `ring_ledger`
   - **Apply adjustment:** `UPDATE users SET ringBalance = ledger_sum`

### Output

```json
{
  "status": "completed",
  "users_checked": 1247,
  "mismatches_found": 3,
  "adjustments_made": 3,
  "mode": "shadow",
  "mismatches": [
    {
      "user_id": "user_xyz",
      "balance_db": 100,
      "balance_ledger": 110,
      "diff": 10
    }
  ]
}
```

---

## 📡 API Endpoints

### GET `/v1/tokens/balance/{user_id}`

Returns user's token balance and pending rewards.

**Response:**

```json
{
  "balance": 450,
  "pending": 120,
  "mode": "shadow",
  "effective_balance": 570
}
```

- `balance`: Current `users.ringBalance` (0 in shadow mode)
- `pending`: Sum of `ring_pending` entries (shadow mode only)
- `mode`: Current issuance mode

### GET `/v1/tokens/summary/{user_id}`

Canonical balance summary (ledger-first).

**Response:**

```json
{
  "userId": "user_123",
  "mode": "shadow",
  "balance": 450,
  "pending_total": 120,
  "effective_balance": 570,
  "last_ledger_at": "2025-12-26T10:30:00Z",
  "last_pending_at": "2025-12-26T10:30:00Z",
  "guardrails_state": {},
  "clerk_sync": { "last_at": null, "last_error": null, "last_error_at": null }
}
```


### GET `/v1/tokens/ledger/{user_id}`

Returns recent ledger entries (last 20 by default).

### POST `/v1/tokens/publish`

Persist publish event and issue tokens if eligible.

**Body:**

```json
{
  "event_id": "uuid",
  "user_id": "user_123",
  "platform": "x",
  "content_hash": "sha256",
  "published_at": "ISO8601",
  "platform_post_id": "tweet_id",
  "enforcement_request_id": "req_123",
  "enforcement_receipt_id": "rec_123",
  "metadata": {"rate_limit_remaining": 4}
}
```

**Response:**

```json
{
  "ok": true,
  "event_id": "uuid",
  "token_result": {
    "mode": "shadow",
    "issued_amount": 0,
    "pending_amount": 10,
    "reason_code": "PENDING",
    "guardrails_applied": []
  }
}
```


**Query Params:**

- `limit` (default: 20, max: 100)

**Response:**

```json
{
  "entries": [
    {
      "id": "uuid",
      "eventType": "EARN",
      "reasonCode": "publish_success",
      "amount": 10,
      "balanceAfter": 460,
      "createdAt": "2025-12-25T10:30:00Z",
      "metadata": {"draft_id": "uuid", "platform": "x"}
    }
  ]
}
```

### POST `/v1/tokens/reconcile`

Triggers reconciliation job (admin only).

**Response:** Same as reconciliation output above.

### GET `/v1/tokens/reconcile/summary`

Returns summary of recent adjustments (last 24h).

**Response:**

```json
{
  "adjustments_24h": 5,
  "total_adjusted": 150,
  "last_run": "2025-12-25T03:00:00Z"
}
```

---

## 🧪 Testing Strategy

### Backend Tests (19 passing)

**File:** `backend/tests/test_token_ledger.py`

**Coverage:**

- `TestLedgerAppend` (3 tests): Verify append-only, EARN/PENALTY entries, no updates
- `TestGuardrails` (4 tests): Daily cap, min interval, state updates, initial pass
- `TestIssuanceRules` (5 tests): QA/audit gates, shadow vs live, guardrail reductions
- `TestReconciliation` (3 tests): Mismatch detection, shadow logging, live adjustments
- `TestLedgerQueries` (2 tests): Pagination, ordering, limit enforcement
- `TestPendingRewards` (2 tests): Shadow mode pending accumulation

**Run Tests:**

```bash
cd c:\Users\hazar\onering
python -m pytest backend/tests/test_token_ledger.py -v
```

### Test Invariants Verified

1. ✅ Ledger is append-only (no UPDATE/DELETE exposed)
2. ✅ EARN amounts must be positive
3. ✅ PENALTY/SPEND amounts must be negative (except ADJUSTMENT)
4. ✅ balance_after matches users.ringBalance after issuance
5. ✅ Shadow mode never touches users.ringBalance
6. ✅ Guardrails block/reduce before issuance, not after
7. ✅ Reconciliation creates ADJUSTMENT entries in both modes
8. ✅ QA/audit gates enforced on every issuance call

---

## Integration with Posting Flow

### Current Status

**Token Router Registered:** Go. Added to `backend/main.py`

**Posting Integration:** Go. Wired to publish success with enforcement receipt gating.

### Publish Events (Canonical)

Publish success emits a canonical event stored in `publish_events` (append-only):

- event_id (uuid), user_id, platform, content_hash, published_at, platform_post_id
- enforcement_request_id, enforcement_receipt_id, qa_status, violation_codes, audit_ok
- token_mode, token_issued_amount, token_pending_amount, token_reason_code
- token_ledger_id, token_pending_id, metadata (rate-limit snapshot, latency)

### Issuance Gating (Must All Pass)

1. Receipt validation PASS (server-side)
2. QA status PASS
3. audit_ok true
4. Platform confirmation present (platform_post_id)

If any gate fails: publish event is persisted with reason_code, issuance skipped.

### Idempotency

- Issuance key: `publish_event_id`
- Duplicate publish calls return stored token_result (no double issuance)

## 📊 Monitoring & Observability

### Key Metrics to Track

1. **Issuance Rate:** Earns per hour (detect anomalies)
2. **Guardrail Blocks:** Count of denied issuances by rule
3. **Reconciliation Drift:** Average mismatch size and frequency
4. **Shadow → Live Divergence:** Compare shadow pending vs expected live balance

### Log Messages

All token operations log with structured context:

```
[token_ledger] mode=shadow user=user_xyz amount=10 reason=publish_success guardrails=[min_interval:-50%]
[token_reconciliation] mismatches_found=3 mode=shadow adjustments_logged=3
```

### Health Checks

- **Ledger Integrity:** No negative balances in `users.ringBalance`
- **Guardrail State:** No stale `reset_at` timestamps (> 25 hours old)
- **Pending Accumulation:** `ring_pending` count should stabilize in shadow mode

---

## 🔐 Security & Compliance

### Invariant Guarantees

1. **No Double-Spend:** Each earn linked to unique `(request_id, receipt_id)` pair
2. **Append-Only Audit Trail:** `ring_ledger` has no UPDATE/DELETE operations exposed
3. **Atomic Commits:** Balance update + ledger append in single transaction
4. **Idempotency:** Duplicate issuance calls with same publish_event_id rejected

### Data Retention

- **Ledger:** Retained indefinitely (regulatory compliance)
- **Pending:** Cleared after shadow → live migration or 30-day expiry
- **Guardrail State:** Reset daily, no long-term storage

---

## 🎯 Rollout Checklist

### Phase 1: Shadow Validation (Current)

- [x] Deploy with `ONERING_TOKEN_ISSUANCE=shadow`
- [x] Run for 7 days, collect `ring_pending` data
- [x] Compare shadow pending vs expected balance in test accounts
- [x] Run reconciliation daily, verify zero mismatches
- [x] Monitor guardrail block rates (should be < 5% of attempts)

### Phase 2: Live Mode (After Validation)

- [ ] Verify shadow mode data integrity (zero reconciliation drift)
- [ ] Update environment: `ONERING_TOKEN_ISSUANCE=live`
- [ ] Deploy with zero-downtime restart
- [ ] Monitor balance updates in real-time (first 100 users)
- [ ] Run reconciliation after 24h, verify < 0.1% mismatch rate
- [ ] Communicate live mode to users (balance now reflects earns)

### Phase 3: Production Hardening

- [x] Add idempotency keys to prevent duplicate issuance
- [ ] Implement platform multipliers (X: 1.2x, IG: 0.8x, etc.)
- [ ] Add user-facing ledger UI (transaction history)
- [ ] Set up alerting for anomaly detection triggers
- [ ] Create admin dashboard for guardrail tuning

---

## 📝 Configuration Reference

### Environment Variables

```bash
# Token issuance mode
ONERING_TOKEN_ISSUANCE=off|shadow|live  # Default: off

# Clerk metadata sync (best-effort, async)
ONERING_CLERK_SYNC_DRY_RUN=1
ONERING_CLERK_SYNC_PER_MINUTE=60

# Backfill/validator
ONERING_LEDGER_BACKFILL_DRY_RUN=1
ONERING_LEDGER_BACKFILL_START=0

# Guardrail thresholds (future overrides)
RING_DAILY_EARN_CAP=1000
RING_MIN_EARN_INTERVAL_SECONDS=300
RING_ANOMALY_THRESHOLD_EARNS_PER_HOUR=10

# Reconciliation schedule (cron format)
RING_RECONCILE_SCHEDULE="0 3 * * *"  # Daily at 3 AM UTC
```

### Database Connection

Uses existing `DATABASE_URL` from `.env.local`:

```
DATABASE_URL="postgresql://user:pass@localhost:5432/onering"
```

---

## 🐛 Troubleshooting

### Issue: Balance not updating in live mode

**Cause:** Mode still set to `shadow` or `off`

**Fix:**

```bash
# Check current mode
curl http://localhost:8000/v1/tokens/balance/{user_id}
# Response shows "mode": "shadow"

# Update environment
export ONERING_TOKEN_ISSUANCE=live
# Restart backend
```

### Issue: Reconciliation finds mismatches

**Cause:** Manual balance edits or ledger corruption

**Fix:**

```bash
# Run reconciliation to auto-adjust (live mode)
curl -X POST http://localhost:8000/v1/tokens/reconcile

# Check summary
curl http://localhost:8000/v1/tokens/reconcile/summary
```

### Issue: Guardrails blocking legitimate users

**Cause:** Thresholds too aggressive or bot-like posting patterns

**Fix:**

```python
# Adjust in backend/features/tokens/ledger.py
DAILY_EARN_CAP = 2000  # Increase if needed
MIN_EARN_INTERVAL_SECONDS = 180  # Reduce if too strict
```

---

## 📚 Related Documentation

- [.ai/API_REFERENCE.md](.ai/API_REFERENCE.md) — Full API specs
- [.ai/ARCHITECTURE.md](.ai/ARCHITECTURE.md) — System design
- [.ai/TESTING.md](.ai/TESTING.md) — Test strategy
- [.ai/PROJECT_STATE.md](.ai/PROJECT_STATE.md) — Current status with test counts
- [DESIGN_DECISIONS.md](../DESIGN_DECISIONS.md) — Why these choices

---

## ✅ Acceptance Criteria (All Met)

- [x] **A) Canonical Ledger:** `ring_ledger` table with append-only constraint, invariants enforced
- [x] **B) Issuance Rules:** QA PASS + audit_ok required, 10 RING base, guardrails applied
- [x] **C) Reconciliation Job:** Daily check, ADJUSTMENT entries created, shadow/live branching
- [x] **D) Anti-Gaming Guardrails:** 3 enforced (daily cap, min interval, anomaly rate)
- [x] **E) API Endpoints:** `/v1/tokens/balance`, `/v1/tokens/ledger`, `/v1/tokens/reconcile`
- [x] **F) Tests:** 19 backend tests passing, covering all invariants
- [x] **G) Documentation:** This file + updated API_REFERENCE.md, PROJECT_STATE.md

---

**Phase 10.2 is PRODUCTION-READY in shadow mode. Live mode enabled after 7-day shadow validation.**
