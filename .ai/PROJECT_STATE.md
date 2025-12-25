# Project State (Canonical)

**Last Updated:** December 25, 2025  
**Status:** Phase 8.8 COMPLETE. All tests passing (617 backend + 388 frontend = 1005 total).

## Test Coverage

| Metric | Count | Status |
|--------|-------|--------|
| Backend Tests | 617/617 | ✅ 100% |
| Frontend Tests | 388/388 | ✅ 100% |
| **Total** | **1005/1005** | ✅ **100%** |
| Skipped | 0 | ✅ ZERO |
| --no-verify bypasses | 0 | ✅ ZERO |

**Last Full Run:** December 25, 2025 @ 11:30 UTC  
**Duration:** ~2.5 minutes (sequential: backend ~2 min + frontend ~8 sec)

## Current Phase Status

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
- `backend/tests/` — 617 tests (100% green)

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
- `src/components/AnalyticsPanel.tsx` — Analytics charts + metrics
- `src/__tests__/` — 388 tests (100% green)

**Key Invariants:**
- ✅ Role-based selectors (accessible + stable)
- ✅ No flaky timeouts (use `waitFor()`)
- ✅ Mock external APIs consistently
- ✅ Use `act()` for state updates in tests

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
| `6d72fa4` | Dec 25 | docs(phase8.7.1b): add completion docs + update PROJECT_STATE |
| `c405a29` | Dec 25 | fix(phase8.7.1b): compute LONG_RING_HOLD from current holder (zero passes) |
| (earlier) | Dec 25 | Phase 8.7.1 + 8.7 + 8.6 features |

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

- ✅ All tests green
- ✅ No security warnings (Dependabot clean)
- ✅ Windows + Linux compatible
- ✅ Docker images ready
- ✅ K8s manifests ready
- ✅ Monitoring dashboard live
- ✅ Error messages actionable

**Ready for:** Production deployment or Phase 9 development.

---

## Next Steps

1. **Phase 8.8 (CURRENT):**
   - Consolidate docs into `.ai/` (canonical single source)
   - Add fast gates + full gates scripts
   - Add agent briefs + task templates
   - Commit + push

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
