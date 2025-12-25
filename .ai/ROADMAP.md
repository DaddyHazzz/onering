
Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# OneRing Roadmap — Feature Tiers

## Tier 1 — Daily Pull (Addiction)
### Creator Streaks
- Behavior: Tracks consecutive days of meaningful creative actions; offers streak protection windows and partial resets.
- Pull: Daily commitment builds identity; breaking a streak matters emotionally.
- Systems: Streak service, posting endpoints, analytics events, RING awards.

### AI Post Coach
- Behavior: Context-aware guidance on clarity, tone, and audience fit; provides small nudges, not rewrites.
- Pull: Immediate, supportive feedback increases confidence and reduces friction.
- Systems: Generation context, archetypes, momentum scoring, values mode.

### Daily Challenges
- Behavior: Lightweight tasks tailored to creator goals (e.g., "Ship one insight in 4 lines").
- Pull: Specific, achievable prompts make showing up easy; completion fuels momentum.
- Systems: Temporal workflows for scheduling/chaining, RQ for reminders, analytics for completion.

## Tier 2 — Identity & Status
### Public Creator Profiles
- Behavior: Shareable pages showing momentum graphs, streaks, and recent content aligned to archetype.
- Pull: Status signaling and identity reflection attract peers and audience.
- Systems: Analytics aggregation, embeddings, RING stats, posting history.

### Creator Archetypes
- Behavior: Personality frameworks that shape prompts and feedback; user selects or evolves archetype.
- Pull: Identity scaffolding increases meaning and self-recognition.
- Systems: Archetype domain, AI coach tone, values mode constraints.

### Momentum Score
- Behavior: Composite score from streaks, challenge completion, content resonance, and lineage.
- Pull: Simple metric representing progress over time encourages ongoing effort.
- Systems: Analytics reducers, scoring service, RING bonuses.

## Tier 3 — Network Effects & Rewards
### Collaborative Threads
- Behavior: Co-authored threads with attribution and shared momentum gains.
- Pull: Social creation increases accountability and reach.
- Systems: Collaboration domain, posting router, lineage tracking.

### Content Lineage
- Behavior: Track how ideas evolve across posts, threads, and collaborators.
- Pull: Seeing the story of ideas deepens attachment and pride.
- Systems: Lineage domain, embeddings, analytics events.

### Ring Drops (Events)
- Behavior: Time-bound events that award RING for participation and completion.
- Pull: Scarcity and communal participation drive action.
- Systems: Events domain, Temporal workflows, RQ jobs, payments.

## Tier 4 — Press-Worthy Experiments
### Audience Simulator
- Behavior: Simulate target audience reactions to draft content using archetype-conditioned models.
- Pull: Safe practice grounds reduce fear and sharpen messaging.
- Systems: Generation + archetypes, analytics capture, coach feedback.

### Post Autopsy AI
- Behavior: Explain why a post worked or didn’t—structure, clarity, resonance—then suggest next steps.
- Pull: Narrative feedback turns outcomes into learning, fueling momentum.
- Systems: Analytics signals, embeddings, AI coach, lineage.

### Values Mode
- Behavior: Constrain prompts and output to user-defined values; filters tone and topics to align with identity.
- Pull: Integrity and alignment increase trust and consistency.
- Systems: Archetypes, AI behavior constraints, generation guardrails.

