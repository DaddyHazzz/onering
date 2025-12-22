# Backend Feature — Momentum Score

**Status:** Production-ready v1 (Phase 2 core feature).

## Overview

Momentum Score answers: **"Am I gaining or losing momentum this week?"**

It is NOT:
- Raw engagement metrics (likes, followers)
- Clickbait optimization advice
- A punitive scorecard

It IS:
- A stable, interpretable score (0..100)
- Derived from streak health, daily completion, consistency, and coach engagement
- A mirror that reflects your actual progress
- Deterministic and timezone-aware (UTC)

**Key Philosophy:** Momentum beats likes. Momentum is the unfolding of creative identity over time, not viral spikes.

## Scoring Formula

**Base Score:** 50 (neutral starting point)

**Components (additive, clamped at component max):**
- **Streak Health** (0..25): Current streak / benchmark streak × 25
  - Reflects consistency and habit formation
  - Benchmark: 30 days = 25 points

- **Challenge Completion** (0 or 15): Did you complete today's challenge?
  - Shows commitment and clear direction
  - Binary: full or nothing (no partial credit)

- **Consistency** (0..10): Posts this week / target posts per week × 10
  - Rewards regular output (at least a few per week)
  - Lightweight platform differentiation

- **Coach Engagement** (0..10): Coach feedback requests this week
  - Rewards intentional improvement
  - 4+ requests = max points (diminishing returns)

**Final Calculation:**
```
raw_score = 50 + streak + challenge + consistency + coach
final_score = clamp(raw_score, 0, 100)
```

**Hard Guarantees:**
- Score always 0..100 (clamped)
- Single event cannot swing score >15 points (stability)
- Missing data treated optimistically (not as 0)
- No randomness; deterministic always

## Trend Calculation

Compares today's score to 7-day rolling average:
- **Up:** current ≥ avg + 5
- **Down:** current ≤ avg - 5
- **Flat:** within 5 points of average
- **Insufficient History:** default to "flat"

## Trend Example

```
Previous 7 days: [45, 48, 50, 52, 51, 49, 50]
Average: 49.3

Today's score 55 => TREND UP (exceeds avg by 5.7)
Today's score 50 => TREND FLAT (within 5 of avg)
Today's score 44 => TREND DOWN (below avg by 5.3)
```

## Next Action Hints

Generated dynamically based on score and context. Examples:

**High momentum (≥80):**
- "You're in flow. Keep riding this wave today."
- "Strong week. Complete today's challenge to cap it off."

**Medium momentum (60-80):**
- "Solid momentum. Try getting coach feedback on your next draft."
- "You're steady. One more push today locks in progress."

**Recovering (40-60):**
- "Room to grow. Complete today's challenge for momentum."
- "Good start. Check coach feedback next time for polish."

**Low momentum (<40):**
- "Momentum is dipping. Post something small today to rebuild."
- "Building back up. A small post today counts."

**Guardrail:** Never use shame words (bad, wrong, fail, stupid, terrible, useless). Always point to next step.

## API Endpoints

### GET /v1/momentum/today
Get today's momentum snapshot.

**Query:** `user_id=...` (Clerk user ID)

**Response:**
```json
{
  "data": {
    "userId": "user_...",
    "date": "2025-12-21",
    "score": 75.5,
    "trend": "up",
    "components": {
      "streakComponent": 20.0,
      "consistencyComponent": 10.0,
      "challengeComponent": 15.0,
      "coachComponent": 5.0
    },
    "nextActionHint": "You're in flow. Keep riding this wave today.",
    "computedAt": "2025-12-21T14:30:00+00:00"
  }
}
```

### GET /v1/momentum/weekly
Get last 7 days of momentum (most recent first).

**Query:** `user_id=...`

**Response:**
```json
{
  "data": [
    { snapshot for today },
    { snapshot for yesterday },
    ...
    { snapshot for 6 days ago }
  ]
}
```

## Input Adapters

Momentum reads from existing systems (gracefully handle missing data):

**Streak System:**
- Current streak length
- Max benchmark (default 30)

**Challenge System:**
- Was today's challenge completed?

**Analytics / Posts:**
- Posts in last 7 days
- Coach feedback requests this week

**Fallbacks:**
- No streak → assume 0
- No challenge data → assume not completed
- No post history → assume 0 posts
- Missing previous scores → trend = "flat"

## Testing

All 22 guardrail tests passing:
- ✅ Determinism: identical inputs => identical output
- ✅ Stability: single event ≤ 15 point swing
- ✅ Missing data: score never 0, always actionable hint
- ✅ Component influences: each contributor impacts score correctly
- ✅ Clamping: score always 0..100
- ✅ Trend calculation: accurate vs rolling average
- ✅ Action hints: never shameful, always actionable
- ✅ Validation: snapshots serialize and validate properly

**Run:**
```bash
python -m pytest backend/tests/test_momentum_guardrails.py -v
```

## Design Decisions

### Why Deterministic, Not ML?
- Transparency: users understand where their score comes from
- Stability: no wild swings from opaque model training
- No API costs or latency
- Reproducible and auditable
- Foundation for future LLM-enhanced variants

### Why These 4 Components?
- **Streak:** Habit formation (the foundation)
- **Challenge:** Daily ritual and direction (the routine)
- **Consistency:** Sustainable pace (not viral bursts)
- **Coach:** Intentional improvement (the growth loop)
Together they form the daily pull loop.

### Why Base 50, Not 0?
- Neutral starting point acknowledges effort
- 0 feels punitive; 50 feels fair
- Room to grow up or down

### Why Trend as "Rolling Average"?
- Smooths out daily noise
- 7 days = one week (natural period)
- Thresholds (±5) prevent false positives

## Future Enhancements

### Real-Time Momentum (Streaming)
Recompute momentum as the user posts/completes challenges in real-time.

### Momentum Triggers
"Momentum >= 80" unlocks early access to features or RING bonuses.

### Archetype Alignment
Factor in archetype (e.g., Creator, Analyst, Coach) to personalize component weights.

### Historical Snapshots
Store MomentumSnapshot in DB for analytics and replays.

## No Further Action Needed

Momentum v1 is production-ready. Phase 2 continues with:
1. Momentum Score ✅
2. Public Profiles (next)
3. Archetypes & Personalization (future)

---

**Implementation:** Pure deterministic engine; no external APIs. 22 tests passing. Ready for frontend UI integration.
