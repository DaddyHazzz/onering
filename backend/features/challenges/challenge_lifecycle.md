# Challenge Lifecycle
- Assignment: user receives a challenge (type: creative, reflective, engagement, growth) with dueAt.
- Acceptance: user acknowledges; optional step.
- Completion: submission evaluated (full/partial) and emits challenge.completed.
- Expiration: dueAt passed without completion → missed; may issue recovery prompt.

Decision Fatigue Reduction
- Offer a single, tailored challenge per day.
- Defaults minimize choice while preserving agency (skip/replace limited).

Feeds Streaks
- challenge.completed can increment streaks (once per day).
- Expiration may threaten streak via streak.missed if no other action.

Interact with Post Coach
- Coach feedback can be requested during challenge drafting.
- Coach suggestions align with challenge intent and archetype.
