# Phase 8 — Consolidation, Insights Hardening, Fast Gates

Status: Complete through 8.7.1b, in-progress for 8.8

## What Shipped
- 8.6 Analytics: Event store + reducers (deterministic, idempotent)
- 8.7 Insights: LONG_RING_HOLD fixed to use current holder duration
- 8.7.1b: Zero ring passes edge case handled; all tests green
- 8.8-A: Canonical documentation under .ai/ established

## Endpoints & Contracts
- Insights: GET /api/insights/drafts/{id}?now=ISO
  - Alerts include LONG_RING_HOLD, NO_ACTIVITY; reasons are canonical
- Analytics: GET /api/collab/drafts/{id}/analytics, GET /v1/analytics/leaderboard
- Generation: POST /v1/generate/content/ (SSE)
- Posting: POST /api/post-to-x (rate-limited)

## Invariants
- Deterministic testing via explicit `now` parameter
- No averaging for alert thresholds; rely on current state
- Alert schema uses `reason` (tests must assert on `reason`)

## How To Test
- Backend: `pytest -q` (Windows friendly)
- Frontend: `pnpm test` or `pnpm test:ui --run`
- Full gates: backend + frontend must both report green; zero skipped

## Notes
- Docs moved to .ai/; legacy docs/ left as pointers
- Windows PowerShell scripts provide fast lanes for changed tests (8.8-B)
