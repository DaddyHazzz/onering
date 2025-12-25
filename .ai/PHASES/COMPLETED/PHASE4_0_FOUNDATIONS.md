# Phase 4.0 — Platform Foundations (✅ COMPLETE)

**Last Updated:** December 22, 2025  
**Status:** COMPLETE  
**Test Results:** 353/353 backend tests passing (100%)

---

## Purpose
Establish core platform capabilities for scale: explicit User domain, role-based collaboration, event schema versioning, and optional read-model snapshots. Preserve boring stability: no behavior surprises, no API breakage, deterministic outputs.

---

## What Was Built

### 1. User Domain (Real Multi-User Foundations)
- **app_users table**: user_id (PK), display_name, status, created_at (renamed to avoid legacy conflicts)
- **User model**: Frozen Pydantic model with normalized_display_name fallback (@u_<sha1 6-char>)
- **User service**: `get_or_create_user(user_id)`, `get_user(user_id)`, `normalize_display_name()`
- **Integration**: Called at all entry points (create_draft, append_segment, pass_ring, accept_invite)
- **Tests**: test_user_domain.py (idempotency, normalization, collab paths)

### 2. Collaboration Roles (Owner/Collaborator Guardrails)
- **draft_collaborators.role**: Column added (owner/collaborator)
- **Persistence**: `add_collaborator()` accepts role param; `list_collaborators()` returns (user_id, role)
- **Service guardrails**: append_segment requires owner/collaborator AND ring holder
- **Backward compatible**: No API surface changes; internal enforcement only
- **Tests**: test_collab_roles.py (append_requires_owner_or_collaborator_and_ring_holder)

### 3. Event Schema Versioning (Safe Future-Proofing)
- **Event model**: All events include schema_version=1 (default)
- **Reducers**: All three reducers (reduce_draft_analytics, reduce_user_analytics, reduce_leaderboard) validate schema_version==1 and raise ValidationError for unknown
- **Future-proof**: New schema versions can be added with explicit migration logic
- **Tests**: test_event_schema_versioning.py (unknown version rejected)

### 4. Read Model Snapshots (Performance Scaffolding)
- **snapshots.py**: In-memory snapshot writer for draft analytics and leaderboard
- **Writers**: `write_draft_analytics_snapshots()`, `write_leaderboard_snapshot()`
- **Getters**: `get_draft_analytics_snapshot()`, `get_leaderboard_snapshot()`
- **Guarantee**: Snapshots equal reducer output byte-for-byte for same `now`
- **Source of truth**: Reducers remain canonical; snapshots optional caching layer
- **Tests**: test_snapshots.py (draft_snapshots_match_reducer, leaderboard_snapshot_matches_reducer)

---

## What Was NOT Built (Explicit Non-Goals)
- **No monetization**: No pricing, checkout, or payment changes (Phase 4.1+)
- **No blockchain/tokens**: No on-chain dependencies or crypto integrations
- **No WebSockets**: HTTP-only; no real-time transports
- **No LLM ranking**: No AI-powered user/content scoring
- **No role UX**: Roles enforced at service layer only; no UI changes
- **No background workers**: No schedulers, cron, or async job queues
- **No breaking API changes**: All changes backward compatible

---

## Files Added
- `backend/models/user.py` — User model with normalized display name
- `backend/features/users/service.py` — User domain operations
- `backend/features/analytics/snapshots.py` — Optional snapshot writer
- `backend/tests/test_user_domain.py` — User service tests (2 tests)
- `backend/tests/test_collab_roles.py` — Role enforcement tests (1 test)
- `backend/tests/test_event_schema_versioning.py` — Schema validation tests (1 test)
- `backend/tests/test_snapshots.py` — Snapshot correctness tests (2 tests)

---

## Files Modified
- `backend/core/database.py` — Added app_users table
- `backend/features/collaboration/persistence.py` — Role support (add_collaborator, list_collaborators)
- `backend/features/collaboration/service.py` — User existence checks, role guardrails in append_segment
- `backend/features/collaboration/invite_service.py` — User existence check in accept_invite
- `backend/features/analytics/event_store.py` — schema_version=1 default in Event model
- `backend/features/analytics/reducers.py` — Schema version validation in all reducers
- `PROJECT_STATE.md` — Marked Phase 4.0 COMPLETE, updated test counts

---

## Architectural Principles Preserved
- **Determinism mandatory**: Reducers remain pure; snapshots are deterministic for same `now`
- **Idempotency on all mutations**: No duplicate user creation, role assignment, or event processing
- **No breaking API changes**: All changes backward compatible with existing clients
- **Tests before claims**: 353/353 backend tests passing; no regressions
- **Stability over novelty**: Boring, predictable platform improvements

---

## Why This Enables Phase 4.1+

### Phase 4.1 — Monetization Hooks (Next)
- User domain now in place → billing/subscription can reference app_users.user_id
- Roles established → premium tiers can gate features by role
- Schema versioning → payment events can be added without breaking analytics

### Phase 4.2+ — Scale & Performance
- Snapshots scaffolded → leaderboard can serve from cache instead of full reduce
- User normalization → display names consistent across all collaboration paths
- Roles → future viewer/admin roles can be added without service refactor

---

## Verification Checklist (✅ All Complete)
- [x] All existing tests remain green (353/353)
- [x] New tests cover users, roles, schema versions, snapshots
- [x] Determinism verified with fixed `now` in reducers and snapshots
- [x] User domain integrated at all entry points
- [x] Roles enforced in append_segment guardrails
- [x] Schema version validation in all reducers
- [x] Snapshots equal reducer output for same `now`
- [x] No breaking API changes
- [x] PROJECT_STATE.md updated with accurate Phase 4.0 status

---

## Next Steps (Phase 4.1 — Monetization Hooks)
Phase 4.1 will introduce:
- Billing/subscription tables (no Stripe integration yet)
- Premium tier flags (user.tier: free/pro/team)
- Usage limits (rate limits tied to user.tier)
- Payment event schema (DeferredPayment, SubscriptionChanged)

Phase 4.1 will NOT introduce:
- No actual payment processing (Stripe integration deferred)
- No frontend pricing pages
- No checkout flows
- Focus: internal billing domain only
