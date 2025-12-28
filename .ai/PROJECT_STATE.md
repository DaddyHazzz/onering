# Project State (Canonical)

**Last Updated:** December 27, 2025 @ 23:45 UTC  
**Status:** Phase 10.3-S3 SAAS PLATFORM SHIFT IN PROGRESS. All tests passing (backend 735+, frontend 448, total 1183+).

## Test Coverage

| Metric | Count | Status |
|--------|-------|--------|
| Backend Tests | 735+/735+ | ✅ 100% |
| Frontend Tests | 448/448 | ✅ 100% (+50 from S3) |
| **Total** | **1183+/1183+** | ✅ **100%** |
| Skipped | 0 | ✅ ZERO |
| --no-verify bypasses | 0 | ✅ ZERO |

**Last Full Run:** December 27, 2025 @ 23:45 UTC  
**Duration:** ~14 seconds (frontend), ~5 minutes (full suite)

## Current Phase Status

### 🔄 Phase 10.3-S3: SaaS Platform Shift - Org-Aware UX (IN PROGRESS)
**Session Start:** December 27, 2025 @ 17:00 UTC  
**Current Status:** 60% COMPLETE (deliverables 0-4 done, 5-7 in progress)

**Deliverables:**
- [x] **0. Preflight** — git clean, secret scan clean, no secrets detected
- [x] **1. Org-Aware UI Skeleton** — useActiveOrgId(), buildOrgHeaders(), buildOrgParams(), OrgBadge component
- [x] **2. Partner Console** — /partner/external page with onboarding-focused UX
- [x] **3. Partner Onboarding Wizard** — 3-step flow (create key, test API, create webhook) with progress tracking
- [x] **4. Admin Console Enhancement** — Superuser org filter (X-Org-ID header threading)
- [ ] **5. Monitoring UX Improvements** — Org filtering + top failing orgs table + alert banners
- [ ] **6. Documentation** — Update consumer guide + create partner onboarding guide
- [ ] **7. Final Commit & Push** — Single clean commit to main

**Files Created (S3):**
1. [src/lib/org.ts](src/lib/org.ts) — 68 lines, org-aware utilities
2. [src/components/OrgBadge.tsx](src/components/OrgBadge.tsx) — 60 lines, org badge + switcher
3. [src/components/PartnerOnboardingWizard.tsx](src/components/PartnerOnboardingWizard.tsx) — 425 lines, 3-step wizard
4. [src/app/partner/external/page.tsx](src/app/partner/external/page.tsx) — 90 lines, partner console
5. [.ai/PARTNER_ONBOARDING.md](.ai/PARTNER_ONBOARDING.md) — 300 lines, partner guide (new)
6. [src/__tests__/org-aware.spec.tsx](src/__tests__/org-aware.spec.tsx) — 170 lines, utility tests (new)
7. [src/__tests__/partner-onboarding-wizard.spec.tsx](src/__tests__/partner-onboarding-wizard.spec.tsx) — 95 lines, integration tests (new)

**Files Modified (S3):**
1. [src/app/admin/external/page.tsx](src/app/admin/external/page.tsx) — Added filterOrgId state + org filter input + X-Org-ID headers
2. [src/app/monitoring/external/page.tsx](src/app/monitoring/external/page.tsx) — Added org filter logic + conditional rendering
3. [.ai/EXTERNAL_API_CONSUMER_GUIDE.md](.ai/EXTERNAL_API_CONSUMER_GUIDE.md) — Added hosted platform section + org scoping docs

**Key Architecture Decisions (S3):**
- **Graceful Degradation:** All org features hidden if no organization (single-user mode unaffected)
- **Header Threading:** X-Org-ID conditionally added to API calls via buildOrgHeaders()
- **Admin Filtering:** Superadmin can scope operations to any org via filterOrgId input
- **Partner Console:** Separate page (/partner/external) from admin console (/admin/external) for clearer separation
- **Onboarding Wizard:** 3-step flow with automatic progression, progress bar, copy-to-clipboard functionality
- **Tests:** Unit tests for utilities + integration patterns (not component render tests to avoid ClerkProvider)

**Non-Breaking Changes:**
- ✅ Single-user flow unchanged (org features degrade gracefully)
- ✅ Existing APIs unmodified (new headers are optional/conditional)
- ✅ All 448 frontend tests passing (up from 395)
- ✅ All 735+ backend tests passing

**Production Readiness (S3 - In Progress):**
- [x] Org-aware routing and header threading
- [x] Partner console with onboarding wizard
- [x] Admin console org filtering
- [x] Utility functions for org context
- [x] Component exports and graceful degradation
- [ ] Monitoring page org filtering + top failing table (in progress)
- [ ] Documentation updates (in progress)
- [ ] Final tests and gates (in progress)
- [ ] Single commit to main (pending)

**Environment Flags (S3 - New):**
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # For partner console API calls
# New org-aware features enabled by default (Clerk orgs)
```

---

### ✅ Phase 10.3-S2: External Platform Enablement Launch Pack (COMPLETE)

**Session 2 Enablement Launch Pack:**
- A) Canary + Kill-Switch: Per-key canary_enabled flag, 10 req/hr limit, ONERING_EXTERNAL_API_CANARY_ONLY mode
- B) Smoke Verification: webhook_sink.py (FastAPI tester), external_smoke.py (5-phase smoke test)
- C) Monitoring + Alerts: Real metrics, configurable thresholds (dead-letter, auth, rate limits, replay, latency)
- D) Admin Console: ExternalApiKeyInfo with canary, X-Canary-Mode headers
- E) Docs & Runbooks: 4 comprehensive guides (enablement, checklist, consumer guide, production report)
- F) Tests + Gates: 7 new canary tests, 735+ backend tests total, all passing
- G) Commit & Push: Deployed to main (commit 9afaa8a)

**Files Created/Modified:**
- New: 14 files (+3298 lines including 3 runbooks, monitoring, smoke script, webhook sink, tests)
- Modified: 31 files (+239 lines including external.py, api_keys.py)
- DB Migration: canary_enabled column added to external_api_keys

**Production Readiness:**
- [x] Canary mode tested (7 tests, all passing)
- [x] Smoke tooling complete
- [x] Monitoring endpoints with real counters
- [x] Alert thresholds configurable
- [x] Ops runbooks for 4-stage rollout
- [x] Consumer guide with code samples
- [x] Tests passing (735+ backend, zero failures, zero skips)
- [x] Kill-switches verified

**Staged Rollout Ready:**
- Stage 1: Enable API (canary-only mode)
- Stage 2: Enable webhooks (no delivery)
- Stage 3: Enable delivery (full webhooks)
- Stage 4: Disable canary-only (production)

---

### ✅ Phase 10.3-S1: External Platform Hardening (COMPLETE)
**Shipped:** December 25, 2025  
**Commit:** `feat(phase10.3): harden external API keys, rate limits, and webhooks delivery`

**Session 1 (Initial Implementation):**
- Created external read-only API endpoints under `/v1/external/*`
- Implemented API key system with bcrypt hashing and scopes
- Added webhook system with HMAC-SHA256 signing
- DB-backed rate limiting (hourly windows)
- Kill switches (default disabled)

**Session 2 (Hardening — December 25, 2025):**
- ✅ **Webhook Delivery Worker** — Durable event log, retry with backoff [60s, 300s, 900s], dead-letter handling
- ✅ **Security Hardening** — Replay protection (300s window), marks REPLAY_EXPIRED events
- ✅ **API Key Management** — Zero-downtime rotation (preserve_key_id), last_used_at tracking, IP allowlist enforcement
- ✅ **Rate Limit Atomicity** — Concurrency-safe increments with standard headers (X-RateLimit-Limit/Remaining/Reset)
- ✅ **Monitoring & Observability** — Real-time dashboards (/admin/external, /monitoring/external), metrics endpoints
- ✅ **Comprehensive Tests** — 3 new test suites (test_external_keys_hardening.py, test_webhooks_hardening.py, test_monitoring_external.py)
- ✅ **Documentation** — Updated API_REFERENCE.md, PHASE_10_3_EXTERNAL_PLATFORM.md with hardening details

**Test Additions (Session 2):**
- IP allowlist enforcement and validation
- API key rotation (preserve_key_id=true/false)
- Rate limit concurrency safety (atomic upserts, no over-issuance)
- Webhook signature verification and replay protection
- Webhook delivery worker (success, retry, dead-letter)
- Monitoring endpoints (admin auth, metrics, filters)

**Production Readiness:**
- [x] Webhook delivery worker (--once / --loop modes)
- [x] Signature verification examples (Python)
- [x] Replay protection (timestamp-based 300s window)
- [x] Rate limit concurrency tested (no quota over-issuance)
- [x] IP allowlist enforcement
- [x] Key rotation (zero-downtime)
- [x] Dead-letter monitoring
- [x] Admin console + monitoring dashboards
- [ ] Admin key rotation policy (Phase 10.4)
- [ ] Customer onboarding runbook (Phase 10.4)

**Environment Flags Added (Session 2):**
```bash
ONERING_WEBHOOKS_DELIVERY_ENABLED=0        # Delivery worker kill switch
ONERING_WEBHOOKS_MAX_ATTEMPTS=3            # Dead after 3 failures
ONERING_WEBHOOKS_BACKOFF_SECONDS="60,300,900"  # Retry delays
ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS=300     # 5-minute tolerance
ONERING_WEBHOOKS_DELIVERY_LOOP_SECONDS=5       # Worker poll interval
```
- At-least-once delivery semantics with status tracking
- Admin endpoints for webhook subscription management

**Part D: Safety & Controls**
- Kill switches: `ONERING_EXTERNAL_API_ENABLED=0` (default), `ONERING_WEBHOOKS_ENABLED=0` (default)
- External API returns 503 when disabled
- Webhooks not emitted when disabled
- Rate limit enforcement with 429 response
- Scope enforcement with 403 response
- Invalid key returns 401 response

**Part E: Tests**
- Comprehensive test suite: 27 tests covering all functionality
- Test coverage: API key generation/validation, scope enforcement, rate limiting, webhook signing/verification, kill switches
- All tests passing (5.48s runtime)

**Database Tables Added:**
- `external_api_keys` (API key storage with bcrypt hashing)
- `external_webhooks` (webhook subscriptions)
- `webhook_deliveries` (delivery tracking and retries)
- `external_api_rate_limits` (hourly rate limit windows)
- `external_api_blocklist` (banned keys/IPs)

**Impact:**
- External developers can access OneRing data via read-only API
- Webhook system enables real-time event notifications
- Kill switches provide safe rollout control
- Rate limiting prevents abuse
- All systems disabled by default for production safety

### ✅ Phase 9.6: Governance, Hooks, Safety Contracts
**Shipped:** December 25, 2025  
**Commit:** Not yet committed (documentation phase)

**Parts Completed:**

**Part A: Git Hooks with Opt-In Safety**
- Created `.git/hooks/pre-commit` and `.git/hooks/pre-push` with recursive guards
- Hooks are **disabled by default** (require `ONERING_HOOKS=1` environment variable)
- Default gate mode: `docs` (fast, non-blocking for documentation-only changes)
- Gate modes: `fast` (changed-only tests), `full` (all 1013 tests), `docs` (docs-only validation)
- Zero false positives from hook recursion (guarded via `ONERING_HOOK_RUNNING` flag)

**Part B: Documentation Standards**
- All canonical docs consolidated under `.ai/` directory
- Handoff Pack created at `.ai/HANDOFF_PACK/` (20 numbered files for new sessions)
- Versioned decision records (DECISIONS.md, TESTING.md, API_REFERENCE.md)
- Explicit non-goals documented (no blockchain, no multi-LLM, no self-hosting)

**Part C: Safety Contracts**
- GREEN ALWAYS policy: zero skipped tests, no `--no-verify` bypasses
- One commit per task maximum (prevents drift and merge conflicts)
- No code changes without explicit user request (agents must ask first)
- Docs-only changes use `pnpm gate --mode docs` (fast validation)

**Impact:**
- Repository governance locked (clear rules for all contributors)
- Hooks prevent accidental broken commits (but are opt-in, not blocking)
- Documentation always reflects actual system state
- Phase 10 can proceed with stable foundation

### ✅ Phase 8.9: Insights UI + Toast Notifications + Summary Cards
**Shipped:** December 25, 2025  
**Commit:** `d4a60b4`

**Parts Completed:**

**Part A: Backend Insights Finalization**
- Verified API contract matches .ai/API_REFERENCE.md
- Confirmed all alert thresholds deterministic (LONG_RING_HOLD, NO_ACTIVITY, SINGLE_CONTRIBUTOR)
- LONG_RING_HOLD uses `ring_state.passed_at` (works with zero ring passes)
- 6 integration tests in backend/tests/test_insights_api.py (100% green)

**Part B: Frontend Refactor**
- Removed all window.alert() calls from InsightsPanel.tsx
- Created Toast.tsx: Reusable notification system (4 types: success, error, info, warning)
  - useToast hook for state management
  - ToastContainer component with auto-dismiss
  - Accessible: role="region" aria-live="polite"
- Created InsightsSummaryCard.tsx: Lightweight insights summary for draft lists
  - Compact mode: Minimal badges (alert/recommendation counts)
  - Full mode: Top insight, counts, timestamps
  - Severity priority: critical > warning > info
  - Silent error handling for list contexts
- Tab accessibility verified (role, aria-controls, aria-labelledby)
- New test: Verifies no window.alert() usage
- 6 new InsightsSummaryCard tests (loading, priority, counts, compact, errors)

**Part C: Documentation Updates**
- .ai/API_REFERENCE.md: Expanded Insights endpoint with JSON response example
- .ai/PHASES/PHASE_8.md: Added Phase 8.9 section with backend/frontend/test details
- Created PHASE_8_9_COMPLETE.md: Comprehensive completion summary

**Impact:**
- Production-ready Insights UI with no blocking alerts
- Toast notifications accessible and dismissible (no jsdom conflicts)
- InsightsSummaryCard enables dashboard integration
- Frontend tests: 388 → 395 (+7 new tests)
- All 1013 tests GREEN, zero skipped, no --no-verify

### ✅ Phase 8.8: Docs Consolidation + Fast Gates + Agent Workflow
**Shipped:** December 25, 2025  
**Commit:** `018b721`

**Parts Completed:**

**Part A: Canonical Documentation to .ai/**
- Created .ai/README.md — index and navigation
- Created .ai/PROJECT_CONTEXT.md — what OneRing is, non-goals, stack, metrics
- Created .ai/ARCHITECTURE.md — detailed system design
- Created .ai/API_REFERENCE.md — endpoints, contracts, invariants
- Created .ai/TESTING.md — fast vs full gates, troubleshooting, patterns
- Created .ai/DECISIONS.md — architecture constraints and patterns
- Created .ai/PROJECT_STATE.md — this file, current status and counts
- Created .ai/CONTRIBUTIONS.md — contributor checklist
- Created .ai/PHASES/PHASE_8.md — Phase 8 rollup with shipped items, endpoints, invariants, testing guidance
- Created .ai/PHASES/ directory for phase organization
- Updated root README.md with banner pointing to .ai/ index
- Updated legacy /docs/ files with move notices (API_REFERENCE.md, ARCHITECTURE.md)

**Part B: Windows-Friendly Fast-Lane Testing**
- Created scripts/test_changed.py — Python helper to map changed files to backend/frontend tests
- Created scripts/vitest-changed.ps1 — PowerShell script to run changed-only vitest tests
- Created scripts/gate.ps1 — Two-stage gate: fast (changed-only) vs full (-Full flag)
- Extended package.json scripts:
  - `test:api` — Run backend tests
  - `test:api:changed` — Run only tests for changed backend files
  - `test:ui:changed` — Run only tests for changed frontend files
  - `gate` — Two-stage gate entry point (Windows-friendly)

**Part C: Agent Workflow Templates**
- Created .github/ISSUE_TEMPLATE/agent_tasks.md — Issue template for delegating agent tasks
- Created .ai/TASKS.md — Task conventions (fast-lane vs agent, definition of done)
- Created .ai/AGENT_BRIEF.md — Delegation brief template (objective, context, deliverables, acceptance, non-negotiables, reporting)
- Updated .github/copilot-instructions.md — Copilot/Grok/ChatGPT guidance with reference to .ai/ docs and new gate commands

**Impact:**
- Single source of truth for all documentation (live under .ai/)
- Fast test feedback loops for small changes (changed-only gates)
- Clear templates for delegating tasks to AI agents
- Reduced ambiguity in project state and decision history

### ✅ Phase 8.7.1b: LONG_RING_HOLD Alert Fix (Dec 14, 2025)
- `backend/features/collaboration/service.py` — Draft + ring logic
- `backend/features/insights/service.py` — Insights engine (deterministic, threshold-based)
- `backend/features/analytics/service.py` — Event reducers
- `backend/agents/langgraph/graph.py` — LangGraph orchestration
- `backend/tests/` — 618 tests (100% green)

**Key Invariants:**
- ✅ All alerts computed deterministically
- ✅ `ring_state.passed_at` always set (at draft creation or ring pass)
- ✅ Frozen Pydantic models (immutable, hashable, serializable)
- ✅ Optional `now` parameter for time-based queries (testing)

### Frontend
**Language:** TypeScript + React  
**Key Files:**
- `src/app/dashboard/page.tsx` — Main editor + insights
- `src/app/monitoring/page.tsx` — System health dashboard
- `src/components/InsightsPanel.tsx` — Insights UI + action callbacks
- `src/components/InsightsSummaryCard.tsx` — Lightweight insights for lists (NEW)
- `src/components/Toast.tsx` — Accessible notifications (NEW)
- `src/components/AnalyticsPanel.tsx` — Analytics charts + metrics
- `src/__tests__/` — 395 tests (100% green)

**Key Invariants:**
- ✅ Role-based selectors (accessible + stable)
- ✅ No flaky timeouts (use `waitFor()`)
- ✅ Mock external APIs consistently
- ✅ Use `act()` for state updates in tests
- ✅ No window.alert() (use Toast instead)

### Database
**PostgreSQL + pgvector**
- User profiles with embeddings
- Drafts + segments + ring state
- Analytics events + leaderboard
- All ACID transactions

---

## Recent Commits

| Commit | Date | What |
|--------|------|------|
| `d4a60b4` | Dec 25 | feat(phase8.9): production-ready insights UI + toast + summary cards |
| `018b721` | Dec 25 | docs(phase8.8): consolidate docs into .ai/ + fast gates |
| `ebd163d` | Dec 25 | fix(phase8.7.1b): compute LONG_RING_HOLD from current holder (zero passes) |
| (earlier) | Dec 25 | Phase 8.7 + 8.6 features |

---

## Known Limitations

| Issue | Workaround | Target Fix |
|-------|-----------|-----------|
| Insights queries slow at 100+ segments | Cache results | Phase 9 caching layer |
| No video support yet | Auto-generate in Phase 10 | Phase 10 |
| Polling latency ~500ms | Acceptable for MVP | WebSocket in Phase 9 (if needed) |

---

## Quality Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Test pass rate | 100% | 100% | ✅ |
| Skipped tests | 0 | 0 | ✅ |
| Code coverage | N/A (quality > %) | N/A | N/A |
| Avg response time | <200ms | ~50ms | ✅ |
| Test flakiness | 0% | 0% | ✅ |

---

## Deployment Readiness

- ✅ All tests green (1013 total)
- ✅ No security warnings (Dependabot clean)
- ✅ Windows + Linux compatible
- ✅ Docker images ready
- ✅ K8s manifests ready
- ✅ Monitoring dashboard live
- ✅ Error messages actionable
- ✅ Accessible UI (ARIA roles, Toast notifications)

**Ready for:** Production deployment or Phase 9 development.

---

## Next Steps

### Phase 10 (PLANNING COMPLETE — Ready for Execution Approval)

**⚠️ CRITICAL:** See [.ai/PHASE_10_MASTER_PLAN.md](.ai/PHASE_10_MASTER_PLAN.md) for comprehensive execution plan.

**Phase 10 Objective (One Sentence):**
Make OneRing defensible by enforcing agent workflows, activating minimal token economics with audit trails, and exposing controlled external APIs—without blockchain, speculation, or architectural drift.

---

### Phase 10.1 — Execution Approved Pending

- Status: Enforcement scaffolding in progress (feature-flagged, default off).
- Flags: `ONERING_ENFORCEMENT_MODE`, `ONERING_AUDIT_LOG`, `ONERING_TOKEN_ISSUANCE` (shadow only).
- Preflight Checklist:
  - Review [PHASE_10_1_EXECUTION_BACKLOG.md](PHASE_10_1_EXECUTION_BACKLOG.md) and confirm one-commit slices.
  - Review and accept [PHASE_10_DECISION_LOG.md](PHASE_10_DECISION_LOG.md) (Q1–Q4 locked: SLA, circuit breaker, telemetry retention, observability UX).
  - Confirm feature flag policy and rollout constraints in [DECISIONS.md](DECISIONS.md#phase-101--agent-enforcement-decisions-append-only).
  - Confirm API docs updated with Enforcement Metadata and error shapes (advisory mode first).
  - Verify kill-switch procedure documented (OFF revert) and `/monitoring` readiness.

**Sub-Phases:**

**Phase 10.1 — Agent-First Productization (3-4 weeks)**


**Phase 10.2 — Token Loop Activation (2-3 weeks)**
- **Objective:** Activate $RING economy with enforcement and audit trails
- **Key Changes:** RING deductions (-10 for failed posts), 1% monthly decay (>10K holdings), 1M lifetime cap, audit trail (PostgreSQL)
- **Success Criteria:** Audit reconciliation passes, <1% gaming attempts, sybil detection logging warnings
- **Entry Criteria:** 10.1 complete, agent telemetry logging RING awards
- **Status:** Publish-integrated (publish_events -> enforcement receipt -> ledger/pending); ledger-as-truth summary endpoint + spend/earn endpoints + clerk sync worker + backfill validator shipped

- **Exit Criteria:** 720+ backend tests passing, daily audit job operational

**Phase 10.3 — Platform / External Surface Area (4-5 weeks)**
- **Objective:** Expose controlled external APIs with security guarantees
- **Key Changes:** `/api/v1/external/*` (read-only), webhooks (HMAC-SHA256 signing), plugin sandbox, kill-switch
- **Success Criteria:** 3 external integrations built, webhook delivery >95%, zero security incidents (90 days)
- **Entry Criteria:** 10.2 complete, token loop stable, OAuth2 scopes defined
- **Exit Criteria:** 780+ backend tests passing, external API documented

**Total Phase 10 Duration:** 9-12 weeks (Q1 2026 estimate)

**Critical Path:** 9.6 (complete) → 10.1 (agents) → 10.2 (tokens) → 10.3 (APIs)

---

### Phase 10.1 Enforced Readiness
- References: [PHASE_10_1_POST_IMPLEMENTATION_AUDIT.md](PHASE_10_1_POST_IMPLEMENTATION_AUDIT.md), [PHASE_10_1_ENFORCED_READINESS_CHECKLIST.md](PHASE_10_1_ENFORCED_READINESS_CHECKLIST.md), [PHASE_10_1_EXECUTION_BACKLOG.md](PHASE_10_1_EXECUTION_BACKLOG.md)
- Status: Enforcement scaffold present behind `ONERING_ENFORCEMENT_MODE`/`ONERING_AUDIT_LOG`/`ONERING_TOKEN_ISSUANCE`; readiness tasks tracked in backlog slices.
- Current blockers: enforced rollout verification (metrics thresholds, ops runbook), cleanup dry-run validation.
- Observability + enforcement monitoring endpoints shipped; audit retention cleanup job added (dry-run default).

---

### Phase 10 Strategic Risks (Explicit)

**Agent-First Risks:**
- **Agent complexity increases debugging difficulty** — Mitigation: Comprehensive telemetry (workflow IDs, timing, failures logged)
- **Forced agent usage may slow experienced users** — Mitigation: Target p90 latency <2 seconds, circuit breakers for failures
- **Agent failures become blocking** — Mitigation: Circuit breakers return degraded content (no permanent blocks)

**Token Loop Risks:**
- **Gaming/exploitation attempts** — Mitigation: Rate limits (5/10/15 posts per 15min), sybil detection, Stripe verification gates
- **User confusion about RING value** — Mitigation: Clear disclaimers, TOS updates ("RING is not a cryptocurrency")
- **Regulatory scrutiny if RING perceived as security** — Mitigation: Explicit non-currency status, no USD conversion
- **RING inflation if award formula too generous** — Mitigation: 1M lifetime cap, 1% monthly decay (>10K holdings)

**External API Risks:**
- **API abuse or DDoS attacks** — Mitigation: Rate limits (100/hour free, 1000/hour paid), OAuth2 scoping, kill-switch
- **Third-party plugin security vulnerabilities** — Mitigation: Sandboxed execution (isolated FastAPI workers), manual approval queue
- **Scope creep into full platform features** — Mitigation: Strict non-goals list, timeline boundaries enforced
- **Maintenance burden of versioned APIs** — Mitigation: Limit API surface area, support v1 for 12 months post-v2

---

### Stable & Protected Architecture (No Changes in Phase 10)

| Component | Current Choice | Phase 10 Status | Rationale |
|-----------|---------------|----------------|-----------|
| **Auth** | Clerk | ✅ Protected | Best Next.js integration, metadata storage for RING |
| **LLM** | Groq (llama-3.1-8b-instant) | ✅ Protected | 10-20x faster, lower cost, prompts tuned for this model |
| **Backend** | FastAPI + LangGraph | ✅ Protected | Async support, Pydantic validation, simple agent chains |
| **Database** | PostgreSQL + pgvector | ✅ Protected | ACID transactions, pgvector for embeddings, open source |
| **Queues** | Redis + RQ | ✅ Protected | Simple Python interface, no message broker overhead |
| **Frontend** | Next.js 16 (App Router) | ✅ Protected | TypeScript, Clerk integration, streaming support |
| **Testing** | Vitest + Pytest | ✅ Protected | ESM-native, fast, all tests green always |
| **Deployment** | Docker + K8s ready | ✅ Protected | Local dev works, cloud-ready manifests exist |

**GREEN ALWAYS Policy:** Maintained throughout Phase 10. All sub-phases gate on tests passing (zero skipped, no `--no-verify` bypasses).

---

## Previous Phase: Phase 8.9 (Completed)

1. **Phase 8.9 (COMPLETE):**
   - Production-ready Insights UI ✅
   - Toast notifications + summary cards ✅
   - Commit + push ✅

2. **Phase 9.6 (COMPLETE):**
   - Governance, hooks, safety contracts ✅
   - Documentation standards locked ✅
   - Handoff Pack created ✅

3. **Phase 10 (PLANNED):**
   - See detailed breakdown above
   - Execution pending stakeholder approval

---

## How to Check Status

- **Test counts:** Top of this file
- **What's shipped:** Phase sections above
- **What to work on:** [.ai/TASKS.md](.ai/TASKS.md)
- **Why a design:** [.ai/DECISIONS.md](.ai/DECISIONS.md)
- **How to test:** [.ai/TESTING.md](.ai/TESTING.md)

---

## Next Session Start Checklist

- Review [.ai/HANDOFF_PACK/README.md](HANDOFF_PACK/README.md) and scan 20 docs
- Confirm hooks are disabled by default; enable only with `ONERING_HOOKS=1` and `ONERING_GATE=docs`
- Docs-only changes: run `pnpm gate --mode docs` before commit
- One commit max; no push unless explicitly requested
