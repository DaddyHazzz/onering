# ONERING PROJECT CONTEXT (CANONICAL — MATCHES PROJECT_STATE)

**Last Updated:** December 21, 2025  
**Status:** Phase 3.3c Complete; Phase 3.4 COMPLETE (Analytics + Leaderboard)  
**Test Suite:** Backend analytics: 49 tests passing; Frontend: 298 tests passing (analytics included)

---

## 0. Canon & Guardrails

OneRing is a creator-first collaboration platform where users build daily streaks, receive momentum coaching, collaborate on shared drafts (via RING token social proof), and track progress deterministically. **The canonical source of truth is `PROJECT_STATE.md`.** If this file conflicts with PROJECT_STATE, PROJECT_STATE wins. Do not invent implemented features. If uncertain, label as "Planned" or "Stubbed."

### What Is Implemented (Phase 1-3)
- ✅ Daily streaks + momentum scoring (Phase 1)
- ✅ Public profiles + archetype detection (Phase 2)
- ✅ Collaborative threads + RING passing (Phase 3.1)
- ✅ Secure invite flow (one-time tokens, no exposure) (Phase 3.2)
- ✅ Invite accept UX + presence tracking (Phase 3.3)
- ✅ Share cards v2 with full attribution + ring velocity (Phase 3.3c)

### What Is Planned / In Progress / Not Yet Implemented
- ✅ Analytics + leaderboards (Phase 3.4 implemented: deterministic reducers, endpoints + proxies, supportive UI)
- ⏳ PostgreSQL persistence layer (Phase 3.5)
- ⏳ Multi-platform publishing (X, IG, LinkedIn) (Phase 4)
- ⏳ Temporal.io durable workflows (future)
- ❌ RING token smart contract (NOT STARTED)
- ❌ Advanced ML personalization (NOT STARTED)

### Do Not Hallucinate
- No real-time WebSocket presence (polling only, 5-second cadence)
- No multi-instance database persistence yet (in-memory stores)
- No image rendering for share cards (JSON only)
- No Instagram Graph API integration (stub/mock ready)
- No Stripe/payments integration (NOT IMPLEMENTED — listed in DESIGN_DECISIONS aspirationally, but not active in PROJECT_STATE)
- No referral system, RING staking, family pools (NOT IMPLEMENTED — listed in DESIGN_DECISIONS aspirationally, but PROJECT_STATE does not claim them)

---

## 1. Product Identity (No-Dark-Patterns Contract)

- **Momentum over vanity:** Streaks, consistency, and effort are rewarded. Likes, views, and followers are tracked but never featured as leaderboard drivers.
- **Determinism first:** Same input + same timestamp = same output, always. This enables reproducible testing and predictable user experience.
- **No shame language:** System never compares users ("you're behind X"), never amplifies self-doubt, never uses "catch up" or "falling behind" language.
- **Authentic attribution:** Collaborative work credits all contributors fairly. RING passing is transparent.
- **Safety-first secrets:** No API response ever leaks token_hash, invite tokens, emails, passwords, or secrets. Internal models (with secrets) are separated from public models.
- **Anti-dark-patterns:** No infinite scroll, no addictive notifications, no engagement chasing. User experience is clear, supportive, and growth-oriented.

---

## 2. Architecture Snapshot (Reality, Not Aspirational)

### Backend: FastAPI (Python)
- **Framework:** FastAPI with async/await
- **Agents:** LangGraph orchestration planned for Phase 4+; NOT currently used for core collaboration logic
- **Auth:** Clerk (user metadata in `publicMetadata`)
- **Persistence:** In-memory stores (STUB for Phase 3.5 PostgreSQL)
  - `_drafts_store: dict[str, Draft]`
  - `_idempotency_keys: dict[str, bool]`
  - `_collaborators_store: dict[str, list[Collaborator]]`
  - (Marked with `# STUB: Phase 3.5 PostgreSQL` in code)
- **Exports:** Frozen Pydantic models (immutable contracts) for all API responses
- **Time handling:** UTC timestamps, optional `now` query param for deterministic testing
- **Timezone:** All calculations in UTC; `now` parameter enables fixed-time testing

### Frontend: Next.js 16 (App Router)
- **Framework:** React 19 + Next.js 16 App Router
- **Auth:** Server-side Clerk integration (`currentUser()` in routes)
- **Validation:** Zod schemas for all API responses (runtime safety)
- **Type Safety:** TypeScript strict mode, no `any` types
- **Styling:** Tailwind CSS (utility-first)
- **Components:** Modal-first UX (share cards, coach, invites)
- **Side Effects:** All imports isolated, no fetch() in module scope

### Current Stack Summary
```
┌─────────────────────────────────┐
│  Frontend (Next.js 16 App)      │
│  React 19, TypeScript, Tailwind │
│  Clerk auth (server-side)       │
│  Zod validation at boundary     │
└─────────────┬───────────────────┘
              │ HTTP
              ↓
┌─────────────────────────────────┐
│  Backend (FastAPI)              │
│  Python 3.10+, Pydantic v2      │
│  In-memory stores (STUB)        │
│  Frozen response models         │
│  Deterministic services         │
└─────────────────────────────────┘
```

**No LLM in Core Logic:** Coach, momentum, and metrics use deterministic heuristics only. Groq integration is deferred to Phase 4+.

**No WebSocket Presence:** Presence indicators update via 5-second polling, not real-time WebSocket.

---

## 3. Determinism Rules (Hard Requirements)

### The Pattern: Optional `now` Parameter

All time-dependent computations accept an optional `now` parameter (ISO 8601 timestamp). If not provided, the system uses current time.

```python
# Backend service
def compute_metrics(draft: Draft, now: Optional[datetime] = None) -> Metrics:
    if now is None:
        now = datetime.now(timezone.utc)
    
    ring_passes_24h = count_passes_in_window(draft, now - timedelta(hours=24), now)
    return Metrics(ring_passes_24h=ring_passes_24h, computed_at=now)
```

```typescript
// Frontend query
GET /v1/collab/drafts/{draftId}/share-card?now=2025-12-21T15:30:00Z
```

### Guarantee: Byte-for-Byte Identity

**Same inputs + same `now` timestamp => Identical output** (reproducible byte-for-byte).

Test pattern:
```python
def test_deterministic_share_card():
    fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
    
    card1 = generate_share_card("draft-123", now=fixed_time)
    card2 = generate_share_card("draft-123", now=fixed_time)
    
    assert card1.model_dump_json() == card2.model_dump_json()
```

### Rules (Enforced)

- ✅ **No `time.now()` in business logic** — use `now` param instead
- ✅ **All time zones are UTC** — never store or compare local times
- ✅ **Sorting is deterministic** — tie-breaking uses `user_id` (stable order)
- ✅ **Tests use fixed `now`** — enables repeatability
- ✅ **Backward compatible** — `now` param is optional; production omits it

---

## 4. Analytics & Leaderboards (Phase 3.4) — Event Reducers

### 4.1 Event Schema (Implemented)

Analytics derives from append-only events defined in `.ai/domain/events.md` (see file for canonical schema). Implemented events:
- `DraftCreated(draft_id, creator_id, created_at)`
- `DraftViewed(draft_id, user_id, viewed_at)`
- `SegmentAdded(draft_id, segment_id, contributor_id, added_at)`
- `RingPassed(from_user_id, to_user_id, draft_id, passed_at)`
- `DraftPublished(draft_id, published_at)`

**Idempotency:** Each event includes a unique key; views use `(draft_id, user_id, viewed_at_bucket)`.

### 4.2 Event Store (Current)

**Status:** In-memory, Phase 3.4 design phase.

Planned interface:
```python
class EventStore:
    def append(event: Event, idempotency_key: str) -> bool:
        """Append event; return False if idempotency key seen before."""
    
    def get_events(start_time, end_time) -> List[Event]:
        """Retrieve events in time window."""
    
    def clear() -> None:  # Testing only
```

**Current limitation:** All events lost on server restart. Phase 3.5 will persist to PostgreSQL.

### 4.3 Reducers (Pure Functions)

Reducers are pure, deterministic functions: `reduce(events, now) -> ReadModel`

Planned reducers:

**reduce_draft_analytics(draft_id, events, now)**
- Inputs: List of events, fixed `now` timestamp
- Computation: Views (count unique `DraftViewed`), Shares, Ring passes in last 24h, contributor count
- Output: `DraftAnalytics` (immutable Pydantic model)
- Property: Same events + same `now` => identical `DraftAnalytics`

**reduce_user_analytics(user_id, events, now)**
- Inputs: All user-related events
- Computation: Drafts created, segments written, rings held, average hold duration
- Output: `UserAnalytics`
- Property: Deterministic aggregation

**reduce_leaderboard(metric_type, all_events, all_drafts, now)**
- Inputs: `metric_type` ∈ {collaboration, momentum, consistency}, all events, timestamp
- Computation:
  - **Collaboration:** segments_written×3 + rings_held×2 + drafts_contributed
  - **Momentum:** pre-computed MomentumScore (Phase 2)
  - **Consistency:** drafts_created×5 + drafts_contributed×2
- Sorting: Score descending, user_id ascending (tie-breaker)
- Output: `LeaderboardResponse` (top 10 entries max, supportive insights)
- Property: Deterministic ordering

**reduce_insights(metric_type, position, score)**
- Inputs: Position (1-10), score, metric type
- Output: String insight (supportive, growth-focused)
- Examples:
  - Position 1: "Leading by example—great contributions!"
  - Position 2-3: "Strong momentum—keep building!"
  - Position 4-10: "You're growing your impact!"
- Property: Never comparative, never shaming

### 4.4 API Surface (Read Models Only)

All endpoints return **read models only**, no raw events.

Planned endpoints:

**GET `/v1/collab/drafts/{draftId}/analytics`**
- Query params: `now` (optional, ISO)
- Returns: `DraftAnalytics` (views, shares, ring_passes_24h, contributors, last_activity)
- Safety: No internal IDs, no token_hash, no secrets

**GET `/v1/analytics/leaderboard?metric={collaboration|momentum|consistency}&now={ISO}`**
- Returns: `LeaderboardResponse`
- Schema:
  ```json
  {
    "metric_type": "collaboration",
    "entries": [
      {
        "position": 1,
        "user_id": "user-xyz",
        "display_name": "Creator Name",
        "avatar_url": "https://...",
        "metric_value": 150,
        "metric_label": "15 segments • 3 rings",
        "insight": "Leading by example!"
      }
    ],
    "computed_at": "2025-12-21T15:30:00Z",
    "message": "Community highlights: creators shaping work together"
  }
  ```
- Constraints:
  - Max 10 entries (prevents "rank shame")
  - Insights are supportive, never comparative
  - No sensitive fields (token_hash, invite tokens, emails)

### 4.5 Anti-Shame Constraints for Leaderboards

- ✅ **No vanity metrics:** Leaderboards never feature likes, views, followers as primary score
- ✅ **No harassment:** Display names only (no emails), no "catching up" language
- ✅ **No shame language:** "You're behind X by Y" is forbidden; compare to self ("your growth this week")
- ✅ **Avoid over-precision:** Metric values rounded (e.g., "~45 segments" not "45.3")
- ✅ **Avoid addictive loops:** No notifications on leaderboard changes, no real-time ranking updates

---

## 5. Backend Extension Points (How to Add Features Safely)

### Where to Plug In New Reducers
**File:** `backend/features/analytics/service.py`
- Define reducer function: `reduce_X(events, now) -> ReadModel`
- Ensure deterministic (pure function, no IO, no randomness)
- Add unit tests with fixed `now` parameter

### Where to Plug In Event Emitters
**File:** `backend/api/collaboration.py` (when applicable)
- On significant action (ring pass, segment added, draft published), call:
  ```python
  events.append(Event(...), idempotency_key=...)
  ```
- Idempotency key prevents double-processing

### Where to Plug In Scoring Rules
**File:** `backend/features/analytics/service.py`
- Update reducer to include new score component
- Update formulas in documentation
- Add tests for new score bounds

### Where to Plug In API Endpoints
**File:** `backend/api/analytics.py`
- New endpoint that calls reducer(s)
- Accept `now` query param
- Return read model (Pydantic frozen model)
- Add safety tests (no token_hash, no emails, no secrets)

### Where to Add Tests
**File:** `backend/tests/test_analytics.py`
- Determinism tests (same input + time => same output)
- Bounds tests (values in expected ranges)
- Safety tests (no sensitive keyword leakage)
- Content tests (insights are supportive, not comparative)

---

## 6. LLM Usage Policy (Reconciled & Test-Safe)

### One Crisp Rule

**"LLM can draft and suggest; scoring, awards, and eligibility are deterministic reducers only."**

Detailed policy:

- ✅ **LLM outputs are advisory:** Coach suggestions, content drafts, and title recommendations may come from LLM
- ✅ **Never direct state change:** LLM output never directly awards RING, changes score, or unlocks features
- ✅ **Deterministic gatekeeping:** All rewards, eligibility, and ranking computed by deterministic reducer logic from events
- ✅ **Orchestration only:** If LangGraph is used, it orchestrates drafting/suggestion agents only—not final scoring or eligibility
- ✅ **Test-safe:** All scoring paths have deterministic tests (fixed `now`, fixed events => fixed output)

**Example flow (Phase 4+):**
```
User input → LLM generates suggestion → User accepts/edits → Deterministic reducer awards RING based on metrics
```

LLM never creates the RING award itself; the reducer does.

---

## 7. Testing Contract (Reality + Enforcement)

### Per-Route Requirements (Backend)

Every new API route must have (per `TESTING_CONTRACT.md`):
1. One unauthenticated test (401 Unauthorized)
2. One validation error test (400 Bad Request)
3. One success test (200 OK)

### Test Patterns

**Determinism Test:**
```python
def test_deterministic_metric():
    fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
    result1 = compute_metric(draft, now=fixed_time)
    result2 = compute_metric(draft, now=fixed_time)
    assert result1 == result2
```

**Safety Test:**
```python
def test_no_token_hash_in_response():
    response = client.get("/v1/analytics/leaderboard")
    payload = str(response.json()["data"])
    assert "token_hash" not in payload
    assert "password" not in payload
    assert "secret" not in payload
```

**Bounds Test:**
```python
def test_metric_values_in_bounds():
    result = reduce_leaderboard("collaboration", events, now)
    assert all(0 <= e.metric_value <= 1000 for e in result.entries)
    assert len(result.entries) <= 10
```

### Current Coverage

| Category | Count | Status |
|----------|-------|--------|
| Backend tests | 226 | ✅ All passing (including analytics: 49) |
| Frontend tests | 298 | ✅ All passing (including analytics UI/route suites) |
| Phase 3.4 tests | 49 backend + analytics-related frontend included | ✅ Complete |
| **Total** | **Stable** | **Project tests green** |

---

## 8. Roadmap Alignment (What's Next)

### Phase 3.4 — Analytics + Leaderboard (JAN 2026)
- Design event schema (`.ai/domain/events.md`)
- Implement reducers (deterministic, testable)
- API endpoints for metrics + leaderboards
- Supportive insights (no shame language)
- 20+ backend tests + 18+ frontend tests
- **Must happen before Phase 3.5**

### Phase 3.5 — Persistence Layer (JAN-FEB 2026)
**Critical blocker for multi-instance deployment:**
- PostgreSQL schema (Prisma)
- Migrate in-memory stores to database
- Event store implementation
- pgvector column for embeddings
- Query optimization (indexes, connection pooling)
- **Requirement:** All existing tests must pass with Prisma models

### Phase 4 — Publishing + Scheduling (FEB-MAR 2026)
- X/Twitter API integration (thread posting)
- Instagram Graph API integration
- Schedule UI (date/time picker)
- Background jobs for scheduled publishing
- Multi-platform batch posting

### Stability & Polish (Ongoing)
- Performance profiling and query optimization
- Better error messages (user-friendly, not stack traces)
- Documentation expansion (API reference, contributor guide)
- Internal analytics (uptime, error rates, latency)

---

## 9. Glossary (Short)

- **Draft:** Shared collaborative document (threads, posts, content pieces)
- **RING:** Social proof token earned through collaboration (ring passing) and consistency (streaks)
- **Segment:** Atomic unit within a draft (one paragraph, one tweet, etc.)
- **Momentum:** Composite score from streaks, challenge completion, and contribution history
- **Event:** Append-only fact (e.g., `DraftViewed`, `RINGPassed`, `SegmentAdded`)
- **Reducer:** Pure function: `reduce(events, now) -> ReadModel` (deterministic aggregation)
- **Read Model:** Immutable DTO (Pydantic frozen model) returned by API
- **Idempotency Key:** Unique identifier preventing duplicate event processing
- **Now Parameter:** Optional ISO timestamp for fixed-time testing and determinism
- **Determinism:** Same inputs + same timestamp = identical output (reproducible, testable)

---

## 10. Architecture Patterns (Copy These)

### Backend Service Pattern
```python
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ServiceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)  # Immutable
    value: float
    computed_at: datetime

def compute_metric(data: dict, now: Optional[datetime] = None) -> ServiceResponse:
    if now is None:
        now = datetime.now(timezone.utc)
    
    value = compute_value(data)  # Pure logic, no randomness
    return ServiceResponse(value=value, computed_at=now)
```

### API Endpoint Pattern
```python
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter()

@router.get("/v1/metric/{id}")
async def get_metric(
    id: str,
    now: Optional[str] = Query(None),  # Optional ISO timestamp
):
    if now:
        now_dt = datetime.fromisoformat(now)
    else:
        now_dt = None
    
    result = compute_metric(id, now=now_dt)
    return {"success": True, "data": result}
```

### Frontend Validation Pattern
```typescript
import { z } from "zod";

const leaderboardSchema = z.object({
  metric_type: z.enum(["collaboration", "momentum", "consistency"]),
  entries: z.array(
    z.object({
      position: z.number().int().min(1).max(10),
      metric_value: z.number().min(0),
      insight: z.string().refine((s) => !s.includes("you're behind")),
    })
  ),
});

type Leaderboard = z.infer<typeof leaderboardSchema>;
```

---

## Known Technical Debt

### In-Memory Stores (Phase 3.5)
- Data lost on server restart
- No multi-instance support
- No query optimization
- **When fixed:** Phase 3.5 (PostgreSQL migration)

### Polling-Based Presence (Phase 3.5+)
- Typing indicators have 5-second latency
- Frontend polls every 5 seconds
- Multiplayer experience feels sluggish
- **When fixed:** Phase 3.5+ (optional WebSocket)

### No Real-Time Leaderboard (Phase 3.5+)
- Leaderboard snapshot is static
- Users must refresh for latest rankings
- No WebSocket broadcasts
- **When fixed:** Phase 3.5+ (optional, depends on feedback)

### Share Cards Are JSON-Only (Phase 4)
- No OG image generation
- No Twitter card preview images
- Links show generic preview
- **When fixed:** Phase 4 (with publishing feature)

---

## Quick Reference: File Locations

**Backend (Python)**
- Models: `backend/models/` (collaboration.py, momentum.py, etc.)
- Services: `backend/features/{domain}/service.py`
- API routes: `backend/api/{domain}.py`
- Tests: `backend/tests/test_{domain}.py`

**Frontend (TypeScript)**
- Pages: `src/app/dashboard/{feature}/page.tsx`
- API proxies: `src/app/api/{feature}/route.ts`
- Components: `src/components/{Component}.tsx`
- Tests: `src/__tests__/{feature}.spec.ts`
- Schemas: `src/lib/validation.ts`

**Documentation**
- Product vision: `.ai/PRODUCT_VISION.md`
- Roadmap: `.ai/ROADMAP.md`
- Testing contract: `.ai/TESTING_CONTRACT.md`
- Design decisions: `DESIGN_DECISIONS.md`
- Project state (canon): `PROJECT_STATE.md`

---

**This document is authoritative for AI agents and developers. Update immediately after merging any feature change, new phase completion, or architectural decision.**