# Domain — Streaks

## Concept Definition
Streaks represent consecutive days of meaningful creative actions (posting, challenge completion, drafting with coach).

## Core Entities
- Streak: userId, length, lastActionAt, protectionWindowEndsAt
- StreakEvent: userId, type (start, continue, protect, break, resetPartial), timestamp

## Example State Transitions
- start -> continue -> continue -> protect -> continue
- continue -> break -> resetPartial (reduce length by N, not zero)
- protect window prevents break if action occurs within mercy period

## Metrics Involved
- Streak length
- Protection usage rate
- Recovery time after break

## Backend Systems
- Posting endpoints increment streaks
- Challenges service awards streak continuation
- Analytics records streak events for dashboards and momentum scoring
