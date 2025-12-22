# Domain — Momentum

## Concept Definition
Composite measure of creator progress over time: streaks, challenges, resonance, lineage, and consistency.

## Core Entities
- MomentumScore: userId, components {streaks, challenges, resonance, lineage, consistency}, total, updatedAt
- MomentumEvent: userId, type, delta, reason, timestamp

## Example State Transitions
- score recomputed daily from components
- events apply deltas with idempotency to prevent duplication

## Metrics Involved
- Component weights and stability
- Day-over-day delta

## Backend Systems
- Analytics reducers feed components
- Posting and challenges emit events
- RING rewards triggered by thresholds
