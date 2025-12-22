# Daily Challenges — Backend Implementation

**Status:** Production-ready (Phase 1 core feature).

## Overview

Daily Challenges provide lightweight, achievable prompts that eliminate decision fatigue and give creators a clear "today" reason to open OneRing. Each user receives exactly one challenge per UTC day, deterministically assigned from a static catalog.

### Key Principles
- **Invitations, not obligations:** Challenges encourage action without shame.
- **Decision fatigue reduction:** One prompt per day removes choice paralysis.
- **Deterministic:** Same user + same date = same challenge (no randomness).
- **Streak-safe:** Completion advances streaks only if not already incremented today.
- **No external dependencies:** Works offline with static catalog (no LLM calls).

## Architecture

### Domain Model

`backend/models/challenge.py` defines:
- **Challenge:** Domain model with lifecycle state (assigned → accepted → completed → expired)
- **ChallengeResult:** API response wrapper with next-action hints
- **ChallengeType:** Literal type: `"creative" | "reflective" | "engagement" | "growth"`
- **ChallengeStatus:** Literal type: `"assigned" | "accepted" | "completed" | "expired"`

### Service

`backend/features/challenges/service.py` implements **ChallengeService**:

```python
class ChallengeService:
    def get_today_challenge(user_id, today?) -> ChallengeResult
    def accept_challenge(user_id, challenge_id, accepted_at?) -> (ChallengeResult, List[events])
    def complete_challenge(user_id, challenge_id, completed_at?, completion_source?) -> (ChallengeResult, List[events])
    def expire_old_challenges(cutoff_date?) -> int
```

**Key behaviors:**
1. **Deterministic assignment:** Hash-based selection from 20-prompt catalog.
2. **Idempotent:** Same challenge_id operations produce identical results.
3. **Lifecycle transitions:** assigned → accepted → completed (or expired).
4. **Event emission:** challenge.accepted, challenge.completed.
5. **Expiration:** Old challenges marked expired; new day = new challenge.

### Challenge Catalog

Static catalog of 20 prompts (5 per type):

**Creative:**
- Write a 3-tweet thread on something you learned this week.
- Draft a hook that stops the scroll—test it on yourself first.
- Rewrite your bio. Make it curiosity-driven, not resume-driven.
- Share one contrarian belief you hold (no hedging).
- Turn a recent mistake into a teaching moment thread.

**Reflective:**
- Review your last 3 posts. Which one felt most true to you? Why?
- Write down one thing you avoided posting this week. What held you back?
- What's one post you'd write if nobody was watching?
- Look at your most engaged post. What made it resonate?
- Describe your creative voice in 3 words. Are your posts aligned?

**Engagement:**
- Reply thoughtfully to 3 posts from creators you admire.
- DM one person whose work inspired you this week. Be specific.
- Find a small creator (< 1k followers) and amplify their best post.
- Comment on a post that challenged your assumptions. No hot takes.
- Share someone else's thread with your own takeaway (give credit).

**Growth:**
- Study 3 viral threads. What pattern do they share?
- Run a content experiment: post at a new time and track engagement.
- Analyze your posting cadence. Are you consistent or sporadic?
- Research one platform feature you've never used (spaces, newsletters, etc.).
- Review your analytics: what's your best-performing content type?

## API Endpoints

**Backend routes:**

- **GET `/v1/challenges/today?user_id=...`**
  - Returns: `{ challenge_id, date, type, prompt, status, next_action_hint, streak_effect }`
  - Idempotent: same user + same UTC day = same challenge

- **POST `/v1/challenges/today/accept`**
  - Payload: `{ user_id, challenge_id }`
  - Returns: `{ challenge_id, status, next_action_hint, emitted }`
  - Transitions: assigned → accepted

- **POST `/v1/challenges/today/complete`**
  - Payload: `{ user_id, challenge_id, completion_source? }`
  - Returns: `{ challenge_id, status, next_action_hint, streak_effect, emitted }`
  - Transitions: assigned/accepted → completed
  - **Streak integration:** conditionally increments streak if not already incremented today

### Frontend Integration

**`src/app/api/challenges/today/route.ts`:**
- GET proxy to backend `/v1/challenges/today`
- Authenticated via Clerk; uses `currentUser().id`

**`src/app/api/challenges/today/accept/route.ts`:**
- POST proxy to backend accept endpoint
- Validates challenge_id presence

**`src/app/api/challenges/today/complete/route.ts`:**
- POST proxy to backend complete endpoint
- Optional completion_source (post_id if tied to a post)

**`src/app/dashboard/page.tsx`:**
- Loads today's challenge on mount
- Displays prompt with type badge
- Action buttons: Accept / Mark Complete (state-dependent)
- Supportive completion message: "Nice. You showed up today."
- Refreshes challenge and streak after completion

## Behavior Examples

### Scenario 1: Fresh Assignment
```
GET /v1/challenges/today?user_id=alice (2024-01-01)
→ { status: "assigned", prompt: "Write a 3-tweet thread...", type: "creative" }
```

### Scenario 2: Accept Challenge
```
POST /v1/challenges/today/accept { user_id: "alice", challenge_id: "abc123" }
→ { status: "accepted", next_action_hint: "You've got this. Share what you create." }
```

### Scenario 3: Complete Challenge (No Prior Post Today)
```
POST /v1/challenges/today/complete { user_id: "alice", challenge_id: "abc123" }
→ { status: "completed", streak_effect: "incremented", next_action_hint: "Nice. You showed up today." }
```

### Scenario 4: Complete Challenge (Already Posted Today)
```
// User posted earlier today (streak already at +1 for today)
POST /v1/challenges/today/complete { user_id: "alice", challenge_id: "abc123" }
→ { status: "completed", streak_effect: "none", next_action_hint: "Nice. You showed up today." }
```

### Scenario 5: Deterministic Assignment
```
GET /v1/challenges/today?user_id=alice (2024-01-01)
→ { challenge_id: "abc123", prompt: "Draft a hook..." }

GET /v1/challenges/today?user_id=alice (2024-01-01) [repeated]
→ { challenge_id: "abc123", prompt: "Draft a hook..." } [identical]
```

### Scenario 6: Different Users, Different Challenges
```
GET /v1/challenges/today?user_id=alice (2024-01-01)
→ { challenge_id: "abc123", type: "creative" }

GET /v1/challenges/today?user_id=bob (2024-01-01)
→ { challenge_id: "def456", type: "reflective" } [different prompt]
```

### Scenario 7: Expiration (New Day)
```
// 2024-01-01: Challenge assigned, not completed
// 2024-01-02: Service expires old challenges
service.expire_old_challenges(cutoff_date=2024-01-02)
→ 1 challenge expired

GET /v1/challenges/today?user_id=alice (2024-01-01)
→ { status: "expired", next_action_hint: "A new challenge awaits tomorrow." }
```

## Events & Side Effects

### Emitted Events

- **challenge.accepted**
  - Payload: `{ userId, challengeId, acceptedAt }`
  - Side effects: Handlers may log analytics; must not mutate challenge state.

- **challenge.completed**
  - Payload: `{ userId, challengeId, completedAt, result: "full", ringEarned? }`
  - Side effects: May trigger streak increment (via separate service call); must not double-increment.

### Streak Integration (Critical)

**Rule:** Challenge completion can advance streak ONLY if no post has already incremented it today.

**Implementation:**
1. Backend `/v1/challenges/today/complete` checks current streak state.
2. If `last_active_date == today`, streak already incremented → no-op.
3. If `last_active_date < today`, call `streak_service.record_posted(challenge_id, platform="challenge")`.
4. Return `streak_effect: "incremented"` or `"none"` based on outcome.

**Guarantees:**
- Max 1 streak increment per user per UTC day (enforced by StreakService).
- Challenge completion and post both use same dedupe logic (day + user).
- No double-increment possible; tests verify this invariant.

## Testing

All tests in `backend/tests/test_challenge_guardrails.py` verify:
1. ✅ Deterministic assignment (same user + same date = same challenge).
2. ✅ Different users get different challenges.
3. ✅ Lifecycle: assigned → accepted → completed.
4. ✅ Idempotent accept (second call is no-op).
5. ✅ Idempotent complete (second call is no-op).
6. ✅ Expiration marks old challenges as expired.
7. ✅ Challenge completion does NOT double-increment streak if already incremented today.

**Run tests:**
```bash
cd c:\Users\hazar\onering
python -m pytest backend/tests/test_challenge_guardrails.py -v
```

All 7 tests pass without environment variables; no mocking required.

## Integration Checklist

- ✅ Backend domain model (Challenge, ChallengeResult, types).
- ✅ Static 20-prompt catalog across 4 types.
- ✅ Deterministic assignment service (hash-based).
- ✅ Lifecycle methods: assign, accept, complete, expire.
- ✅ Streak integration (conditional increment, no double-counting).
- ✅ FastAPI endpoints registered with proper error handling.
- ✅ Frontend API routes with Clerk authentication.
- ✅ Dashboard UI with accept/complete buttons and supportive copy.
- ✅ All tests passing (7/7).
- ✅ Events ready for downstream handlers (analytics, momentum).

## Design Decisions

1. **Static Catalog Over LLM Generation:**
   - Eliminates external dependencies (no Groq/OpenAI calls).
   - Deterministic across restarts and environments.
   - 20 prompts provide variety without overwhelming choice.

2. **Hash-Based Deterministic Selection:**
   - `hash(user_id + date) % catalog_size` ensures stability.
   - Same user always gets same challenge on same day.
   - Different users get different challenges (high probability).

3. **Single Challenge Per Day:**
   - Reduces decision fatigue.
   - Creates ritual ("check OneRing for today's challenge").
   - Aligns with streak mechanics (daily action).

4. **Lifecycle Simplicity:**
   - Optional "accept" step (not required to complete).
   - Completion is single-action; no partial states.
   - Expiration is passive (no notifications; just marks expired).

5. **Streak-Safe Completion:**
   - Challenge completion can count toward daily streak.
   - Never double-increments if user already posted today.
   - Uses same StreakService invariants (day-level dedupe).

6. **Non-Punitive Language:**
   - "Nice. You showed up today." (not "Great job!" or "Finally!").
   - "Ready to try? No pressure." (not "You must complete this.").
   - Expired challenges: "A new challenge awaits tomorrow." (not "You missed it.").

7. **No RING Rewards Yet:**
   - Challenges are intrinsic motivation experiments.
   - Future: may award small RING bonuses for streaks.
   - Current: completion message is the reward.

## Future Integration Points

### AI Post Coach
- Coach can provide feedback on challenge drafts before posting.
- Coach suggestions align with challenge type (creative → hook quality, reflective → depth).
- No auto-completion; coach is advisory only.

### Momentum Score
- Challenge completion contributes to overall momentum.
- Variety bonus: completing all 4 types in a week.
- Consistency signal: challenges + posts = full momentum.

### Archetypes (Future)
- Challenge prompts may be filtered/weighted by user archetype.
- Example: "Rebel" archetype gets more contrarian/engagement challenges.
- "Builder" archetype gets more growth/analytics challenges.

---

**No further action needed.** Phase 1 loop now includes Streaks + Challenges, giving users two clear reasons to open OneRing daily.