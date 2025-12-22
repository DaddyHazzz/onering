# .ai/domain/archetypes.md — AI Agent Context

**Phase 2 Feature #3: Archetypes + Personalization**

This document provides domain context for AI agents working on the OneRing archetypes system.

---

## Feature Intent

Archetypes give creators a **mirror that shows who they're becoming**, not who they wish they were. The system observes signals from Coach feedback, Challenge choices, and post patterns to classify creators into 6 evolving archetypes.

**Core Promise:** Soft guidance without destiny. Archetypes influence Coach suggestions and Challenge selection but never lock users in or shame them.

---

## 6 Archetypes (with Personality + Influence)

| Archetype | Icon | Core Traits | Coach Influence | Challenge Influence |
|-----------|------|-------------|-----------------|-------------------|
| **Truth Teller** 🎯 | Direct, no-BS, facts | Makes suggestions more direct ("might" → "should") | Prefers "creative" challenges | |
| **Builder** 🔨 | Execution-focused, ships fast | Directive tone ("Consider" → "Try") | Favors "growth" challenges | |
| **Philosopher** 💭 | Deep thinker, explores nuance | Exploratory tone ("Add" → "Consider adding") | Favors "reflective" challenges | |
| **Connector** 🤝 | Relationship-driven, community | Converts statements → questions | Favors "engagement" challenges | |
| **Firestarter** 🔥 | Provocateur, disruptor, catalyst | Aggressive tone ("Consider" → "Push further") | Prefers "creative" challenges | |
| **Storyteller** 📖 | Rich narrative, vivid details | Vivid tone ("Add details" → "Paint the scene") | Prefers "creative" challenges | |

---

## Scoring System (Pure Functions, Deterministic)

### Entry Points
- `score_from_text(text, platform="twitter")` — keyword analysis with platform multipliers
- `score_from_coach_feedback(scores_dict, suggestions_list)` — converts Coach scores to boosts
- `score_from_challenge_type(challenge_type)` — maps challenge types to archetypes

### Core Functions
- `merge_scores(current, new, decay=0.92)` — weighted merge with historical smoothing
- `pick_primary_secondary(scores)` — primary = max, secondary = 2nd max if within 15 points
- `explain(primary, secondary, user_id)` — 3 supportive bullets, deterministic, no shame words

### Key Constants
- **DECAY_FACTOR** = 0.92 (higher = more stable, lower = more responsive)
- **SECONDARY_THRESHOLD** = 15 points (gap must be ≤15 to show secondary)
- **SHAME_WORDS** = banned from explanations (lack, fail, stuck, mediocre, weak, poor, shame, etc.)

---

## Integration Checkpoints

### ✅ Coach Service
**File:** `backend/features/coach/service.py`

**Integration Pattern:**
```python
# In get_coach_feedback():
archetype_snapshot = archetype_service.get_snapshot(user_id)
feedback = service.generate_feedback(
    request,
    archetype_primary=archetype_snapshot.primary,
    archetype_secondary=archetype_snapshot.secondary,
)
```

**Tone Inflection** (deterministic):
- Builder: "Consider" → "Try", "could" → "should"
- Philosopher: "Add" → "Consider adding", "Try" → "Reflect on"
- Connector: statements → questions ("What if you...?")
- Truth Teller: "might" → "should" (more direct)
- Firestarter: "Consider" → "Push further"
- Storyteller: "Add details" → "Paint the scene"

**Important:** Archetype influences **tone only**, not content. Same inputs → same suggestions.

### ✅ Challenges Service
**File:** `backend/features/challenges/service.py`

**Integration Pattern:**
```python
# In get_today_challenge():
archetype_snapshot = archetype_service.get_snapshot(user_id)
challenge = service.get_today_challenge(
    user_id,
    archetype=archetype_snapshot.primary,
)
```

**Preference Filtering** (deterministic):
- Builder → "growth" challenges
- Philosopher → "reflective" challenges
- Connector → "engagement" challenges
- Truth Teller/Firestarter/Storyteller → "creative" challenges

**Fallback:** If filtered subset is empty, use full catalog.

**Important:** Selection is `hash(user_id + date + archetype) % len(subset)` → deterministic.

### ✅ Profile API
**File:** `backend/api/profile.py`

**Integration Pattern:**
```python
# In get_public_profile():
archetype_snapshot = archetype_service.get_snapshot(user_id)
# Add to response:
response["archetype"] = archetype_snapshot.to_public_dict()  # Safe subset only
```

**Public Subset (to_public_dict):**
- ✅ userId, primary, secondary, explanation, updatedAt
- ❌ NO scores (internal only)
- ❌ NO signal payloads (privacy)

---

## API Surface

### Backend Endpoints
- **GET `/v1/archetypes/me?user_id=...`** — Full snapshot (authenticated context only)
- **POST `/v1/archetypes/signal`** — Record behavioral signal (idempotent)
- **GET `/v1/archetypes/public?user_id=...`** — Safe public subset (no auth)

### Frontend Routes
- **GET `/api/archetypes/me`** — Proxy to backend (Clerk auth required)
- **POST `/api/archetypes/signal`** — Proxy to backend (Clerk auth required)
- **GET `/api/archetypes/public`** — Proxy to backend (no auth)

### Frontend Components
- **`<ArchetypeCard />`** — Dashboard component showing archetype + explanation
- **Profile page** — Includes archetype card if available (optional field)

---

## Critical Design Constraints

### ✅ MUST Preserve
1. **Determinism**: Same inputs → same outputs. No randomness. Coach + Challenges depend on this.
2. **Idempotency**: Recording the same signal twice doesn't double-count (hash-based deduplication).
3. **Public Safety**: Scores never leak to public profiles. Only safe fields exposed.
4. **Supportive Tone**: No shame words in explanations. Positive, growth-focused only.
5. **Stability**: Large score gaps resist flipping. Decay factor smooths volatility.
6. **No External Deps**: Works entirely offline. No LLM calls, no API dependencies.

### ❌ DO NOT
1. **Add randomness** to scoring (breaks determinism).
2. **Change decay factor without testing** (affects stability).
3. **Expose scores to public API** (privacy violation).
4. **Call external LLMs** for classification (tradeoff: lose determinism, gain richness).
5. **Recompute old signals** without proper versioning (data integrity).
6. **Mix archetype computation with user action** (archetype should observe, not influence behavior).

---

## Testing Strategy

### Backend Tests (23 test cases)
**File:** `backend/tests/test_archetype_guardrails.py`

**Guardrail Classes:**
1. **Determinism** (3 tests): Same signal twice → same result
2. **Stability** (2 tests): Large gaps resist flipping, decay works
3. **Clamping** (2 tests): Scores always 0..100
4. **Explanation** (3 tests): 3 bullets, no shame words, non-empty
5. **Public Safety** (2 tests): to_public_dict excludes scores
6. **Coach Integration** (3 tests): Deterministic tone, works with/without archetype
7. **Challenge Integration** (3 tests): Deterministic filtering and selection
8. **Pick Logic** (2 tests): Secondary only if within 15 points
9. **Keyword Scoring** (3 tests): Keywords boost correct archetypes

### Frontend Tests (23 test cases)
**File:** `src/__tests__/archetypes.spec.ts`

**Validation Suites:**
1. **Archetype ID Validation** (2 tests): Enum values only
2. **Full Snapshot Validation** (9 tests): Structure, types, ranges
3. **Public Archetype Validation** (8 tests): Safe subset only, no scores
4. **Explanation Content** (2 tests): Non-empty, supportive
5. **Timestamp Validation** (2 tests): ISO 8601 format

### Profile Tests (4 additional tests)
**File:** `src/__tests__/profile.spec.ts`

**Coverage:**
- Profile with archetype (valid)
- Profile without archetype (backward compatible)
- Profile with invalid archetype (rejected)
- Profile with invalid explanation (rejected)

**Commands:**
```bash
# Frontend tests
pnpm test -- --run

# Backend tests
cd backend && pytest tests/test_archetype_guardrails.py -v
```

---

## Known Limitations (Phase 2)

1. **In-Memory Storage**: Data lost on restart (no persistence)
   - Fix in Phase 3: Migrate to Postgres with historical snapshots

2. **Keyword-Based Analysis**: Misses context (e.g., "I never ship" counts "ship")
   - Fix in Phase 3: Optional LLM-enhanced classification (optional, not required)

3. **No Score Visualization**: Users see primary/secondary + explanation, not score radar
   - Fix in Phase 3: Add radar chart showing score distribution

4. **No Historical Tracking**: Only latest snapshot stored (no time-series)
   - Fix in Phase 3: Store all historical snapshots, enable evolution visualization

5. **No Signal Aggregation**: High-frequency users may cause performance issues
   - Fix in Phase 3: Batch signal processing

---

## Maintenance Checklist (For Future Work)

### To Add New Archetype
1. [ ] Add to `ArchetypeId` enum in `backend/models/archetype.py`
2. [ ] Add keywords to `ARCHETYPE_KEYWORDS` dict in `backend/features/archetypes/engine.py`
3. [ ] Add explanation templates to `explain()` function
4. [ ] Update Coach tone mapping in `backend/features/coach/service.py`
5. [ ] Update Challenge preference mapping in `backend/features/challenges/service.py`
6. [ ] Add icon + label to `src/components/ArchetypeCard.tsx`
7. [ ] Add icon + label to `src/app/u/[handle]/page.tsx`
8. [ ] Update all test files (backend + frontend)

### To Adjust Stability
- **Decay factor**: Edit `DECAY_FACTOR` in `engine.py`, rerun tests
- **Secondary threshold**: Edit `SECONDARY_THRESHOLD` in `pick_primary_secondary()`, rerun tests

### To Change Keywords
1. [ ] Edit `ARCHETYPE_KEYWORDS` in `engine.py`
2. [ ] Maintain ~10-15 keywords per archetype
3. [ ] Avoid overlap (keywords should be distinctive)
4. [ ] Run tests to ensure no regressions

---

## References

- **Completion Document**: [PHASE2_ARCHETYPES_COMPLETE.md](../PHASE2_ARCHETYPES_COMPLETE.md)
- **Feature README**: [backend/features/archetypes/README.md](../backend/features/archetypes/README.md)
- **Backend Models**: [backend/models/archetype.py](../backend/models/archetype.py)
- **Engine**: [backend/features/archetypes/engine.py](../backend/features/archetypes/engine.py)
- **Service**: [backend/features/archetypes/service.py](../backend/features/archetypes/service.py)
- **Backend API**: [backend/api/archetypes.py](../backend/api/archetypes.py)
- **Frontend Component**: [src/components/ArchetypeCard.tsx](../src/components/ArchetypeCard.tsx)
- **Backend Tests**: [backend/tests/test_archetype_guardrails.py](../backend/tests/test_archetype_guardrails.py)
- **Frontend Tests**: [src/__tests__/archetypes.spec.ts](../src/__tests__/archetypes.spec.ts)

---

## Questions?

If working on archetype-related tasks:
1. Read [PHASE2_ARCHETYPES_COMPLETE.md](../PHASE2_ARCHETYPES_COMPLETE.md) for full context
2. Check [backend/features/archetypes/README.md](../backend/features/archetypes/README.md) for technical details
3. Review test files for examples and guardrails
4. Ensure determinism is preserved in all changes

**Key Principle:** Archetypes are a **mirror, not a cage**. They show creators who they're becoming without locking them in. Every change should preserve that intent.
- Analytics tracks alignment trends
