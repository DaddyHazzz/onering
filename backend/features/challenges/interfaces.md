# Interfaces — Challenges (Conceptual)

## Inputs
- userId: string
- challengeId: string
- submission: { contentRef, timestamp }

## Outputs
- ChallengeAssignment: { userId, challengeId, dueAt }
- ChallengeResult: { status: 'completed' | 'missed' | 'partial', rewardRing? }

## Notes
- Use Temporal for retries and windows; RQ for notifications
- Idempotent reward issuance
