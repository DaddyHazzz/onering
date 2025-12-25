# Phase 8 — Consolidation, Insights Hardening, Fast Gates

Status: Complete through 8.9

## What Shipped
- 8.6 Analytics: Event store + reducers (deterministic, idempotent)
- 8.7 Insights: LONG_RING_HOLD fixed to use current holder duration
- 8.7.1b: Zero ring passes edge case handled; all tests green
- 8.8: Canonical documentation under .ai/ established
- 8.9: Production-ready Insights UI + actionable recommendations

## Phase 8.9 Details (Dec 25, 2025)
**Backend:**
- Insights API fully contract-compliant (.ai/API_REFERENCE.md)
- All alerts deterministic, thresholds verified
- LONG_RING_HOLD uses ring_state.passed_at (works with zero passes)

**Frontend:**
- InsightsPanel: Removed window.alert(), now uses Toast notifications
- InsightsSummaryCard: Lightweight summary for draft lists
- Tab accessibility verified (role/aria-controls/aria-labelledby)

**Tests:**
- Backend: 6 insights integration tests (stalled, dominant, healthy, alerts, 403, determinism)
- Frontend: 12 insights tests + new Toast verification + InsightsSummaryCard tests

## Endpoints & Contracts
- Insights: GET /api/insights/drafts/{id}?now=ISO
  - Alerts: LONG_RING_HOLD, NO_ACTIVITY, SINGLE_CONTRIBUTOR
  - Recommendations: pass_ring, invite_user
  - Response includes reasons for explainability

## Invariants
- Deterministic testing via explicit `now` parameter
- No window.alert() — use Toast for user feedback
- Alert schema uses `reason` (not message)
- Access: collaborator-only (403 if not)

## How To Test
- Backend: `pytest -q` (Windows friendly)
- Frontend: `pnpm test` or `pnpm test:ui --run`
- Full gates: backend + frontend must both report green; zero skipped

## Notes
- Docs moved to .ai/; legacy docs/ left as pointers
- Windows PowerShell scripts provide fast lanes for changed tests (8.8-B)
