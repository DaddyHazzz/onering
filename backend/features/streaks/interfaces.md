# Interfaces — Streaks (Conceptual)

## Inputs
- userId: string
- actionType: 'post' | 'challengeComplete'
- timestamp: ISO string

## Outputs
- StreakEvent: { userId, type, timestamp }
- StreakState: { length, lastActionAt, protectionWindowEndsAt }

## Notes
- Idempotent write boundaries; dedupe on (userId, day)
- Do not mutate within request handlers; call streak service
