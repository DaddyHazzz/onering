# Creator Streaks — Backend Implementation

**Status:** Production-ready (Phase 1 core feature).

## Overview

Creator Streaks track consecutive days of posting activity. They measure momentum, not volume, and prioritize encouragement over punishment through mercy mechanics.

### Key Principles
- **Never red zero:** Streaks start at 1 on first post; never display 0 to the user.
- **Mercy by default:** One missed day is forgiven (grace); additional misses trigger partial decay.
- **Protection windows:** Every 7 days of consecutive activity, the user earns a new grace window.
- **Deterministic:** Same inputs always produce the same state; idempotent on event retry.

## Architecture

### Domain Model

`backend/models/streak.py` defines:
- **StreakRecord:** Holds user streak state (length, longest, last active date, grace usage, decay state, event dedup).
- **StreakSnapshot:** Immutable point-in-time record for history.
- **StreakStatus:** Literal type: `"active" | "grace" | "decayed"`.

### Service

`backend/features/streaks/service.py` implements **StreakService**, a pure state machine:

```python
class StreakService:
    def record_posted(user_id, post_id, posted_at, platform) -> (StreakRecord, List[events])
    def get_state(user_id) -> dict
    def history(user_id) -> List[snapshot_dicts]
```

**Key behaviors:**
1. **Idempotent:** Same `post_id` on same day never double-increments.
2. **Day-level only:** Uses UTC normalized dates; ignores time-of-day variance.
3. **Grace window:** First missed day is absorbed without streak loss.
4. **Partial decay:** Misses beyond grace trim momentum, but preserve some progress (min 1).
5. **Protection reset:** After every 7-day stride, grace is restored.
6. **Event emission:** On success or miss, appropriate events are emitted (no side effects in handlers).

### API Endpoints

**Backend routes** (no prefixes needed; aliased at root):

- **GET `/v1/streaks/current?user_id=...`**
  - Returns: `{ current_length, longest_length, last_active_date, grace_used, decay_state, status, next_action_hint }`
  - Example: `{ "current_length": 5, "status": "active", "next_action_hint": "Post today to stay hot. 2 day(s) to your next protection window." }`

- **GET `/v1/streaks/history?user_id=...`**
  - Returns: `{ history: [...] }` — list of daily snapshots.

- **POST `/v1/streaks/events/post`**
  - Payload: `{ user_id, post_id, posted_at?, platform? }`
  - Called by `src/app/api/post-to-x/route.ts` after successful posting.
  - Returns: `{ state, emitted }` — new streak state + events triggered.

- **POST `/v1/streaks/events/scheduled`**
  - Payload: `{ user_id, content_ref, scheduled_for? }`
  - Called when a post is scheduled (not yet published).
  - Scheduled posts do not advance streaks until posted.

### Frontend Integration

**`src/app/api/streaks/current/route.ts`:**
- Next.js route that proxies to `/v1/streaks/current` on the backend.
- Authenticated via Clerk; uses `currentUser().id`.
- Returns the full streak state for client display.

**`src/app/dashboard/page.tsx`:**
- Loads streak on mount via `refreshStreak()`.
- Displays current length + protective status emoji (🚀 active | 🛡️ grace | 📉 decayed).
- Shows progress bar toward next protection window (7-day stride).
- Refreshes streak after each post.

## Behavior Examples

### Scenario 1: Fresh Start (No Streak)
```
Day 1: Post → current_length=1, longest_length=1, status="active", next_action_hint="Post today to stay hot..."
```

### Scenario 2: Day-2 Post (Continuous)
```
Day 2: Post → current_length=2, status="active" (no grace used)
```

### Scenario 3: Miss Day 3, Post Day 4 (Grace Used)
```
Day 4: Post (after 1-day gap) → current_length=2, status="grace", grace_used=true
   Reason: 1-day gap is absorbed by grace. next_action_hint="You're protected—post today to lock it in."
```

### Scenario 4: Miss Days 3, 4, 5, Post Day 6 (Partial Decay)
```
Day 6: Post (after 3-day gap) → current_length=1 (was 2, decayed by 1), status="decayed"
   Reason: Grace absorbs 1 day; remaining 2 days trigger decay. next_action_hint="Momentum dipped—post today to rebuild..."
```

### Scenario 5: 7-Day Streak, Miss Day 8, Post Day 9 (Protection Restored)
```
Day 9: Post → current_length=7, status="grace", grace_used=false (reset at stride)
   Reason: At 7-day boundary, grace is restored even though it was just used.
```

### Scenario 6: Retry Same Post (Idempotent)
```
Day 1: Post (post_id="p1") → current_length=1
Day 1: Post (post_id="p1") again within same UTC day → current_length=1 (no change, deduplicated)
```

## Events & Side Effects

### Emitted Events
- **streak.incremented**
  - Payload: `{ userId, streakDay (ISO date), reason ("post"|"challenge"), protectionUsed? }`
  - Side effects: Handlers may emit analytics or trigger UI notifications; must not re-mutate streaks.

- **streak.missed**
  - Payload: `{ userId, missedDay (ISO date), protectionAvailable? }`
  - Side effects: Handlers may trigger recovery prompts; must not retro-break already-advanced streaks.

### Event Idempotency
- Events are keyed on `(userId, day)` for incrementing.
- Events are keyed on `(userId, missedDay)` for missing.
- Handlers must be idempotent (re-running should not double-emit analytics or send duplicate notifications).

## Testing

All tests in `backend/tests/test_streak_guardrails.py` verify:
1. ✅ No double-increment in same UTC day.
2. ✅ Failed posts never break streaks.
3. ✅ Grace-day behavior (1 missed day absorbed, streak preserved).
4. ✅ Partial decay (multi-day misses trim momentum).
5. ✅ Idempotent retries (same `post_id` on retry does not double-count).

**Run tests:**
```bash
cd c:\Users\hazar\onering
python -m pytest backend/tests/test_streak_guardrails.py -v
```

All 5 tests pass without environment variables; no mocking required.

## Integration Checklist

- ✅ Backend domain model (streak.py) and service (service.py).
- ✅ FastAPI endpoints registered in main.py.
- ✅ Frontend API route (src/app/api/streaks/current/route.ts).
- ✅ Dashboard UI displays streak with status emoji and progress bar.
- ✅ Post-to-X route emits `streak.posted` event (best-effort).
- ✅ All tests pass (5/5).
- ✅ Events ready for downstream handlers (challenges, coach, analytics).

## Future Integration Points

### Challenge System
- `challenge.completed` events will also advance streaks (once per user per day).
- Challenges and posts compete for the same day's streak increment (max 1 per day).

### AI Post Coach
- Coach feedback will not auto-adjust streak counts.
- Instead, coach scores influence perceived "quality" of momentum without changing length.

### Analytics & Monitoring
- Real-time dashboard will show: active users with streaks, % in "grace" vs "active" vs "decayed".
- Historical view: user streaks over time, protection window usage patterns.

---

**No further action needed.** Phase 1 loop is **ready** for challenges and coach integration.
