# Archetypes Feature

**Phase 2 Feature #3** — Deterministic creator personality classification based on behavior and content patterns.

## Purpose
Archetypes give creators a mirror that shows **who they're becoming**, not who they wish they were. The system observes signals from Coach feedback, Challenge choices, and post patterns to classify creators into 6 evolving archetypes.

This is **soft guidance, not destiny**. Archetypes influence Coach suggestions and Challenge selection **without locking users in** or making them feel judged.

## Design Philosophy
1. **Supportive, never shame**: Explanations are positive and growth-focused.
2. **Deterministic stability**: Large score gaps resist flipping. Merging uses decay (0.92) to smooth volatility.
3. **No external dependencies**: Works entirely offline, no LLM required for classification.
4. **Idempotent signal recording**: Duplicate signals (same hash) are ignored.
5. **Public safety**: Only safe fields (primary, secondary, explanation, updatedAt) are exposed publicly.

## The 6 Archetypes

| Archetype     | Icon | Keywords (Examples) | Core Trait |
|---------------|------|---------------------|------------|
| **truth_teller** | 🎯 | honest, brutal, real, facts | Direct, no-BS communicator |
| **builder** | 🔨 | shipped, built, launched, deployed | Execution-focused maker |
| **philosopher** | 💭 | ponder, reflect, consider, nuance | Deep thinker, explores ideas |
| **connector** | 🤝 | community, collaborate, together | Relationship-driven |
| **firestarter** | 🔥 | disrupt, challenge, question | Provocateur, catalyst |
| **storyteller** | 📖 | vivid, scene, narrative, journey | Rich narrative style |

## Scoring Algorithm

### 1. Text Scoring (`score_from_text`)
- Scans text for archetype keywords (case-insensitive).
- Base score: +10 per keyword match.
- Platform multipliers:
  - Twitter: 1.2x (short-form bias)
  - Coach feedback: 1.5x (deliberate reflection)
- **Clamped to 0..100**.

### 2. Coach Feedback Scoring (`score_from_coach_feedback`)
- Converts Coach scores to archetype boosts:
  - **execution_bias** (>0) → builder +20
  - **reflection_bias** (>0) → philosopher +20
  - **directness_score** (>0.5) → truth_teller +15
- If suggestions contain "community", "engage" → connector +10.
- **Clamped to 0..100**.

### 3. Challenge Scoring (`score_from_challenge_type`)
- Maps challenge types to archetypes:
  - `growth` → builder +15
  - `reflective` → philosopher +15
  - `engagement` → connector +15
  - `creative` → storyteller +15

### 4. Score Merging (`merge_scores`)
- Combines new scores with existing snapshot using **decay factor 0.92**:
  ```
  merged[archetype] = (old_score * 0.92) + (new_score * 0.08)
  ```
- Smooths volatility, prevents instant flips.
- **Clamped to 0..100**.

### 5. Primary/Secondary Selection (`pick_primary_secondary`)
- **Primary**: Highest score.
- **Secondary**: Second-highest **only if within 15 points** of primary.
  - Large gaps → no secondary (user is clearly one archetype).
  - Close scores → secondary shown (user is blending styles).

### 6. Explanation Generation (`explain`)
- 3 supportive bullets, no shame words.
- Banned words: "lack", "fail", "stuck", "mediocre", "weak", "poor", "shame".
- Templates per archetype (deterministic from user_id seed):
  - **builder**: "You ship consistently", "bias toward execution", "building momentum"
  - **philosopher**: "You explore ideas", "patience with nuance", "depth-first thinker"
  - Etc. (see `engine.py` for full templates).

## Data Models

### ArchetypeSignal (Input)
```python
class ArchetypeSignal(BaseModel):
    source: str  # "coach", "challenge", "post"
    date: str    # ISO 8601 date (for idempotency)
    payload: dict  # source-specific data
```

### ArchetypeSnapshot (Output)
```python
@dataclass(frozen=True)
class ArchetypeSnapshot:
    user_id: str
    primary: ArchetypeId
    secondary: ArchetypeId | None
    scores: dict[ArchetypeId, float]  # 0..100 each
    explanation: list[str]  # 3 bullets
    updated_at: str  # ISO 8601 timestamp
    version: int  # increment on each update

    def to_public_dict(self) -> dict:
        """Safe subset for public profiles (no scores)."""
        return {
            "userId": self.user_id,
            "primary": self.primary,
            "secondary": self.secondary,
            "explanation": self.explanation,
            "updatedAt": self.updated_at,
        }
```

## Service Layer

### In-Memory Storage
- `_snapshots: dict[str, ArchetypeSnapshot]` — Latest snapshot per user.
- `_applied_signals: set[str]` — Signal hashes for idempotency.

### Public Methods

#### `get_snapshot(user_id: str) -> ArchetypeSnapshot`
Returns existing snapshot or computes **deterministic initial** from user_id hash.

Initial snapshot (if no signals yet):
- Hash user_id → seed → rotate top 2 archetypes as primary/secondary.
- Scores: primary=75, secondary=65, rest=50.
- Generic explanation: "Early days, still learning your style."

#### `record_signal(user_id: str, signal: ArchetypeSignal) -> ArchetypeSnapshot`
1. Compute signal hash: `hash(user_id + signal.source + signal.date + json(payload))`.
2. If hash in `_applied_signals`, return existing snapshot (idempotent).
3. Else:
   - Fetch existing snapshot.
   - Score new signal (`score_from_text`, `score_from_coach_feedback`, or `score_from_challenge_type`).
   - Merge scores with decay=0.92.
   - Pick primary/secondary.
   - Generate explanation.
   - Increment version.
   - Store snapshot.
   - Emit event: `"archetype_updated"`.
4. Return new snapshot.

#### `recompute_today(user_id: str) -> ArchetypeSnapshot`
Recomputes snapshot from all signals **for today** (for manual refresh or admin tools).

## Integration Points

### Coach Suggestions (`backend/features/coach/service.py`)
Coach calls `archetype_service.get_snapshot(user_id)` before generating feedback.

Tone influence (`_archetype_inflect_suggestions`):
- **builder**: "Consider" → "Try", "could" → "should" (more directive).
- **philosopher**: "Add" → "Consider adding", "Try" → "Reflect on" (softer, exploratory).
- **connector**: statements → questions ("What if you...?").
- **truth_teller**: "might" → "should", more direct.
- **firestarter**: "Consider" → "Push further" (more aggressive).
- **storyteller**: "Add details" → "Paint the scene" (more vivid).

**Preserves determinism**: Archetype influences tone, not content. Same inputs → same suggestions.

### Challenge Selection (`backend/features/challenges/service.py`)
Challenge service calls `archetype_service.get_snapshot(user_id)` before assigning today's challenge.

Preference mapping (`_deterministic_index_with_archetype`):
- **builder** → filters catalog to "growth" challenges.
- **philosopher** → filters to "reflective" challenges.
- **connector** → filters to "engagement" challenges.
- **truth_teller, firestarter, storyteller** → filters to "creative" challenges.

If filtered subset is empty, falls back to full catalog.

Final selection: `hash(user_id + date + archetype) % len(filtered_catalog)` → deterministic.

## API Endpoints

### `GET /v1/archetypes/me?user_id=<id>`
Returns full snapshot (including scores).

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "primary": "builder",
    "secondary": "philosopher",
    "scores": {
      "builder": 75.0,
      "philosopher": 65.0,
      "truth_teller": 50.0,
      "connector": 50.0,
      "firestarter": 45.0,
      "storyteller": 50.0
    },
    "explanation": [
      "You ship consistently and focus on actionable outcomes.",
      "Your work shows a bias toward execution over theory.",
      "You're building momentum through tangible progress."
    ],
    "updated_at": "2025-12-21T10:30:00Z",
    "version": 5
  }
}
```

### `POST /v1/archetypes/signal`
Records a behavioral signal (idempotent).

**Request:**
```json
{
  "user_id": "user_123",
  "source": "coach",
  "date": "2025-12-21",
  "payload": {
    "execution_bias": 0.8,
    "reflection_bias": 0.2
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "archetype updated"
}
```

### `GET /v1/archetypes/public?user_id=<id>`
Returns safe public subset (no scores, no payload).

**Response:**
```json
{
  "success": true,
  "data": {
    "userId": "user_123",
    "primary": "builder",
    "secondary": "philosopher",
    "explanation": [
      "You ship consistently.",
      "Your work shows execution focus.",
      "You're building momentum."
    ],
    "updatedAt": "2025-12-21T10:30:00Z"
  }
}
```

## Frontend Integration

### Dashboard Card (`src/components/ArchetypeCard.tsx`)
- Fetches `/api/archetypes/me` (Clerk auth required).
- Displays primary + secondary archetype with icon.
- Shows 3-bullet explanation.
- Note: "Updates over time as you create and engage."

### Public Profile (`src/app/u/[handle]/page.tsx`)
- Profile API includes `archetype` field (optional).
- If present, displays archetype card with icon + explanation.
- No scores shown (public safety).

## Testing

### Backend Tests (`backend/tests/test_archetype_guardrails.py`)
24 test cases across 9 test classes:
1. **Determinism**: Same signal twice → same output, same merge → same scores.
2. **Stability**: Large gaps resist flipping, decay preserves history.
3. **Clamping**: Text scores clamped 0..100, merge scores clamped 0..100.
4. **Explanation**: 3 bullets, no shame words, non-empty.
5. **Public Safety**: `to_public_dict` excludes scores, no payload leaks.
6. **Coach Integration**: Archetype influences suggestion tone without breaking determinism.
7. **Challenge Integration**: Archetype weights challenge type selection deterministically.
8. **Pick Logic**: Secondary only if within 15 points, no secondary if large gap.
9. **Keyword Scoring**: Builder keywords → builder boost, philosopher keywords → philosopher boost.

### Frontend Tests (`src/__tests__/archetypes.spec.ts`)
22 test cases across 5 test suites:
- Archetype ID validation (valid/invalid enum values).
- Full snapshot validation (user_id, primary, scores, explanation, version).
- Public archetype validation (no scores, 3 bullets, valid timestamps).
- Explanation content validation (non-empty strings).
- Timestamp validation (ISO 8601 format).

## Maintenance Notes

### Adding New Archetypes
1. Add new `ArchetypeId` to enum in `models/archetype.py`.
2. Add keywords to `ARCHETYPE_KEYWORDS` in `engine.py`.
3. Add explanation templates to `explain()` in `engine.py`.
4. Update Coach tone mapping in `coach/service.py`.
5. Update Challenge preference mapping in `challenges/service.py`.
6. Add icon + label to frontend (`ArchetypeCard.tsx`, profile page).
7. Update tests to include new archetype.

### Adjusting Stability
- **Decay factor** (currently 0.92): Lower = more responsive, higher = more stable.
- **Secondary threshold** (currently 15 points): Raise = fewer secondaries shown.

### Changing Keywords
- Edit `ARCHETYPE_KEYWORDS` in `engine.py`.
- Maintain ~10-15 keywords per archetype.
- Avoid overlap (keywords should be distinctive).

## Known Limitations
1. **No LLM analysis**: Cannot detect subtle nuance (intentional tradeoff for determinism).
2. **Keyword-based**: May miss context (e.g., "I never ship" counted as "ship").
3. **In-memory storage**: No persistence (lost on restart). Future: migrate to DB.
4. **No historical tracking**: Only latest snapshot stored (no time-series).

## Future Enhancements
1. **DB persistence**: Migrate to Postgres with historical snapshots.
2. **Archetype evolution visualization**: Show score changes over time (line graph).
3. **Advanced Coach integration**: Archetype-specific coaching strategies (not just tone).
4. **Community features**: Show archetype distribution in family pools, leaderboards.
5. **Archetype-based recommendations**: Suggest creators with complementary archetypes.

## References
- Backend models: [backend/models/archetype.py](../../models/archetype.py)
- Engine: [engine.py](engine.py)
- Service: [service.py](service.py)
- API: [backend/api/archetypes.py](../../api/archetypes.py)
- Frontend component: [src/components/ArchetypeCard.tsx](../../../src/components/ArchetypeCard.tsx)
- Backend tests: [backend/tests/test_archetype_guardrails.py](../../tests/test_archetype_guardrails.py)
- Frontend tests: [src/__tests__/archetypes.spec.ts](../../../src/__tests__/archetypes.spec.ts)
