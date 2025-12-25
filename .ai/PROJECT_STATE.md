# Project State (Canonical)

**Last Updated:** December 25, 2025 @ 11:48 UTC  
**Status:** Phase 8.9 COMPLETE. All tests passing (618 backend + 395 frontend = 1013 total).

## Test Coverage

| Metric | Count | Status |
|--------|-------|--------|
| Backend Tests | 618/618 | ✅ 100% |
| Frontend Tests | 395/395 | ✅ 100% |
| **Total** | **1013/1013** | ✅ **100%** |
| Skipped | 0 | ✅ ZERO |
| --no-verify bypasses | 0 | ✅ ZERO |

**Last Full Run:** December 25, 2025 @ 11:48 UTC  
**Duration:** ~2.5 minutes (sequential: backend ~2m 53s + frontend ~7s)

## Current Phase Status

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

1. **Phase 8.9 (COMPLETE):**
   - Production-ready Insights UI ✅
   - Toast notifications + summary cards ✅
   - Commit + push ✅

2. **Phase 9 (PLANNED):**
   - ML-based recommendations
   - Cohort analysis
   - Predictive alerts
   - User preferences

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
