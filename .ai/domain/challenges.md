# Domain — Challenges

## Concept Definition
Daily/weekly tasks tailored to creator goals; designed to be attainable and momentum-building.

## Core Entities
- Challenge: id, title, description, difficulty, duration, rewardRing
- ChallengeAssignment: userId, challengeId, assignedAt, dueAt, status
- ChallengeAttempt: userId, challengeId, submittedAt, status, notes

## Example State Transitions
- assigned -> started -> submitted -> completed
- assigned -> missed -> partialCredit
- completed -> claimedReward (RING)

## Metrics Involved
- Completion rate
- Time-to-start
- Partial credits ratio

## Backend Systems
- Temporal workflows schedule assignments and reminders
- RQ jobs handle retries and notifications
- Analytics aggregates completion and participation metrics
