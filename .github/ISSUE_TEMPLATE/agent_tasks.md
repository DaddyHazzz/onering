# OneRing — Issue Template for Agent Tasks

Use this template when creating tasks for AI agents (Copilot, Grok, ChatGPT, etc.).

---

## Title
[Clear, 5–10 word description of objective]

Example: "Fix LONG_RING_HOLD alert with zero ring passes edge case"

## Objective
State what outcome is required. Include success criteria and non-negotiables.

Example:
- Fix alert logic to handle drafts with zero ring passes (no averages)
- All tests must pass (backend + frontend), zero skipped
- No `--no-verify` commits

## Context
Link to relevant architecture, prior phases, codebase areas.

Example:
- See .ai/ARCHITECTURE.md for insights system overview
- Phase 8.7 introduced LONG_RING_HOLD alert; Phase 8.7.1 is hardening
- Key files: backend/features/insights/service.py, src/__tests__/insights-panel.spec.tsx

## Deliverables
- Code changes (files, modules affected)
- Tests (unit, integration, UI)
- Docs updates (if behavior or contracts changed)

Example:
- backend/features/insights/service.py: Switch to current holder duration
- backend/tests/test_insights_api.py: Update assertions to use alert.reason
- src/__tests__/insights-panel.spec.tsx: Add mock onSmartPass callback

## Acceptance Tests
Explicit steps and expected outputs. Use deterministic inputs (`now` param for time-based tests).

Example:
- Scenario 1: Draft with zero passes, 25h hold → LONG_RING_HOLD triggered
- Scenario 2: Draft with three passes, avg 20h → no alert (not using average)
- Run `pnpm test:api` and `pnpm test:ui:changed` — all green

## Non-Negotiables
✅ All tests GREEN (backend + frontend), zero skipped, no `--no-verify`
✅ Windows-friendly scripts
✅ Preserve architecture decisions (see .ai/DECISIONS.md)

## Reporting
Provide summary: what changed, why, where. Update .ai/PROJECT_STATE.md.

Example:
- Fixed LONG_RING_HOLD to use current holder duration (ring_state.passed_at)
- Updated 2 backend tests, 1 frontend test
- All tests green (618 backend, 400 frontend)
- See PHASE8_7_1_COMPLETE.md for details
