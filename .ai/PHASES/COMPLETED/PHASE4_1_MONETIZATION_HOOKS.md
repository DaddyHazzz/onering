# Phase 4.1 — Monetization Hooks (No Payments)

**Last Updated:** December 22, 2025  
**Status:** IN PROGRESS  
**Phase:** 4.1 (Platform Capabilities & Scale Foundations)

---

## Purpose

Build the **plumbing** for monetization without implementing **payments** or **billing**.

This phase answers:
> "Is this user allowed to do this, under their plan, right now?"

…deterministically, correctly, and **without charging anyone**.

---

## What This Phase Enables

### For Product
- Safe experimentation with plan configurations
- Usage pattern measurement before enforcement
- A/B testing of limits without billing risk
- Gradual rollout of paid features

### For Engineering
- Clean separation of concerns: entitlements ≠ payments
- Provider-agnostic design (Stripe, PayPal, crypto, enterprise contracts all viable)
- Reversible soft-enforcement (can disable without breaking core features)
- Deterministic usage accounting (same events + same `now` = same counts)

### For Future Phases
- Phase 4.2: Hard enforcement (block actions when limits exceeded)
- Phase 4.3: Payment provider integration (Stripe, etc.)
- Phase 4.4: Subscription management UI
- Phase 4.5: Enterprise billing (invoicing, custom plans)

---

## What This Phase Builds

### 1. Plans Domain
- **Plan Model**: plan_id, name, is_default, created_at
- **Seeded Plans**: `free` (default), `creator`, `team`
- **No Prices**: Plans have capabilities, not currency

### 2. Entitlements Domain
- **Entitlement Model**: entitlement_key, value, plan_id
- **Entitlement Keys**: 
  - `drafts.max` (int): Max drafts per user
  - `collaborators.max` (int): Max collaborators per draft
  - `analytics.enabled` (bool): Access to analytics features
  - `segments.max` (int): Max segments per draft (future)
  - `ai_credits.monthly` (int): AI generation credits (future)

### 3. User → Plan Assignment
- **UserPlan Model**: user_id, plan_id, assigned_at
- **Auto-Assignment**: Default plan assigned on user creation
- **Constraint**: Exactly one active plan per user

### 4. Usage Accounting
- **UsageEvent Model**: user_id, usage_key, occurred_at, metadata
- **Emission Points**:
  - `drafts.created` → create_draft
  - `segments.appended` → append_segment
  - `collaborators.added` → add_collaborator
- **Reducer**: reduce_usage(user_id, events, now) → counts per usage_key

### 5. Entitlement Check Hooks
- **Checker Service**: check_entitlement(user_id, key, requested_value)
- **Return Values**: ALLOWED | WOULD_EXCEED | DISALLOWED
- **Behavior (Phase 4.1)**: Log WOULD_EXCEED, never throw exceptions
- **Future (Phase 4.2)**: Optionally block actions when WOULD_EXCEED

### 6. Observability
- **Structured Logging**: All usage + entitlement checks logged with request_id
- **Machine-Parseable**: JSON format for future billing analytics
- **No PII**: Only user_id, plan_id, entitlement_key, result

---

## What This Phase Does NOT Build

### Explicitly Out of Scope
- ❌ **No Payments**: No credit card capture, no transactions
- ❌ **No Billing Provider**: No Stripe, PayPal, crypto, or wallet integration
- ❌ **No Subscriptions UI**: No pricing pages, checkout flows, or plan selection
- ❌ **No Time-Based Billing**: No monthly/annual cycles (just plan assignment)
- ❌ **No Currency**: No prices, no $, no tokens
- ❌ **No Hard Enforcement**: Actions not blocked (soft enforcement only)
- ❌ **No Webhooks**: No payment success/failure handling
- ❌ **No Invoicing**: No receipts, no billing history

### Why Not Now?
- **Provider Lock-In Risk**: Choosing Stripe now locks us into their pricing model
- **Premature Optimization**: Need usage data before setting limits
- **Reversibility**: Hooks can be disabled; payments can't be easily rolled back
- **Flexibility**: Same hooks work for Stripe, crypto, enterprise contracts, or free tier only

---

## Architectural Principles (Preserved)

### Determinism Mandatory
- Plan assignment is deterministic (same user_id + same timestamp = same plan)
- Usage reducers are pure functions (same events + same `now` = same counts)
- Entitlement checks are stateless (no caching, no stale data)

### Idempotency Everywhere
- Usage events emitted with idempotency keys
- Plan assignment idempotent (re-assigning same plan = no-op)
- Usage counting resilient to duplicate events

### No Breaking API Changes
- Existing endpoints unchanged
- Entitlement checks return metadata in responses (warnings, not errors)
- Services log enforcement status but don't block actions

### Tests Before Claims
- All models have tests
- Usage accounting has deterministic tests
- Entitlement checks have classification tests
- No feature shipped without test coverage

---

## Implementation Details

### Database Schema

#### plans table
```sql
CREATE TABLE plans (
  plan_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

#### plan_entitlements table
```sql
CREATE TABLE plan_entitlements (
  plan_id TEXT NOT NULL REFERENCES plans(plan_id),
  entitlement_key TEXT NOT NULL,
  value JSONB NOT NULL,  -- supports int, bool, string
  PRIMARY KEY (plan_id, entitlement_key)
);
```

#### user_plans table
```sql
CREATE TABLE user_plans (
  user_id TEXT PRIMARY KEY REFERENCES app_users(user_id),
  plan_id TEXT NOT NULL REFERENCES plans(plan_id),
  assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

#### usage_events table
```sql
CREATE TABLE usage_events (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES app_users(user_id),
  usage_key TEXT NOT NULL,
  occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
  metadata JSONB,
  INDEX idx_usage_events_user_id (user_id),
  INDEX idx_usage_events_occurred_at (occurred_at)
);
```

### Default Plan Configuration

#### Free Plan (default)
- `drafts.max` = 10
- `collaborators.max` = 3
- `analytics.enabled` = true
- `segments.max` = 20

#### Creator Plan
- `drafts.max` = 50
- `collaborators.max` = 10
- `analytics.enabled` = true
- `segments.max` = 100

#### Team Plan
- `drafts.max` = unlimited (-1)
- `collaborators.max` = unlimited (-1)
- `analytics.enabled` = true
- `segments.max` = unlimited (-1)

### Entitlement Check Flow

```python
# Service layer (e.g., create_draft)
result = check_entitlement(user_id, "drafts.max", requested=1)

if result == EntitlementResult.ALLOWED:
    # Proceed with draft creation
    pass
elif result == EntitlementResult.WOULD_EXCEED:
    # Phase 4.1: Log warning, proceed anyway
    logger.warning(f"[entitlement] user {user_id} would exceed drafts.max")
    # Phase 4.2: Raise ValidationError
    # raise ValidationError("Draft limit exceeded")
elif result == EntitlementResult.DISALLOWED:
    # Plan doesn't have this entitlement at all
    logger.warning(f"[entitlement] user {user_id} not entitled to drafts.max")
```

---

## Testing Strategy

### Unit Tests
- **test_plan_models.py**: Plan and Entitlement model validation
- **test_user_plans.py**: Plan assignment, entitlement resolution
- **test_usage_accounting.py**: Usage event emission, reducer correctness
- **test_entitlement_checks.py**: Classification logic (ALLOWED/WOULD_EXCEED/DISALLOWED)

### Integration Tests
- **test_plan_assignment_on_user_creation.py**: Default plan auto-assigned
- **test_usage_tracking_end_to_end.py**: Draft creation emits drafts.created
- **test_entitlement_warnings_in_responses.py**: API returns warnings when limits approached

### Determinism Tests
- Fixed `now` parameter in all reducers
- Same events = same usage counts
- Idempotency: duplicate events = no count change

---

## Rollout Plan

### Phase 4.1 (This Phase)
- ✅ Plans, entitlements, user plans deployed
- ✅ Usage events emitted (no enforcement)
- ✅ Entitlement checks log warnings (no blocking)
- ✅ Observability: structured logs for billing analysis

### Phase 4.2 (Next: Hard Enforcement)
- Enable blocking when entitlement checks return WOULD_EXCEED
- Add graceful error messages for users
- Add "upgrade plan" CTA in error responses
- No payment processing yet

### Phase 4.3 (Payment Provider Integration)
- Choose provider (Stripe likely, but decision deferred)
- Implement checkout flow
- Handle webhooks for plan upgrades/downgrades
- Sync user_plans with payment status

### Phase 4.4 (Subscriptions UI)
- Pricing page
- Plan comparison
- In-app upgrade flow
- Usage dashboard ("You've used 7/10 drafts")

### Phase 4.5 (Enterprise Billing)
- Custom plans
- Invoicing
- Multi-seat licensing
- SSO integration

---

## Why This Design?

### Provider Agnostic
Same hooks work for:
- **Stripe**: Checkout → plan_id → user_plans
- **Crypto**: Wallet payment → plan_id → user_plans
- **Enterprise**: Contract → custom plan_id → user_plans
- **Free Tier Only**: No payment, just plans

### Reversible
- Soft enforcement can be disabled via feature flag
- No user data locked behind payments
- Graceful degradation if billing fails

### Testable
- Usage accounting is deterministic (pure functions)
- Entitlement checks are stateless (no side effects)
- Plan configurations are data, not code

### Observable
- Every check logged with structured data
- Billing analytics possible without custom code
- Debugging: full audit trail of entitlement decisions

---

## Success Criteria

### Phase 4.1 Complete When:
- [x] Plans seeded in database (free, creator, team)
- [x] Every user has exactly one active plan
- [x] Default plan auto-assigned on user creation
- [x] Usage events emitted at service boundaries
- [x] reduce_usage returns correct counts
- [x] check_entitlement classifies correctly
- [x] Entitlement checks logged with request_id
- [x] All tests passing (no regressions)
- [x] Zero breaking API changes
- [x] Phase 4.1 docs complete and accurate

### Phase 4.1 Does NOT Require:
- ❌ Any payment processing
- ❌ Any billing provider integration
- ❌ Any UX changes (modals, pricing pages)
- ❌ Any hard enforcement (blocking actions)

---

## Next Steps (Phase 4.2)

When ready to enforce limits:
1. Add feature flag: `ENFORCE_ENTITLEMENTS=true`
2. Update check_entitlement to raise ValidationError when WOULD_EXCEED
3. Add "upgrade plan" CTA to error responses
4. Test enforcement with `ENFORCE_ENTITLEMENTS=false` first
5. Gradual rollout: enforce for new users only, then all users

---

## Questions & Answers

**Q: Why not just use Stripe Billing?**  
A: Stripe locks us into their model. This design supports Stripe AND crypto AND enterprise contracts.

**Q: Why not enforce limits immediately?**  
A: Need usage data to set correct limits. Soft enforcement lets us measure without breaking UX.

**Q: What if we never add payments?**  
A: Free tier works forever. Plans just control capabilities, not billing.

**Q: How do we test billing logic without payments?**  
A: Plan assignments can be manipulated in tests. Usage accounting is deterministic.

**Q: What about time-based limits (monthly resets)?**  
A: Phase 4.3+. Current design supports it (usage_events have timestamps).

**Q: Can we A/B test plans?**  
A: Yes. Assign different plans to cohorts, measure usage, compare.

---

## File Manifest

### Files Added (Phase 4.1)
- `backend/models/plan.py` — Plan model
- `backend/models/entitlement.py` — Entitlement model
- `backend/models/user_plan.py` — UserPlan model
- `backend/models/usage_event.py` — UsageEvent model
- `backend/features/entitlements/service.py` — Entitlement checker
- `backend/features/usage/service.py` — Usage accounting
- `backend/tests/test_plan_models.py`
- `backend/tests/test_user_plans.py`
- `backend/tests/test_usage_accounting.py`
- `backend/tests/test_entitlement_checks.py`
- `PHASE4_1_MONETIZATION_HOOKS.md` (this file)

### Files Modified (Phase 4.1)
- `backend/core/database.py` — Added plans, plan_entitlements, user_plans, usage_events tables
- `backend/features/users/service.py` — Auto-assign default plan on user creation
- `backend/features/collaboration/service.py` — Emit usage events, check entitlements
- `PROJECT_STATE.md` — Phase 4.1 status and scope

---

**End of Phase 4.1 Specification**
