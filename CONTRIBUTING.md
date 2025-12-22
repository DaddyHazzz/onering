## Phase 1 Focus
- Core loop: Creator Streaks, Daily Challenges, AI Post Coach.
- Every feature must answer “Why today?” and reinforce daily momentum.

## Event & Guardrail Requirements
- New features must emit events (see .ai/events.md) and define invariants.
- Add at least one guardrail test (xfail/skip allowed) describing intended behavior.
- Do not introduce side effects in request handlers; mutations must be idempotent.
