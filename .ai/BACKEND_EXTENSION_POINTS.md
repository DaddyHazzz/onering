# Backend Extension Points

## Streak Logic Hooks
- Hook into posting endpoints after successful publish to record streak continuation.
- Respect mercy mechanics (protection windows) and partial resets.
- Implement via dedicated streak service; do not mutate streaks inside request handlers.

## Analytics → Momentum Aggregation
- Analytics reducers emit component scores (streaks, challenges, resonance, lineage, consistency).
- Momentum service recomputes daily and writes idempotent events.
- Expose read models for dashboards; keep writes transactional and deterministic.

## Temporal Workflows (Challenges, Events, Retries)
- Schedule challenge assignments and reminders.
- Orchestrate event windows, participation verification, and reward issuance.
- Use stable idempotency keys for retries; wrap RQ job IDs to prevent duplication.

## Extending RQ Jobs Safely
- Enqueue jobs with explicit `job_id` and result TTLs.
- Make handlers idempotent; guard against double execution.
- Separate side effects (DB writes, external posts) behind service boundaries.

## Preserving Determinism
- Do not introduce side effects in request handlers.
- All progress-related mutations must be idempotent.
- Prefer explicit, small helpers over implicit global state.
- Record events with stable keys; dedupe at write boundaries.
