# Project State (Canonical)

**Last Updated:** December 25, 2025  
**Status:** Phase 8.7.1b COMPLETE. Phase 8.8 IN PROGRESS (Docs consolidation + fast gates).

## Test Coverage

| Metric | Count | Status |
|--------|-------|--------|
| Backend Tests | 617/617 | ✅ 100% |
| Frontend Tests | 388/388 | ✅ 100% |
| **Total** | **1005/1005** | ✅ **100%** |
| Skipped | 0 | ✅ ZERO |
| --no-verify bypasses | 0 | ✅ ZERO |

**Last Full Run:** December 25, 2025 @ 10:00 UTC  
**Duration:** ~2.5 minutes (sequential: backend ~2 min + frontend ~8 sec)

## Current Phase Status

### ✅ Phase 8.7.1b: LONG_RING_HOLD Alert Fix
**Shipped:** December 25, 2025  
**Commit:** `c405a29` (fix), `6d72fa4` (docs)

**Problem:** Alert computed from average hold time (None with zero ring passes) → edge case failed.  
**Solution:** Use current holder's actual hold time from `ring_state.passed_at`.  
**Impact:** Catches stuck drafts even when ring never passed.

**Test Results:**
- `test_alerts_no_activity_and_long_hold` — now PASSING
- All 6 insights API tests green
- No test weakening, no assertions deleted

### ⏳ Phase 8.8: Docs Consolidation + Fast Gates + Agent Workflow
**Status:** IN PROGRESS  
**Target:** December 25, 2025 (today)

**Parts:**
- A (DOCS): Consolidate into `.ai/` → IN PROGRESS
- B (GATES): Add fast/full gate scripts → PENDING
- C (AGENTS): Add briefs + task templates → PENDING

---

## Code Snapshot

### Backend
**Language:** Python 3.10+  
**Key Files:**
- `backend/main.py` — FastAPI app
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
