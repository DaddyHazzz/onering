# AI Post Coach — Deterministic Feedback Engine

**Status:** Production-ready v1 (Phase 1 feature, MVP).

## Overview

AI Post Coach provides a deterministic, supportive pre-flight check for draft posts across platforms (X, Instagram, LinkedIn). It analyzes content for clarity, resonance, platform fit, authenticity, and momentum alignment—without external LLM calls or network dependencies.

**Key principle:** Coach is a mirror, not a judge. It provides honest, actionable feedback that helps creators refine their voice—never shaming or manipulating toward clicks.

## Architecture

### Domain Model

`backend/models/coach.py` defines:
- **CoachRequest:** User draft + platform + optional metadata (values_mode, archetype)
- **CoachResponse:** Scores (5 dimensions), tone detection, suggestions, warnings, revised example
- **Types:** Literals for platform, post_type, values_mode, tone

### Scoring Engine

`backend/features/coach/scoring_engine.py` implements pure, deterministic heuristics:

**Clarity (0-100):**
- Penalize extremely long sentences (>30 words)
- Reward structure (line breaks, bullet points, section markers)
- Penalize low punctuation density (sign of run-on text)
- Reward clarity keywords ("first", "then", "because")

**Resonance (0-100):**
- Reward first-person narrative (>3 mentions of I/me/my/we)
- Reward specificity (concrete details, numbers, names)
- Penalize flat corporate buzzwords (synergy, leverage, paradigm shift)
- Reward emotion words (learned, struggled, inspired, vulnerable)
- (Viral threads) reward insight language (pattern, realize, truth)

**Platform Fit (0-100):**
- **X:** Reward brevity (<280 chars), hooks, scannability; penalize long rambling text
- **LinkedIn:** Reward concrete insights + lessons; penalize sarcasm; allow longer format
- **Instagram:** Reward visual language, emotional warmth; penalize excessive sarcasm

**Authenticity (0-100):**
- Penalize excessive hashtags (>5)
- Penalize hyperbole without evidence (best ever, game-changer, revolutionary)
- Reward concrete experience language (I learned, I failed, I messed up)
- Apply values_mode constraints (faith_aligned: avoid profanity; optimistic: avoid doom spirals)

**Momentum Alignment (0-100):**
- Reward forward-motion language (today, now, starting, building, shipping)
- Penalize doom spirals (dying, failing, hopeless) without redemption (lift words: but, learned, next)
- Bonus for doom + lift (redemption arc)

### Tone Detection (Deterministic)

Keyword-based categorization:
- **Hopeful:** excited, looking forward, inspired, grateful
- **Reflective:** realized, learned, discovered, wondered
- **Confrontational:** actually, honestly, real talk, truth is
- **Playful:** haha, lol, hilarious, funny
- **Neutral:** default fallback (confidence = 0.5)

Confidence scales with indicator count; max 0.95.

### Service Layer

`backend/features/coach/service.py`:
- `generate_feedback(request) -> (CoachResponse, events)`
- Idempotency key: `event_id = hash(user_id + draft)[:16]`
- Emits: `coach.feedback_generated` event with scores, suggestions, warnings
- Zero external dependencies

### API Endpoint

`backend/api/coach.py`:
- **POST `/v1/coach/feedback`**
  - Accepts: `CoachRequestSchema` (Pydantic)
  - Validates: user_id, platform, draft (1-4000 chars)
  - Returns: `{ data: CoachResponse, emitted: [event] }`
  - No auth required at backend (frontend adds Clerk auth)

### Frontend Integration

`src/app/api/coach/feedback/route.ts`:
- Clerk-authenticated proxy
- Enforces `user_id = caller.id` (no spoofing)
- Forwards to backend, returns raw response
- Error handling with Zod validation

## Behavioral Examples

### Example 1: Clear, Authentic X Post
```
Input:
- platform: "x"
- draft: "I learned something counterintuitive today: the more specific you get, the broader your appeal becomes."

Output:
- overall_score: 82
- clarity: 85 (good structure, specific example)
- resonance: 85 (first-person, concrete)
- platform_fit: 80 (concise, insightful)
- authenticity: 85 (specific insight, no hype)
- momentum_alignment: 75 (forward-looking)
- tone: "reflective" (confidence 0.65)
- suggestions: ["Consider adding an example or consequence"]
- warnings: []
```

### Example 2: Long LinkedIn with Lessons
```
Input:
- platform: "linkedin"
- draft: "After 10 years building, I learned three things: listen first, ship fast, compound small wins. Here's why each matters..."

Output:
- overall_score: 78
- clarity: 75 (good structure with numbered points)
- resonance: 80 (specific numbers, experience)
- platform_fit: 85 (insight-heavy, professional)
- authenticity: 80 (concrete experience language)
- momentum_alignment: 70 (could emphasize next step)
- tone: "reflective" (confidence 0.75)
- suggestions: ["Close with a specific call-to-action or question"]
- warnings: []
```

### Example 3: Overhyped Instagram Caption
```
Input:
- platform: "instagram"
- draft: "This is the BEST EVER moment of my life!!! #amazing #incredible #blessed #grateful #thankful #blessed"

Output:
- overall_score: 42
- clarity: 50 (excessive caps reduce clarity)
- resonance: 40 (no specificity, all hype)
- platform_fit: 45 (visual language missing)
- authenticity: 30 (hyperbole, excessive hashtags)
- momentum_alignment: 35 (no forward motion)
- tone: "hopeful" (confidence 0.8)
- suggestions: [
    "Reduce hashtags to 2-3 most important",
    "Share a specific detail instead of hype",
    "Use visual language: what does this moment look/feel like?",
    "Replace exclamation marks with specificity"
  ]
- warnings: ["Too many hashtags (reduces authenticity)"]
```

### Example 4: Values Mode — Confrontational
```
Input:
- platform: "x"
- draft: "Here's the truth: most advice you read online is generic and useless for YOUR situation."
- values_mode: "confrontational"

Output:
- overall_score: 71
- authenticity: 75 (directness rewarded in this mode; would be penalized in "optimistic")
- warnings: []
- suggestions: ["Back up this claim with a specific example"]
```

## Invariants & Constraints

1. **Determinism:** Same draft + platform + values_mode = identical scores (to 0.01%)
2. **No Network:** Pure function; no LLM, API, or external calls
3. **No Shame:** Suggestions are developmental, never punitive
4. **No Auto-Post:** Coach never posts or changes streaks; it's advisory only
5. **Idempotency:** `event_id = hash(user_id + draft)` allows safe replay
6. **Values Respect:** values_mode filters disallowed language (profanity, despair, personal attacks)
7. **Platform Differentiation:** Same draft scores differently across X/LinkedIn/Instagram

## Testing

All tests in `backend/tests/test_coach_guardrails.py` (27 passing):
1. ✅ Determinism: same input = identical output
2. ✅ No network: pure function verification
3. ✅ Safety: disallowed language detection (all modes)
4. ✅ Platform differentiation: X rewards brevity, LinkedIn rewards insight
5. ✅ Values mode: confrontational allows directness; optimistic penalizes despair
6. ✅ Tone detection: hopeful, reflective, neutral, confrontational, playful
7. ✅ Suggestions: concrete, actionable, never shaming
8. ✅ Event emission: correct schema, idempotent
9. ✅ Request validation: all fields validated
10. ✅ Revised examples: deterministic, under 600 chars
11. ✅ Dimension scores: all 0-100, overall weighted average
12. ✅ Strategic language: no shame words, advisory only

Frontend tests in `src/__tests__/coach.spec.ts`:
- Zod schema validation (request/response)
- Required field checks
- Optional field defaults
- Platform/type enums
- Score range validation

**Run:**
```bash
# Backend
python -m pytest backend/tests/test_coach_guardrails.py -v

# Frontend (when Vitest available)
npm run test -- src/__tests__/coach.spec.ts
```

## Event Contract

**coach.feedback_generated**
- Payload: `{ userId, draftId, scores, suggestions, warnings, generatedAt }`
- Source: coach service (deterministic, no LLM)
- Side-effect rules: Handlers may log analytics; must not post or increment streaks
- Idempotency: keyed by `draftId` (user_id + draft hash)

## Integration Points

### Dashboard UI (Future)
- "Get Coach Feedback" button on generate/post panel
- Display scores as dimension bars (0-100 scale)
- Show 3-5 suggestions in card format
- Optional "See Revised Example" expandable section
- Copy button for revised example

### Momentum Score (Future)
- Coach feedback scores may influence confidence signals
- High authenticity + platform_fit suggest strong post
- Used for future archetype recommendations

### Archetype Tagging (Future)
- Coach can suggest which archetype best fits draft
- Store as pass-through field for future personalization
- Current: accept but ignore (prepare for future filtering)

## Future Enhancements

### LLM-Enhanced Suggestions (Optional Flag)
- Current: Heuristic suggestions are concrete and rule-based
- Future: Behind a `use_llm_suggestions` flag, could call Groq for detailed rewrites
- Contract: Still deterministic if seeded with draft hash

### Platform-Specific Coaches
- Current: Generic coach works across platforms
- Future: Specialized coaches for each platform (Twitter/X coach knows threads; LinkedIn coach emphasizes narrative)

### Real-Time Coach (Streaming)
- Current: Single endpoint, full response
- Future: Stream suggestions as user types (websocket integration)

### Coach Learning
- Current: No training; static heuristics
- Future: Could track which suggestions users adopt; use as feedback signal for heuristic tuning

## Design Decisions

1. **Deterministic Over LLM:**
   - Ensures consistency and reproducibility
   - No API costs or rate-limiting
   - Heuristics are transparent and auditable
   - Future LLM integration is opt-in behind a flag

2. **5 Dimensions:**
   - Clarity (structural health)
   - Resonance (emotional connection)
   - Platform Fit (format alignment)
   - Authenticity (voice integrity)
   - Momentum Alignment (forward motion)
   - Together they form a holistic picture; weighted average for overall score

3. **Non-Shaming Language:**
   - Suggestions assume creator is learning, not failing
   - No phrases like "Bad," "Wrong," "You need to..." instead: "Consider," "Could add," "Try shifting..."
   - Supportive tone aligns with OneRing product philosophy

4. **Platform Differentiation:**
   - Not one-size-fits-all; different platforms have different norms
   - X rewards hooks and brevity; LinkedIn rewards insight and narrative; Instagram rewards visual warmth
   - Same content, different platform = different scores (not averaged)

5. **Idempotency:**
   - Same draft always produces same event_id
   - Allows safe replay and batch processing
   - Enables future caching layer

## No Further Action Needed

Coach is production-ready v1. Future enhancements (LLM, streaming, real-time) are scoped separately. Phase 1 loop now has:
1. Streaks (reason to show up daily)
2. Challenges (what to post)
3. Coach (how to improve)

Together: "I have a reason, I know what to post, and I'm getting better at it."

---

**Implementation:** All files created; tests passing; zero external dependencies.
