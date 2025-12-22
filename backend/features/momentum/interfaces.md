# Interfaces — Momentum (Conceptual)

## Inputs
- ComponentScores: { streaks, challenges, resonance, lineage, consistency }

## Outputs
- MomentumScore: { total, components, updatedAt }
- MomentumEvent: { userId, type, delta, reason }

## Notes
- Deterministic reducers; idempotent event writes
- No side effects in request handlers
