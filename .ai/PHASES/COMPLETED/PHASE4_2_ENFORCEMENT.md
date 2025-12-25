# Phase 4.2 — Hard Entitlement Enforcement & Overrides

## Why Enforcement Is Separated From Monetization
- Billing providers (Stripe, crypto, enterprise) can change without changing enforcement logic.
- Hooks must work for free tiers and enterprise contracts alike.
- Enforcement can be toggled per plan without touching payments or UI.

## Reversibility Guarantees
- Plan-level flag `enforcement_enabled` (default: false). Disable to revert to Phase 4.1 soft warnings.
- Grace overage window `enforcement_grace_count` lets us roll out gradually before hard-blocking.
- Overrides table allows per-user escape hatches without redeploys.
- Deterministic reducers mean no state drift: same events + same now = same decision.

## What Is Blocked vs Warned
- **Blocked (when enforcement enabled and grace exhausted):**
  - Creating drafts (`drafts.max`)
  - Appending segments (`segments.max`)
  - Adding collaborators (`collaborators.max`)
- **Warn-only:**
  - Over-limit actions when grace overages remain (decision = WARN_ONLY)
  - Enforcement disabled for plan (Phase 4.1 behavior)
- **Not touched:**
  - Payments, checkout, billing, pricing pages (explicitly out of scope)
  - UI changes (backend-only work)

## Admin/Support Escape Hatches
- `entitlement_overrides` table: (user_id, entitlement_key, override_value, expires_at, created_by)
- Resolution order: active override → plan entitlement → default behavior
- `set_override`, `clear_override`, `get_effective_entitlement` for operational controls

## Safety Rails
- No partial mutations when blocked (no drafts/segments/collaborators created, no usage events emitted).
- Structured logs on BLOCKED/WARN_ONLY include user_id, plan_id, entitlement_key, usage, limit, request_id.
- Metrics counters (log-only): `enforcement.blocked.count`, `enforcement.warned.count`.

## Rollout Plan
1) Default: enforcement off (Phase 4.1 behavior)
2) Enable per plan, set grace > 0
3) Reduce grace to 0 when confident
4) Use overrides for support cases

## Testing Strategy
- Unit tests for plan flags, enforcement decisions, overrides, and service-level blocking
- Full backend suite: `python -m pytest backend/tests -q`
- Deterministic tests via fixed `now` values
