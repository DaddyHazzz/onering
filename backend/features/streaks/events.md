# Streak Events

## Advance Streak
- post.posted → increment (once per user per day)
- challenge.completed (full/partial) → increment (once per user per day)

## Threaten Streak
- streak.missed emitted when day ends with no qualifying action and no protection used.
- Scheduled-only does not advance; absence triggers missed if day passes.

## Never Breaks a Streak
- Failed post attempts
- Draft generation or coach feedback alone
- Scheduled but not yet posted
