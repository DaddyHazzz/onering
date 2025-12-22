# Analytics Domain — OneRing Phase 3.4

**Status:** Phase 3.4 Complete (December 21, 2025)  
**Scope:** Analytics models, deterministic leaderboards, insight-oriented UI  
**Safety:** No engagement chasing, no shame language, no comparative pressure

---

## Overview

Phase 3.4 introduces analytics for collaboration tracking and leaderboards for community discovery. Core principle: **insights for reflection, not dopamine loops**.

### What Changed

- **Backend models:** DraftAnalytics, UserAnalytics, LeaderboardEntry, LeaderboardResponse (frozen Pydantic)
- **Backend service:** Deterministic analytics computation (same input + same `now` = identical output)
- **Backend API:** GET `/v1/analytics/leaderboard?metric=collaboration|momentum|consistency`
- **Frontend page:** `/dashboard/insights` (activity cards + leaderboard preview)
- **Tests:** 20+ backend tests + 18 frontend tests (all passing)

---

## Analytics Models

### DraftAnalytics
Metrics for a single collaborative draft:
- `draft_id` (UUID)
- `views` (int ≥ 0): clicks from share card
- `shares` (int ≥ 0): times shared
- `segments_count` (int ≥ 0): total segments
- `contributors_count` (int ≥ 1): unique contributors
- `ring_passes_count` (int ≥ 0): total ring passes
- `last_activity_at` (ISO timestamp): most recent segment or ring pass
- `computed_at` (ISO timestamp): when analytics were computed

### UserAnalytics
Aggregated metrics for a user:
- `user_id` (Clerk user ID)
- `drafts_created` (int ≥ 0): drafts authored
- `drafts_contributed` (int ≥ 0): drafts with segments added
- `segments_written` (int ≥ 0): total segments
- `rings_held_count` (int ≥ 0): times held ring
- `avg_time_holding_ring_minutes` (float ≥ 0): average duration
- `last_active_at` (ISO timestamp): most recent activity
- `computed_at` (ISO timestamp): when computed

### LeaderboardEntry
Single entry in a leaderboard:
- `position` (1-10): rank
- `user_id`: Clerk user ID
- `display_name`: User display (stub: `user_XXXXXXXX`, Phase 3.5 will be real names)
- `avatar_url`: Avatar URL (nullable, stub: Phase 3.5)
- `metric_value` (float): score for this leaderboard
- `metric_label` (string): human-readable metric (e.g., "12 segments • 3 rings")
- `insight` (string): supportive message (never comparative)

### LeaderboardResponse
API response for leaderboard:
- `metric_type`: "collaboration" | "momentum" | "consistency"
- `entries`: List of LeaderboardEntry (max 10)
- `computed_at`: ISO timestamp
- `message`: Supportive header (e.g., "Community highlights: creators shaping work together")

---

## Leaderboard Types

### 1. Collaboration Leaderboard
**Based on:** segments_written × 3 + rings_held_count × 2 + drafts_contributed

**Message:** "Community highlights: creators shaping work together"

**Insights:**
- Position 1: "Leading by example—great contributions!"
- Positions 2-3: "Strong collaboration—keep it up!"
- Positions 4-5: "Good momentum on shared work!"
- 6-10: "Growing collaboration skills!"

**Why this formula:** Segments represent direct contribution, ring passes represent trust, drafts contributed show breadth.

---

### 2. Momentum Leaderboard
**Based on:** Existing MomentumScore from Phase 2 service

**Message:** "Momentum matters: sustaining effort over time"

**Insights:**
- Score ≥ 80: "Exceptional momentum—sustaining excellence!"
- Score ≥ 60: "Strong momentum—great consistency!"
- Score ≥ 40: "Growing momentum—keep building!"
- < 40: "Starting to build momentum!"

**Why this formula:** Momentum already captures streak health + consistency—leaderboard just aggregates it.

---

### 3. Consistency Leaderboard
**Based on:** drafts_created × 5 + drafts_contributed × 2

**Message:** "Commitment: showing up, creating, and iterating"

**Insights:**
- Total ≥ 10: "Consistent creator—impressive dedication!"
- Total ≥ 5: "Regular contributor—great habit!"
- < 5: "Building your creation rhythm!"

**Why this formula:** Creating drafts requires starting; contributing shows breadth. Emphasizes long-term habit over viral moments.

---

## Determinism Strategy

All leaderboard computations are deterministic:

```python
def get_leaderboard(metric_type, all_drafts, user_analytics_map, momentum_scores, now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Compute scores
    user_scores = [(score, user_id, analytics) for ...]
    
    # Sort deterministically: by score (descending), then by user_id (tie-breaker)
    user_scores.sort(key=lambda x: (-x[0], x[1]))
    
    # Return top 10 entries
    return leaderboard
```

**Same inputs + same `now` => identical entries in identical order (byte-for-byte).**

This enables:
- Reproducible testing with fixed timestamps
- Cacheability (same leaderboard for same hour)
- Predictable tie-breaking (always by user_id)

---

## Safety Guarantees

### What Never Leaks
- No `token_hash` (internal invite model field)
- No invite tokens
- No email addresses
- No secrets or passwords
- All fields in LeaderboardEntry are safe for public display

### Test Enforcement
```python
def test_leaderboard_entries_have_no_sensitive_fields():
    leaderboard = get_leaderboard(...)
    response_str = str(leaderboard.model_dump())
    
    assert "token_hash" not in response_str
    assert "password" not in response_str
    assert "secret" not in response_str
```

---

## No Engagement Chasing

### What We Avoid
- Likes, hearts, reactions (vanity metrics)
- "You're behind [user]" language
- Ranking by views/followers alone
- Notifications on every engagement ("Someone liked your post!")
- Infinite scroll or algorithmic feed

### What We Emphasize
- Streaks (consistency over time)
- Collaboration (ring passing, contributors)
- Segments written (actual effort)
- Momentum (multi-component score)
- Growth mindset ("building rhythm", "growing skills")

### Leaderboard Copy Examples
✅ **Good:** "Leading by example—great contributions!"  
❌ **Bad:** "You're crushing it! [User] is behind you."

✅ **Good:** "Community highlights: creators shaping work together"  
❌ **Bad:** "Top 10 performers this week"

---

## Frontend Analytics Page

Location: `/dashboard/insights`

### Sections

#### 1. Your Activity
Three cards showing:
- Drafts Contributed (e.g., "3 collaborations")
- Segments Written (e.g., "12 segments")
- RING Held (e.g., "2 times")

Each card includes supportive insight (e.g., "Growing your collaboration skills").

#### 2. Community Momentum
Metric selector (Collaboration | Momentum | Consistency) with leaderboard preview (Top 3 only).

Entries show:
- Position badge (1-10)
- Display name
- Metric label
- Supportive insight

#### 3. Tip
Supportive message: "Insights are here to support your growth, not to measure yourself against others. Focus on consistency and collaboration—everything else follows."

---

## Implementation Details

### Backend Service (`backend/features/analytics/service.py`)

**Key Functions:**

1. `compute_draft_analytics(draft, now=None) -> DraftAnalytics`
   - Uses ring history length for pass count
   - Tracks views/shares from in-memory store
   - Deterministic: same draft + same now => same metrics

2. `compute_user_analytics(user_id, drafts, now=None) -> UserAnalytics`
   - Aggregates across all user drafts
   - Counts segments, rings, contributions
   - Estimates ring hold duration (stub: 30 min per pass)

3. `get_leaderboard(metric_type, all_drafts, user_analytics_map, momentum_scores, now=None) -> LeaderboardResponse`
   - Computes scores based on metric type
   - Sorts deterministically (score desc, user_id asc)
   - Returns top 10 entries with supportive insights

**In-Memory Stubs (Phase 3.5→PostgreSQL):**
- `_draft_views_store`: Dict[draft_id, view_count]
- `_draft_shares_store`: Dict[draft_id, share_count]
- Both cleared via `clear_store()` for testing

---

### Backend API (`backend/api/analytics.py`)

**New Endpoint:**
```
GET /v1/analytics/leaderboard?metric=collaboration&now=ISO(optional)

Response:
{
  "success": true,
  "data": {
    "metric_type": "collaboration",
    "entries": [...],
    "computed_at": "2025-12-21T15:30:00Z",
    "message": "Community highlights: ..."
  }
}
```

---

### Frontend (`src/app/dashboard/insights/page.tsx`)

**Page Features:**
- Server-side rendered with Clerk auth
- Metric selector (controlled state)
- Activity cards (hardcoded for Phase 3.4 stub)
- Leaderboard fetch on metric change
- Error and loading states
- Supportive tip at bottom

**Key Hook:**
```typescript
useEffect(() => {
  if (!isLoaded || !user) return;
  
  const fetchLeaderboard = async () => {
    const res = await fetch(`/api/analytics/leaderboard?metric=${metric}`);
    const data = await res.json();
    setLeaderboard(data);
  };
  
  fetchLeaderboard();
}, [isLoaded, user, metric]);
```

---

### Frontend API Proxy (`src/app/api/analytics/leaderboard/route.ts`)

**Route Handler:**
- Clerk auth required
- Query param: `metric` (collaboration | momentum | consistency)
- Query param: `now` (optional, ISO timestamp)
- Calls backend `/api/analytics/leaderboard`
- Validates response with Zod schema
- Returns validated LeaderboardResponse

**Response Type Export:**
```typescript
export type Leaderboard = z.infer<typeof leaderboardSchema>;
```

---

## Test Coverage

### Backend Tests (20+)

**TestDraftAnalyticsDeterminism:**
- Same draft + same time => identical analytics
- Different time => different computed_at, same metrics

**TestDraftAnalyticsBounds:**
- Views, shares, ring_passes are non-negative
- Contributors count >= 1 (creator always included)

**TestUserAnalyticsDeterminism:**
- Same user + same drafts + same time => identical analytics
- User with no drafts has all zeros

**TestLeaderboardDeterminism:**
- Same metric + same time => same entries in same order
- Leaderboard entries max 10

**TestLeaderboardSafety:**
- No token_hash in response
- No password, secret keywords
- All fields safe for public display

**TestLeaderboardMessages:**
- Message never contains "you're behind", "catch up", "falling behind"
- All insights are supportive

### Frontend Tests (18)

**SchemaValidation (4):**
- Valid leaderboard entry passes schema
- Invalid position (>10) rejected
- Null avatar_url accepted
- Invalid metric_type rejected

**MetricsBounds (6):**
- metric_value is numeric
- Zero metric_value accepted
- Large metric_values accepted
- Position range 1-10 enforced

**Safety (3):**
- No sensitive keywords in metric_label
- Display name not an email
- Insight never comparative

**HelperFunctions (3):**
- Position formatting (medals)
- Metric label formatting (bullet replacement)
- Display name truncation

**MetricTypes (2):**
- All three metric types supported
- Invalid metric_type rejected

---

## Known Limitations (Honest)

### Phase 3.4 Stubs
- **Display names:** `user_XXXXXXXX` (Phase 3.5 will be real names from Clerk)
- **Avatars:** All null (Phase 3.5 will pull from Clerk)
- **Activity cards:** Hardcoded (Phase 3.5 will compute from drafts)
- **Views/shares:** Only updated via `record_draft_view()` calls (not auto-tracked yet)

### In-Memory Stores
- Data lost on server restart
- Not suitable for multi-instance deployment (no shared Redis yet)
- Phase 3.5 migration to PostgreSQL planned

### No Real-Time Updates
- Leaderboard is static snapshot (no WebSocket updates)
- Frontend must manually refresh for latest rankings

### Momentum Integration
- Momentum scores assumed pre-computed (Phase 3.4 accepts dict as parameter)
- Real leaderboard will fetch from momentum service

---

## Next Steps (Phase 3.5)

1. **PostgreSQL Migration**
   - Create tables: analytics_event, leaderboard_cache
   - Migrate in-memory stores to database
   - Add indexes for leaderboard queries

2. **Real-Time Event Tracking**
   - Track draft views, shares, segment additions
   - Aggregate into event log
   - Compute metrics from events

3. **Display Names & Avatars**
   - Fetch from Clerk in leaderboard query
   - Cache for performance
   - Fallback to user_id if unavailable

4. **Leaderboard Caching**
   - Pre-compute hourly snapshots
   - Store in database
   - Serve cached version until next hour

---

## References

- `backend/models/analytics.py` — Model definitions
- `backend/features/analytics/service.py` — Deterministic computation
- `backend/api/analytics.py` — API endpoints
- `backend/tests/test_analytics.py` — 20+ tests
- `src/app/dashboard/insights/page.tsx` — Frontend page
- `src/app/api/analytics/leaderboard/route.ts` — Frontend API proxy
- `src/__tests__/analytics.spec.ts` — 18 frontend tests
