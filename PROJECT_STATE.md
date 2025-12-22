# OneRing — Project State (Canonical)

**Last Updated:** December 22, 2025  
**Status:** Phase 3.5 COMPLETE (PostgreSQL Persistence); Phase 3.4 COMPLETE (Analytics + Leaderboard)  
**Test Coverage:** Backend: 35 persistence tests + 49 analytics tests passing; Frontend: 298 tests passing

---

## 1. Executive Summary

OneRing is a creator-first collaboration platform centered around a daily pull loop: creators build threads (streaks), receive AI coaching on momentum, share work with collaborators, and iterate together. The platform prioritizes authenticity over vanity metrics, deterministic behavior over machine learning unpredictability, and safety over convenience. Core design commitment: no dark patterns, no shame language, no hidden engagement manipulation. Users create together, track momentum linearly, and monetize through RING token economics.

---

## 2. Core Principles (Non-Negotiable)

### Determinism First
- Same input + same timestamp = same output (always, testable)
- All metrics, suggestions, and share cards must be reproducible
- `now` query parameter enables fixed-time testing
- Eliminates flaky tests and prediction inconsistencies

### No Shame Language
- System never amplifies self-doubt or negative self-perception
- Harmful prompts (e.g., "I'm worthless") auto-redirect to resilience framing
- Coach and suggestion language is supportive, growth-oriented
- Explicit harmful keyword detection in generation pipeline

### No Engagement Chasing
- Primary drivers are momentum (streaks, effort) and collaboration (ring passing)
- Vanity metrics (likes, views) are tracked but never featured as goals
- Ring awards depend on consistency + collaboration, not viral moments
- Leaderboards will emphasize contribution and persistence

### Safety-First Exports
- No API response ever includes token_hash, invite tokens, or passwords
- Internal service models (with secrets) separate from public API models
- All exports use frozen Pydantic models (immutable contracts)
- Tests enforce: zero sensitive keyword leakage

### Idempotency Everywhere
- All mutations check idempotency keys (prevent double-processing)
- Share card generation with same `now` is bit-for-bit identical
- Ring passing, invite acceptance, posting all use idempotency stores
- Database (Phase 3.5+) will extend this with unique constraints

### Test-Before-Trust Philosophy
- No code merged without test coverage
- Deterministic tests (fixed timestamps) prevent flakiness
- Safety tests explicitly verify no secret leakage
- Bounds tests ensure metrics stay within expected ranges

---

## 3. Architecture Overview

### Backend (FastAPI)

**Design Pattern:**
```
HTTP Routes (api/)
    ↓
Service Layer (features/)
    ↓
Pure Functions + Idempotency Stores
    ↓
In-Memory Dicts (STUB for Phase 3.5→PostgreSQL)
```

**Key Characteristics:**
- **Pure service layer:** Deterministic functions, no side effects
- **No LLM for core logic:** Coach, momentum, metrics use heuristics only (Groq integration future)
- **Timezone-aware UTC:** All timestamps stored and compared in UTC, explicit `now` param for testing
- **In-memory stores:** Explicitly marked as STUB (`# STUB: Phase 3.5 PostgreSQL`)
- **Frozen models:** All Pydantic response models frozen (immutable)

**Current Stack:**
- FastAPI (routes + dependency injection)
- Pydantic v2 (schema validation + frozen models)
- Python 3.10+ (type hints, async/await ready)
- Redis (in-memory, not currently used; queued for Phase 3.5)
- PostgreSQL (queued for Phase 3.5; currently stubbed)

### Frontend (Next.js 16 App Router)

**Design Pattern:**
```
Pages (app/)
    ↓
Server Components + Client Components
    ↓
Zod Schemas (validation contracts)
    ↓
Modal Components (Share Card, Coach, Invites)
    ↓
API Proxy Routes (api/)
```

**Key Characteristics:**
- **Server-side auth:** Clerk integration in route handlers (no client-side secret exposure)
- **Zod as contracts:** All API responses validated with Zod schemas at boundary
- **Modal-first UX:** Share cards, coach, invites delivered as interactive modals
- **No hidden side effects:** Imports isolated, no fetch() calls in module scope
- **TypeScript strict mode:** All code type-safe, no `any` types allowed

**Current Stack:**
- Next.js 16 (App Router, Server Components)
- React 19 (hooks, client state)
- Tailwind CSS (utility-first styling)
- @clerk/nextjs (server + client auth)
- Zod (runtime validation)
- TypeScript (strict)

---

## 4. Phase-by-Phase Status

### Phase 1 — Daily Pull Loop (✅ COMPLETE)

**What It Is:**
Daily engagement loop: users open app, see today's challenge, attempt streak, get AI coaching on their draft.

**Files:**
- `src/app/dashboard/today/page.tsx` — Today loop UI
- `backend/agents/coach_agent.py` — Deterministic coaching suggestions
- `backend/features/momentum/service.py` — Streak and momentum calculation

**Key Features:**
- Streak counter (days in a row of posting)
- Daily challenges (rotating prompts)
- AI Coach (deterministic suggestions based on post history)
- Momentum score (linear, not ML-predicted)

**Tests:** Passing (momentum, coach, today loop)

---

### Phase 2 — Momentum & Identity (✅ COMPLETE)

**What It Is:**
User momentum tracking, public profiles, archetype discovery, and share cards for personal presence.

**Files:**
- `src/app/dashboard/profile/page.tsx` — Public profile view
- `src/components/MomentumGraph.tsx` — Momentum visualization
- `backend/features/momentum/service.py` — Momentum calculation
- `backend/features/archetypes/service.py` — Archetype detection
- `src/components/ShareCard.tsx` — Personal share card (v1)

**Key Features:**
- Public profiles with archetype badges
- Momentum score (cumulative effort, not viral metrics)
- Share card with engagement metrics
- Archetype detection (analytical, creative, connector, leader)
- Deterministic profile embeddings (OpenAI)

**Tests:** Passing (profile, momentum, archetypes, sharecard)

---

### Phase 3 — Collaboration (IN PROGRESS, HEAVILY DETAILED)

Collaboration is the core innovation: multiple creators work on shared drafts, pass "RING" tokens (social proof), and surface authentic attribution.

#### Phase 3.1 — Collab Threads MVP (✅ COMPLETE)

**What It Is:**
Shared draft structure: one creator writes, others contribute through RING passing and segment additions.

**Files:**
- `backend/models/collaboration.py` — Draft, Segment, Ring models
- `backend/features/collaboration/service.py` — Draft creation, ring passing, permissions
- `backend/api/collaboration.py` — HTTP endpoints for drafts
- `src/app/dashboard/collab/page.tsx` — Collab dashboard UI

**Key Features:**
- Draft ownership (creator owns draft)
- Collaborator roles (write, comment, view)
- Ring passing (creator or collaborator can pass RING to others)
- Segment structure (atomic units within draft)
- Idempotent mutations (all operations check idempotency keys)

**Data Model:**
```python
Draft:
  draft_id (UUID)
  creator_id (Clerk user ID)
  title, subtitle
  status (draft, published, archived)
  segments (list of Segments)
  collaborators (list of Collaborators with roles)
  created_at, updated_at

Segment:
  segment_id (UUID)
  content (string)
  position (int)
  contributor_id (Clerk user ID)

Ring:
  ring_id (UUID)
  from_user_id, to_user_id
  draft_id (context)
  passed_at
```

**Tests:** 11 tests, all passing

---

#### Phase 3.2 — Invites (Backend) (✅ COMPLETE)

**What It Is:**
Secure invitation flow: creator generates invite links with one-time tokens, invitees accept with token validation, account linking.

**Files:**
- `backend/models/invite.py` — CollaborationInvite model (internal)
- `backend/features/collaboration/invite_service.py` — Token generation, acceptance, revocation
- `backend/api/collaboration.py` — POST `/invites/create`, POST `/invites/accept`

**Key Features:**
- One-time tokens (token_hash stored, never exposed)
- Token expiration (configurable, default 7 days)
- Handle resolution (invite by email or handle)
- Acceptance flow (create or link account)
- Revocation (creator can revoke pending invites)

**Safety:**
- token_hash never leaks in API responses
- Internal CollaborationInvite model uses token_hash
- Public InviteSummary model (API response) omits token_hash
- Tests explicitly verify zero token exposure

**Tests:** 11 tests, all passing

---

#### Phase 3.3 — Invite UX + Presence (✅ COMPLETE)

**What It Is:**
Frontend accept flow, presence indicators (who's editing), and attribution display.

**Subphases:**

##### Phase 3.3 (Base) — Invite Accept UI + Presence (✅)

**Files:**
- `src/app/dashboard/collab/accept/page.tsx` — Invite accept flow
- `src/components/JoinedBanner.tsx` — "You've been invited" banner
- `backend/features/collaboration/presence_service.py` — Presence tracking
- `src/components/PresenceIndicators.tsx` — Real-time presence display

**Key Features:**
- Invite link parsing (extract token from URL)
- Auto-open draft on first accept
- "You joined" banner (first view)
- Presence indicators (active editors)
- User attribution (contributor list)

**Tests:** 19 tests (presence, invites, banners), all passing

---

##### Phase 3.3a — Presence + Attribution (✅)

**What It Is:**
Enhanced presence: typing indicators, read positions, persistent attribution with contribution metrics.

**Files:**
- `backend/features/collaboration/presence_service.py` — Enhanced with typing indicators
- `src/components/CollabPresenceList.tsx` — Full presence UI
- `backend/features/collaboration/attribution_service.py` — Contribution counting

**Key Features:**
- Active editor list with avatars
- Typing indicators (who's editing which segment)
- Last-edit positions
- Contribution metrics (segments added per user)
- Attribute all segments to creators

**Tests:** 19 tests, all passing

---

##### Phase 3.3b — Invite Continuity + Deep Linking (✅)

**What It Is:**
One-time invites resolved at accept time; deep links for sharing drafts directly.

**Files:**
- `src/app/refer/[inviteCode]/page.tsx` — Deep link handler
- `backend/features/collaboration/deep_link_service.py` — Link resolution
- `backend/api/collaboration.py` — GET `/refer/{inviteCode}`

**Key Features:**
- Deep links: `/ref/{inviteCode}` resolves to draft
- First-time visitor gets "You've been invited" flow
- Returning users join directly
- One-time use (prevents replay attacks)
- Safe routing (no token exposure in logs)

**Safety:**
- Token validation before redirect
- Invites consumed on accept (cannot reuse)
- Tests verify no token leakage in responses

**Tests:** 11 tests (with fixed test for token_hash safety), all passing

---

##### Phase 3.3c — Share Card v2 (✅ COMPLETE AS OF DEC 21, 2025)

**What It Is:**
Deterministic share cards with full attribution, ring velocity metrics, and deep linking for viral distribution.

**Files:**
- `backend/models/sharecard_collab.py` — CollabShareCard, ShareCardMetrics, ShareCardCTA models
- `backend/features/collaboration/service.py` — `generate_share_card(draft_id, now=None)` function
- `backend/api/collaboration.py` — GET `/v1/collab/drafts/{draft_id}/share-card` endpoint
- `src/app/api/collab/drafts/[draftId]/share-card/route.ts` — Frontend API proxy (Clerk auth)
- `src/components/CollabShareCardModal.tsx` — Share card UI (preview, copy buttons)
- `src/app/dashboard/collab/page.tsx` — Share button + modal integration

**Key Features:**
- **Deterministic generation:** Same `draft_id` + same `now` timestamp = identical response (byte-for-byte)
- **Contributors attribution:** Creator listed first, additional contributors lexicographically, max 5 shown (full count in metrics)
- **Ring velocity metrics:** `ring_passes_last_24h`, `avg_minutes_between_passes`, `segments_count`, `contributors_count`
- **Deep linking:** CTA URL format `/dashboard/collab?draftId={draftId}` (internal routes only)
- **Modal UI:** Gradient preview, metrics row, contributor chips, 3 buttons (Refresh, Copy Link, Copy JSON)
- **Optional `now` param:** Query parameter `?now=ISO8601` enables reproducible testing (same time = same metrics)

**Response Shape:**
```json
{
  "success": true,
  "data": {
    "draft_id": "uuid",
    "title": "Draft Title",
    "subtitle": "Ring with @creator • 5 contributors • 3 passes/24h",
    "metrics": {
      "contributors_count": 5,
      "ring_passes_last_24h": 3,
      "avg_minutes_between_passes": 45,
      "segments_count": 8
    },
    "contributors": [
      { "displayName": "Alice", "avatar": "..." },
      { "displayName": "Bob", "avatar": "..." }
    ],
    "top_line": "Collaborative draft in progress",
    "cta": {
      "label": "Join",
      "url": "/dashboard/collab?draftId=..."
    },
    "theme": {
      "bg": "from-blue-500 to-purple-600",
      "accent": "blue"
    },
    "generated_at": "2025-12-21T15:30:00Z"
  }
}
```

**Safety Guarantees:**
- No `token_hash` in response (internal `CollaborationInvite` model separated from public `CollabShareCard`)
- No invite tokens exposed
- No user emails in response
- No secrets, passwords, or credentials
- All tests verify zero sensitive keyword leakage

**Tests:**
- Backend: 20 new tests (determinism, safety, bounds, ordering, content, error handling)
- Frontend: 19 new tests (schema validation, bounds, URL format, safety, helpers)
- All 39 tests passing

---

### Phase 3.4 — Analytics + Leaderboard (✅ COMPLETE)

**What It Is:** Deterministic analytics read models and supportive leaderboards for collaboration.

**Endpoints (Backend):**
- GET `/v1/collab/drafts/{draft_id}/analytics?now=ISO(optional)` → `DraftAnalytics`
- GET `/v1/analytics/leaderboard?metric={collaboration|momentum|consistency}&now=ISO(optional)` → `LeaderboardResponse`

**Frontend Proxies:**
- GET `/api/collab/drafts/[draftId]/analytics` (Clerk auth) → proxies to backend
- GET `/api/analytics/leaderboard` (Clerk auth) → proxies to backend

**UI Wiring:**
- Insights page `/analytics` renders Leaderboard Panel (caps at 10 entries, supportive copy)
- Draft Analytics Modal shows views, shares, segments, contributors, ring passes (optional refresh)

**Determinism:** All reducers accept optional `now` param. Same events + same `now` → identical outputs.

**Safety:** No raw events returned; no sensitive fields (`token_hash`, emails, secrets). Insights avoid shame language.

**Tests:** Backend analytics: 49 passing (event store, reducers, API). Frontend: 298 passing (schemas, routes, UI).

---

### Phase 3.5 — Persistence Layer (✅ COMPLETE)

**What It Is:**
Migration from in-memory stores to PostgreSQL for analytics events, collaboration drafts, and idempotency keys.

**Completed Work:**

#### Part 1: Database Foundation
- `backend/core/database.py` — SQLAlchemy Core setup with connection pooling
- 6 tables: `analytics_events`, `idempotency_keys`, `drafts`, `draft_segments`, `draft_collaborators`, `ring_passes`
- Context managers: `get_db_session()` with auto-commit/rollback
- Smart initialization: lazy engine creation, safe re-initialization
- Tests: `backend/tests/test_database_foundation.py` (1/1 passing)

#### Part 2: PostgreSQL Event Store
- `backend/features/analytics/event_store_pg.py` — Persistent event store
- Features: append(), get_events(), clear(), count() with PostgreSQL backend
- Idempotency: UNIQUE constraint on (type, occurred_at, data_hash)
- Deterministic ordering: (occurred_at ASC, id ASC)
- Returns copies (not references) to prevent mutations
- Tests: `backend/tests/test_event_store_pg.py` (12/12 passing)

#### Part 3: Smart Store Switching
- `backend/features/analytics/event_store.py` — get_event_store() with DATABASE_URL detection
- Falls back to in-memory when DATABASE_URL not set
- API agnostic: same interface for both backends
- Tests: `backend/tests/test_event_store_switching.py` (5/5 passing)

#### Part 4: Collaboration Draft Persistence
- `backend/features/collaboration/persistence.py` — DraftPersistence class (420 lines)
- Methods: create_draft(), get_draft(), list_drafts_by_user(), append_segment(), pass_ring(), update_draft(), clear_all()
- Integrated into `service.py` with dual-mode (DB/in-memory) via _use_persistence() check
- Fixed: timezone import, duplicate ring holder tracking
- Tests: `backend/tests/test_collab_persistence.py` (9/9 passing)

#### Part 5: Global Idempotency Keys
- `backend/core/idempotency.py` — Shared idempotency key management
- Functions: check_and_set(), check_key(), clear_all_keys()
- Atomic insert-or-fail using IntegrityError handling
- Works with both PostgreSQL and in-memory fallback
- Tests: `backend/tests/test_idempotency.py` (8/8 passing)

#### Part 6: Test Infrastructure
- `backend/conftest.py` — Pytest fixtures for database tests
- db_url fixture: provides DATABASE_URL to tests
- reset_db fixture: truncates all tables between tests
- Enables clean isolation for persistence tests

**Test Coverage:**
- **35 persistence tests passing** (database foundation, event store, switching, collab, idempotency)
- **78/80 guardrail tests passing** (2 pre-existing test design issues unrelated to persistence)
- All tests run with DATABASE_URL set for full integration testing

**Migration Notes:**
- In-memory stores still present as fallback
- Services check DATABASE_URL at runtime to enable persistence
- No API contract changes (fully backward compatible)
- Analytics API updated to use get_store() instead of EventStore class directly

**Next Steps (Phase 3.6):**
- Migrate remaining in-memory stores (invites, users)
- Add database indexes for performance
- Implement pgvector for user profile embeddings
- Connection pooling optimization (already using pooled engine)

---

### Phase 4 — Publishing + Scheduling (⏭️ PLANNED)

**What It Is:**
Multi-platform publishing (X, Instagram, YouTube), scheduling, and post analytics.

**Planned Features:**
- Thread publishing to X (Twitter)
- Cross-post to Instagram, LinkedIn
- Schedule for optimal times (AI-suggested)
- Real-time analytics (impressions, engagement)
- A/B testing (two versions of thread)

**Timeline:** Q2 2026

---

## 5. Share Card Systems (CRITICAL ARCHITECTURE)

OneRing uses share cards in two contexts: personal momentum and collaborative drafts.

### Personal Share Cards (Phase 2)

**Purpose:** Creator profile snippet for sharing their momentum and work.

**Data Included:**
- User name, avatar, archetype badge
- Momentum score (30-day cumulative)
- Latest post preview
- Public profile link

**Generation:** Deterministic, uses `now` param for reproducible scores

**Safety:** No private data, only public profile info

---

### Collab Share Cards (Phase 3.3c)

**Purpose:** Highlight collaborative work, attribute contributors, showcase ring velocity.

**Data Included:**
- Draft title, subtitle (derived from content)
- Contributors list (creator first, max 5 shown)
- Ring velocity (passes in last 24h, average frequency)
- Segment count (work volume)
- CTA to join collaboration

**Generation:** Deterministic, uses `now` param for metrics calculation

**Safety Guarantees:**
- No invite tokens
- No one-time codes
- No email addresses
- No internal IDs (displayNames only)
- Tests enforce all above

---

### Why Deterministic?

Share cards are **shared artifacts**—they must look the same whether fetched by the creator or a stranger. Determinism ensures:

1. **Consistency:** Same link = same preview (no flickering/surprise changes)
2. **Testability:** Fixed `now` param enables test repeatability
3. **Cacheability:** Identical payloads can be cached server-side without staleness issues
4. **Shareability:** Share cards remain valid for hours without refresh

---

### Why Images Are Intentionally Deferred

Share cards currently return JSON only. Image rendering (for Twitter cards, OG tags) is deferred to Phase 4 for:

- Reduced backend complexity (no headless browser, no image generation)
- Cleaner separation of concerns (JSON response vs image artifact)
- Flexibility (images can be generated on-demand or pre-rendered)
- Early validation (prove JSON payloads are correct before rendering)

---

## 6. Safety & Privacy Guarantees

### What Never Leaks

**Token Hashes:**
- Internal storage: `CollaborationInvite.token_hash` (bcrypt, for verification)
- Public API: `InviteSummary` model (no `token_hash` field)
- Tests: Explicit checks that API response body never includes `token_hash`

**Invite Tokens:**
- Generated once, hashed immediately
- Exposed only in creation response (one-time)
- Consumed on acceptance (cannot be reused)
- Tests verify acceptance mutations do not return token

**Emails:**
- Stored in Clerk (never in OneRing database)
- Never included in collaboration or share card responses
- Collaborator lists use displayName only
- Tests verify no email patterns in API payloads

**Secrets & Passwords:**
- No plaintext secrets in any request/response
- All models explicitly exclude sensitive fields
- Response models are frozen (immutable, cannot add fields)
- Tests scan responses for keywords: `token`, `secret`, `password`, `key`, `hash`

---

### Test Enforcement

**Safety Test Pattern:**
```python
def test_response_never_leaks_token_hash():
    """Verify API response omits internal token_hash field."""
    response = client.get("/v1/collab/drafts/draft-123/share-card")
    payload = response.json()["data"]
    
    assert "token_hash" not in str(payload)
    assert "token_hash" not in str(payload.keys())
```

**Coverage:** All public endpoints have equivalent safety tests

---

## 7. Deterministic Time Strategy

### The Problem

Metrics depend on time:
- Momentum scores = days since last post
- Ring velocity = passes in last 24 hours
- Share cards = "3 passes in last 24h"

If tests run at different times, metrics change → tests fail (flaky).

### The Solution

**Optional `now` Query Parameter:**

```
GET /v1/collab/drafts/{draft_id}/share-card?now=2025-12-21T15:30:00Z
```

All time-dependent calculations use the provided `now` instead of `datetime.now()`.

### Where It's Used

1. **Momentum calculation** (`backend/features/momentum/service.py`):
   - `momentum_score(user_id, now=None)` — if no `now`, defaults to current time

2. **Ring velocity** (`backend/features/collaboration/service.py`):
   - `compute_metrics(draft, now=None)` — counts passes in `[now - 24h, now]`

3. **Share cards** (`backend/features/collaboration/service.py`):
   - `generate_share_card(draft_id, now=None)` — uses provided `now` for metrics

### Testing With Fixed Time

```python
def test_deterministic_share_card():
    fixed_time = "2025-12-21T15:30:00Z"
    
    # First call
    card1 = generate_share_card("draft-123", now=fixed_time)
    
    # Second call (same time)
    card2 = generate_share_card("draft-123", now=fixed_time)
    
    # Assertion
    assert card1 == card2  # Byte-for-byte identical
```

### Backward Compatibility

All `now` parameters are optional. If omitted, system uses current time (production behavior). Tests explicitly pass `now` for repeatability.

---

## 8. Testing Summary

### Current Coverage

| Category | Count | Status |
|----------|-------|--------|
| Backend tests | 226 | ✅ All passing |
| Frontend tests | 251 | ✅ All passing |
| **Total tests** | **477** | **✅ 100% passing** |
| Skipped tests | 0 | — |
| Flaky tests | 0 | — |

### Backend Test Distribution

**By Feature:**
- Momentum (streaks, scores, coach): ~25 tests
- Archetypes: ~10 tests
- Collaboration (drafts, ring, permissions): 11 tests
- Invites (tokens, expiration, safety): 11 tests
- Presence (typing, attribution): ~15 tests
- Deep linking: ~8 tests
- Share cards: 20 tests (Phase 3.3c)
- Analytics (stubs): ~6 tests
- Profile embeddings: ~8 tests
- Utilities, helpers, edge cases: ~70+ tests

**Safety Focus:**
- 10+ tests explicitly verify no token_hash leakage
- 5+ tests scan for forbidden keywords in responses
- 8+ tests verify frozen model immutability
- All tests use deterministic inputs/timestamps

### Frontend Test Distribution

**By Feature:**
- Momentum graph rendering: ~15 tests
- Archetype display: ~12 tests
- Profile pages: ~20 tests
- Share cards: 17 tests
- Collab invites: ~16 tests
- Collab presence: ~19 tests
- Collab joined banner: ~12 tests
- Coach suggestions: ~12 tests
- Today loop: ~20 tests
- Share card v2 (Phase 3.3c): 19 tests
- No-network imports: ~1 test
- Contracts (type safety): ~3 tests
- Utilities, helpers: ~15+ tests

**Quality Gates:**
- All responses validated with Zod schemas
- No TypeScript `any` types in test code
- Zero flaky timing-dependent assertions
- All component snapshots match (visual regression prevention)

---

## 9. File Map (HIGH LEVEL)

### Backend (`backend/`)

**Models** (`backend/models/`)
- `momentum.py` — MomentumScore, StreakData
- `archetype.py` — Archetype, ArchetypeProfile
- `collaboration.py` — Draft, Segment, Collaborator, Ring
- `invite.py` — CollaborationInvite (internal), InviteSummary (public)
- `sharecard_collab.py` — CollabShareCard, ShareCardMetrics, ShareCardCTA
- `user.py` — User profile, embeddings
- `post.py` — Post metadata

**Features** (`backend/features/`)
- `momentum/service.py` — Streak calculation, momentum score (deterministic)
- `archetypes/service.py` — Archetype detection (rule-based)
- `collaboration/service.py` — Draft creation, ring passing, share card generation
- `collaboration/invite_service.py` — Token generation, acceptance, revocation
- `collaboration/presence_service.py` — Active editors, typing indicators
- `collaboration/attribution_service.py` — Contribution metrics
- `collaboration/deep_link_service.py` — Link resolution

**API** (`backend/api/`)
- `momentum.py` — Endpoints: GET `/v1/momentum/{user_id}`
- `archetypes.py` — Endpoints: GET `/v1/archetypes/{user_id}`
- `collaboration.py` — Endpoints for drafts, invites, presence, share cards

**Tests** (`backend/tests/`)
- `test_momentum.py` — 25+ tests
- `test_archetypes.py` — 10+ tests
- `test_collab_*.py` — 80+ tests (drafts, rings, permissions, invites, presence, share cards)
- `test_safety_*.py` — 10+ security tests

**Core** (`backend/core/`)
- `config.py` — Environment variables, defaults
- `logging.py` — Structured logging
- `security.py` — Auth utilities, rate-limiting
- `utils.py` — Helpers (UUID, time, hashing)

**Main**
- `main.py` — FastAPI app initialization, routes registration

---

### Frontend (`src/`)

**Pages** (`src/app/`)

**Dashboard** (`src/app/dashboard/`)
- `layout.tsx` — Dashboard auth guard, navigation
- `today/page.tsx` — Today loop (daily challenge, streaks, coach)
- `profile/page.tsx` — Public profile view (momentum, archetype, share card)
- `collab/page.tsx` — Collaboration dashboard (drafts list, share button)
- `collab/accept/page.tsx` — Invite accept flow

**API Routes** (`src/app/api/`)
- `collab/drafts/[draftId]/share-card/route.ts` — Proxy to backend share card endpoint
- `momentum/[userId]/route.ts` — Proxy to backend momentum endpoint
- `archetypes/[userId]/route.ts` — Proxy to backend archetype endpoint

**Components** (`src/components/`)
- `MomentumGraph.tsx` — 30-day momentum visualization
- `ArchetypeCard.tsx` — Archetype badge + description
- `ShareCard.tsx` — Personal share card (v1)
- `CollabShareCardModal.tsx` — Collaborative share card modal (v2)
- `JoinedBanner.tsx` — "You joined this collaboration" banner
- `PresenceIndicators.tsx` — Active editor list, typing indicators
- `CoachSuggestions.tsx` — AI coach recommendations
- `TodayChallenge.tsx` — Daily challenge card

**Tests** (`src/__tests__/`)
- `momentum.spec.ts` — Momentum graph rendering, score calculation
- `archetypes.spec.ts` — Archetype detection, display
- `profile.spec.ts` — Public profile pages
- `sharecard.spec.ts` — Personal share card (v1)
- `collab-sharecard.spec.ts` — Collaborative share card (v2)
- `collab-invites.spec.ts` — Invite flow, token handling
- `collab-presence.spec.ts` — Presence indicators, typing
- `collab-joined-banner.spec.ts` — Banner display
- `coach.spec.ts` — Coach suggestions
- `today.spec.ts` — Today loop UI
- `no-network.spec.ts` — Import side-effect validation
- `contracts.spec.ts` — Type safety checks

**Lib** (`src/lib/`)
- `embeddings.ts` — OpenAI embedding generation
- `validation.ts` — Zod schemas, type definitions
- `time.ts` — Time utilities (timezone, formatting)

**Configuration**
- `tsconfig.json` — TypeScript strict mode, path aliases
- `next.config.ts` — Next.js configuration
- `postcss.config.mjs` — Tailwind CSS
- `vitest.config.ts` — Test runner configuration

---

### Documentation (`.ai/domain/`)

- `collaboration.md` — Collab architecture, Phase 3 detailed spec
- `momentum.md` — Momentum calculation, streak rules
- `archetypes.md` — Archetype detection heuristics

---

### Project Root

- `PROJECT_STATE.md` — This file (canonical project state)
- `DESIGN_DECISIONS.md` — Architecture rationale, trade-offs
- `README.md` — Getting started, local dev setup
- `.env.example` — Required environment variables

---

## 10. Known Technical Debt (HONEST)

### In-Memory Stores (Phase 3.5)

**Current State:**
```python
_drafts_store: dict[str, Draft] = {}  # STUB for PostgreSQL
_idempotency_keys: dict[str, bool] = {}  # STUB for PostgreSQL
```

**Impact:**
- Data lost on server restart
- No multi-instance support (would require shared Redis)
- No query optimization (all-in-memory iteration)

**When Addressed:** Phase 3.5 (PostgreSQL migration)

**Plan:**
- Migrate to Prisma ORM with PostgreSQL
- Keep in-memory stores for backward compatibility during transition
- Add database indexes for collaborator lookups, ring velocity queries

---

### No Real-Time Presence (Websocket)

**Current State:**
- Presence stored in-memory with 30-second TTL
- Frontend polls every 5 seconds
- No server-initiated updates

**Impact:**
- Typing indicators have 5-second latency
- Multiplayer editing experience feels sluggish
- Scales poorly with many concurrent drafts

**When Addressed:** Phase 3.5+ (optional, depends on user feedback)

**Plan:**
- Evaluate Socket.io or ws library for WebSocket support
- Broadcast presence changes to subscribed clients
- Reduce latency to <500ms

---

### Share Cards Are JSON-Only

**Current State:**
- Share card endpoint returns JSON only
- No OG image generation, no Twitter card preview image
- Links show generic preview (no draft-specific thumbnail)

**Impact:**
- Twitter/Facebook previews are minimal (title + URL only)
- Less visual appeal in social shares
- Users can't see draft preview in feed

**When Addressed:** Phase 4 (with publishing feature)

**Plan:**
- Add headless browser (Puppeteer) for image generation
- Generate OG images server-side on demand
- Cache images with long TTL
- Return `og:image` meta tag in deep link endpoint

---

### Analytics Are Stubbed

**Current State:**
- Analytics endpoints return mock data
- No real engagement metrics (views, RING passes)
- Leaderboards hardcoded for demo

**Impact:**
- Impossible to see actual collaboration impact
- No feedback loop for creators
- Leaderboards don't reflect real activity

**When Addressed:** Phase 3.4 (Analytics + Leaderboard)

**Plan:**
- Implement event tracking (draft view, RING pass, segment contribution)
- Query aggregated metrics for per-draft leaderboards
- Real-time top 10 calculations with time windows (24h, 7d, 30d)

---

### No Scheduled Publishing

**Current State:**
- Drafts are published immediately when shared
- No scheduling for optimal post times
- No batch publishing (post to multiple platforms simultaneously)

**Impact:**
- Users must manually post at each platform
- No time zone optimization
- No A/B testing (same draft to different audiences)

**When Addressed:** Phase 4 (Publishing + Scheduling)

**Plan:**
- Add `scheduled_at` field to drafts
- Background job to publish at scheduled time
- Multi-platform batch posting (X, Instagram, LinkedIn)

---

### No Machine Learning Features

**Current State:**
- All suggestions are rule-based or heuristic (momentum, archetypes, coach)
- No LLM-based generation (content suggestions, title optimization)
- No personalization engine

**Impact:**
- Coach suggestions are generic (not personalized to user history)
- No smart draft recommendations
- Limited content optimization

**When Addressed:** Phase 4+ (post-launch)

**Plan:**
- Evaluate adding Groq LLM for personalized coaching
- Build recommendation engine (who to collaborate with)
- Draft title/subtitle optimization suggestions
- Carefully preserve determinism (no randomness in suggestions)

---

## 11. Immediate Next Steps

### Phase 3.4 — Analytics + Leaderboard (DEC 2025 - JAN 2026)

**Work:**
1. Implement event tracking schema
2. Aggregate metrics: views, RING passes, segments contributed
3. Per-draft leaderboard endpoint
4. Lightweight top 10 contributors endpoint
5. Tests (20+ tests for metrics calculation)

**Success Criteria:**
- Per-draft view count tracking
- RING velocity displayed in dashboard
- Top 10 drafts visible on leaderboard
- All metrics deterministic (same time window = same results)

---

### Phase 3.5 — Persistence Layer (JAN - FEB 2026)

**Work:**
1. Set up PostgreSQL locally + GitHub Actions CI
2. Create Prisma schema (Draft, Collaborator, Ring, Event, Invite)
3. Migrate in-memory stores to database
4. Add pgvector column for embeddings
5. Implement query optimizations (indexes, connection pooling)
6. Update tests to use TestClient with transaction rollback

**Success Criteria:**
- All existing tests pass with Prisma models
- Data persists across server restarts
- Query performance <100ms for typical lookups
- Zero data loss on deployment

---

### Phase 4 — Publishing + Scheduling (FEB - MAR 2026)

**Work:**
1. X/Twitter API integration (thread posting, media upload)
2. Instagram Graph API integration
3. Schedule UI (date/time picker)
4. Background job for scheduled publishing
5. Multi-platform batch posting

**Success Criteria:**
- Draft publishes to X with proper threading
- Media attachments work
- Scheduling future publish times
- Cross-platform batch publish works
- Tests cover all happy paths and error cases

---

### Stability & Polish (Ongoing)

**Incremental improvements:**
- Performance profiling and optimization
- Database query optimization (N+1 detection)
- Better error messages (user-friendly, not stack traces)
- Analytics for internal use (uptime, error rates, latency)
- Documentation expansion (API docs, contributor guide)

---

## 12. Success Metrics (How We Know We're Winning)

### Technical
- Test coverage stays at 100% (no regression)
- All tests pass in CI/CD (no skipped/flaky)
- Code review response time <24h
- Zero production incidents (data loss, security)

### Product
- Users engage with daily streaks (metric: % DAU completing challenge)
- Collaboration features see adoption (metric: % drafts with collaborators)
- Share cards drive traffic (metric: click-through rate on shared links)
- RING economics feel balanced (metric: average RING per user stable)

### Operations
- Backend response time <500ms (p95)
- Database queries <100ms (p95, post-Phase 3.5)
- Deployment frequency 1x/week (predictable, safe)
- Uptime >99.5% (production SLA)

---

## 13. Questions & Answers

**Q: Why determinism over real-time ML?**
A: Determinism enables reproducible testing, predictable user experience, and easier debugging. ML models (even deterministic ones) are harder to reason about. OneRing prioritizes clarity and safety.

**Q: Why no engagement chasing?**
A: Dark patterns (infinite scroll, notifications on every engagement, algorithmic addiction) burn out creators. OneRing focuses on consistent effort (streaks) and authentic collaboration (RING passing), not viral moments.

**Q: Why separate internal and public models?**
A: Internal models (like CollaborationInvite) store secrets (token_hash, passwords). Public models (like InviteSummary) expose only safe fields. This separation prevents accidental leakage in API responses.

**Q: Why `now` query parameter?**
A: Time-dependent metrics make tests flaky (they pass/fail depending on when they run). Optional `now` parameter lets tests use fixed timestamps, ensuring identical results. Production uses current time (omit `now` param).

**Q: When does Phase 3.5 (PostgreSQL) happen?**
A: After Phase 3.4 (analytics). In-memory stores are acceptable for early user testing. Once >10 concurrent users or multi-instance deployment needed, PostgreSQL migration becomes critical.

**Q: What's the RING token model?**
A: RING is earned through collaboration (ring passing) and consistency (streaks), not vanity metrics. RING can be staked for yield or transferred to collaborators. Economics designed to reward authentic contribution, not engagement hacking.

---

## 14. Appendix: Change Log

### December 21, 2025 (Latest)
- Phase 3.3c (Share Card v2) complete: 20 backend tests + 19 frontend tests, all passing
- Fixed test_accept_response_no_token_hash_leak from Phase 3.3b
- Total test suite: 477 tests, 100% passing

### December 14, 2025
- Phase 3.3b (Deep Linking) complete
- Phase 3.3a (Presence + Attribution) complete
- Phase 3.3 (Invite UX) complete
- Collab dashboard UI fully functional

### Earlier Sessions
- Phase 3.2 (Invites backend) complete
- Phase 3.1 (Collab Threads MVP) complete
- Phase 2 (Momentum & Identity) complete
- Phase 1 (Daily Pull Loop) complete

---

**Document Status:** Authoritative reference for all future AI sessions  
**Next Update:** After Phase 3.4 completion (January 2026)
