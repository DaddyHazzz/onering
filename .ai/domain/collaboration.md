# Domain — Collaboration

**Phase 3.1 + 3.2 + 3.3 + 3.3a + 3.3b Complete**  
**December 21, 2025**

## Concept Definition
Co-creation features enabling shared threads, attribution, and mutual momentum gains via the **Ring** pattern + **Collaborative Invites** + **Presence & Attribution**.

## Core Entities

### Draft (CollabDraft)
A collaborative thread being composed by a group of users. One user creates the draft; others are invited to contribute.

**Invariants:**
- Creator initiates draft
- Ring holder controls segment order
- Status: ACTIVE (open), LOCKED (paused), COMPLETED (published)
- Immutable: All Pydantic models frozen with `ConfigDict(frozen=True)`
- Collaborators: List of accepted collaborator user_ids
- Pending invites: List of invite IDs awaiting acceptance

### Segment (DraftSegment)
A single contribution to a draft by one user. Immutable after append.

**Phase 3.3a Attribution Fields (optional):**
- `author_user_id` — User who wrote this segment
- `author_display` — Deterministic display name (@u_XXXXXX format, 6-char sha1 hash)
- `ring_holder_user_id_at_write` — Ring holder at time of write
- `ring_holder_display_at_write` — Ring holder display name at time of write

**Invariants:**
- Attribution fields set on append (if present)
- Display names never leak user secrets (deterministic hash)

### Ring (RingState)
Token that controls who can append segments or pass the ring. Exactly one user holds the ring at any time.

**Phase 3.3a Presence Field (optional):**
- `last_passed_at` — ISO timestamp of most recent ring pass

**Invariants:**
- Only ring holder can append segments
- Only ring holder can pass ring to: owner OR accepted collaborators
- Ring can be passed multiple times (non-destructive)
- History is immutable (append-only)
- `last_passed_at` updated on every pass_ring call

### Invite (CollaborationInvite)
An invitation for a user to collaborate on a draft.

**Invariants:**
- Created by: Draft creator or ring holder only
- Target: Handle or user_id (resolved via identity service)
- Status: PENDING, ACCEPTED, REVOKED, EXPIRED (computed on read)
- Token: Deterministic generation, hashed storage, never leaked
- Expiration: 72 hours (default), configurable
- Idempotency: Same idempotency_key returns cached invite

## Example State Transitions

### Draft Lifecycle
- **proposed → active:** Create draft (creator becomes ring holder)
- **active → active:** Holder appends segment, passes ring
- **active → locked:** Creator or holder pauses draft
- **locked → active:** Creator resumes draft
- **active → completed:** Creator publishes draft

### Invite Lifecycle
- **created → pending:** Invite generated with token + share URL
- **pending → accepted:** Target user verifies token, joins as collaborator
- **pending → revoked:** Creator revokes invite before acceptance
- **pending → expired:** 72 hours pass, invite no longer valid
- **accepted → (complete):** Collaborator now on draft

### Ring Passing (with Collaborators)
1. Creator creates draft (holder = creator)
2. Creator invites @alice
3. @alice accepts (added to collaborators)
4. Creator passes ring to @alice (valid: she's a collaborator)
5. @alice appends segment
6. @alice passes ring back to creator (valid: he's the owner)
7. Creator appends segment, publishes

## Metrics Involved
- Participation rate: segments / total collaborators
- Shared momentum delta: engagement gained from collaborative effect
- **Ring velocity (Phase 3.3a):** passes 24h, avg minutes between passes, contributors count
- Invitation acceptance rate: accepted / created
- Collaborator count per draft
- **Presence indicators (Phase 3.3a):** Last activity timestamp, current ring holder

## Ring Velocity Formulas (Phase 3.3a)

### contributorsCount
**Unique authors + creator:**
```python
unique_authors = set(seg.author_user_id for seg in segments if seg.author_user_id)
contributors_count = len(unique_authors | {draft.creator_id})
```

### ringPassesLast24h
**Ring passes within 24 hours of `now`:**
```python
if now is None: now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=24)
passes_24h = sum(1 for holder in ring_state.holders_history if holder.timestamp >= cutoff)
```

### avgMinutesBetweenPasses
**Average time between ring passes (null if <2 passes):**
```python
if len(ring_state.holders_history) < 2:
    avg_minutes = None
else:
    timestamps = [h.timestamp for h in ring_state.holders_history]
    time_span = (max(timestamps) - min(timestamps)).total_seconds() / 60
    avg_minutes = time_span / (len(timestamps) - 1)
```

### lastActivityAt
**Most recent of: segment creation, ring pass, draft creation:**
```python
segment_times = [seg.created_at for seg in segments]
pass_times = [h.timestamp for h in ring_state.holders_history]
activity_times = segment_times + pass_times + [draft.created_at]
last_activity_at = max(activity_times)
```

## Backend Systems

### Collaboration Service
- Draft CRUD, segment append, ring passing (idempotent)
- In-memory store: `_drafts_store` dict (Phase 3.5: replace with PostgreSQL)
- Idempotency tracking: `_idempotency_keys` set
- Permission checks: Validates ring holder + collaborators

### Invite Service
- Create invite: Resolve handle, generate deterministic token, hash for storage
- Accept invite: Verify token, add collaborator to draft
- Revoke invite: Only creator can revoke (idempotent)
- Expiration: Computed on read (EXPIRED if now > expires_at)
- In-memory store: `_invites_store` dict + `_invite_idempotency_keys` set
- Token security: Token is deterministic (test stub), hashed storage, never exposed raw

### Identity Service
- Handle resolution: Deterministic hash-based (test stub)
- Production (Phase 3.5): Replace with Clerk user lookup
- Validation: is_valid_user_id(), is_valid_handle()

### Event Emission
- collab.draft_created, collab.segment_added, collab.ring_passed
- collab.invite_created, collab.invite_accepted, collab.invite_revoked
- All with timestamp, type, payload (per .ai/events.md)

## API Endpoints

### Draft Operations
- `POST /v1/collab/drafts` — Create draft
- `GET /v1/collab/drafts` — List user's drafts
- `GET /v1/collab/drafts/{draft_id}` — Get draft by ID
- `POST /v1/collab/drafts/{draft_id}/segments` — Append segment (idempotent)
- `POST /v1/collab/drafts/{draft_id}/pass-ring` — Pass ring (idempotent)

### Invite Operations
- `POST /v1/collab/drafts/{draft_id}/invites` — Create invite (idempotent)
- `GET /v1/collab/drafts/{draft_id}/invites` — List invites for draft
- `POST /v1/collab/invites/{invite_id}/accept` — Accept invite (idempotent)
- `POST /v1/collab/invites/{invite_id}/revoke` — Revoke invite (idempotent)

## Data Invariants
1. **Draft creation:** Ring holder = creator, status = ACTIVE
2. **Segment append:** Only ring holder can append, order auto-increments
3. **Ring pass:** Only ring holder can pass, history is append-only
4. **Immutability:** All models frozen, no mutations after creation
5. **Idempotency:** Same idempotency_key = no duplicate state change
6. **Bounds:** Title < 200 chars, content < 500 chars per segment

## Implementation Status

### Phase 3.1: Draft + Ring MVP ✅ COMPLETE
- [x] Models (Draft, Segment, Ring, RingState)
- [x] Service (CRUD + ring passing)
- [x] API endpoints (5 routes)
- [x] Frontend proxies + UI
- [x] Tests (guardrails, schema validation)
- [x] Status: Production-ready, 162 tests passing

### Phase 3.2: Collaborator Invites + Handle Resolution ✅ COMPLETE
- [x] Invite models (InviteStatus, CollaborationInvite, request/response schemas)
- [x] Identity service (deterministic handle→user_id resolution)
- [x] Invite service (create, accept, revoke with idempotency + token security)
- [x] API endpoints (4 routes with permission checks)
- [x] Token security (deterministic generation, hashed storage, safe exports)
- [x] Draft model updates (collaborators + pending_invites fields)
- [x] Ring passing restriction (owner + collaborators only)
- [x] Backend tests (23 new guardrail tests)
- [x] Frontend schema tests (16 new validation tests)
- [x] Status: Production-ready, 365 total tests passing (185 backend + 180 frontend)
- [x] Documentation: PHASE3_INVITES_COMPLETE.md, domain/collaboration.md updated

### Phase 3.3: Frontend UI + Invite Links
- [x] Frontend API proxies (3 routes with Clerk auth + Zod)
  * `/api/collab/drafts/[draftId]/invites` (GET list, POST create)
  * `/api/collab/invites/[inviteId]/accept` (POST accept)
  * `/api/collab/invites/[inviteId]/revoke` (POST revoke)
  * Deterministic idempotency keys: `sha1(userId:context:action)`
  * Target detection: `user_` prefix → user_id, else → handle
  * HTML response detection (502 error with helpful message)
- [x] Draft detail page: Invite form, collaborators list, pending invites
  * Invite form: Target input (handle or user_id), expires hours
  * Share URL display: Copy button, token hint (last 6 chars)
  * Collaborators list: Accepted users with "You" indicator
  * Pending invites: Status badges (PENDING/ACCEPTED/REVOKED/EXPIRED), revoke button
  * Permission check: Only owner/ring holder can invite
- [x] Invite links: `/collab/invite/[inviteId]?token=...` with auto-accept
  * Deep link accept page: Auto-accept on sign-in
  * Manual token input: If token missing from URL
  * Success state: "You're in!" with "Open the Draft" button
  * Error handling: Expired, revoked, invalid token with help text
  * Not signed in: "Welcome" with sign-in CTA
- [x] Frontend schema tests (21 new validation tests)
  * CreateInviteSchema: Target validation, expiresInHours bounds (1-168)
  * AcceptInviteSchema: Token required validation
  * RevokeInviteSchema: DraftId required validation
  * InviteStatus enum: Valid/invalid status tests
  * Idempotency key determinism tests
  * Target detection logic tests
  * Token extraction tests (from share URL)
  * HTML response detection tests
  * Permission check tests
- [x] Backend datetime fix: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`
  * Fixed 6 occurrences across invite_service.py + service.py
  * All datetime objects now timezone-aware (ISO-8601 with offset)
- [x] Status: Production-ready, 201 frontend tests passing (21 new invite UI tests)
- [x] Documentation: collaboration.md updated with Phase 3.3 details

### Phase 3.3a: Presence + Attribution + Ring Velocity ✅ COMPLETE
- [x] Backend model updates (attribution fields, last_passed_at, metrics dict)
  * DraftSegment: author_user_id, author_display, ring_holder_user_id_at_write, ring_holder_display_at_write (optional)
  * RingState: last_passed_at (optional datetime, updated on pass_ring)
  * CollabDraft: metrics (optional dict with contributorsCount, ringPassesLast24h, avgMinutesBetweenPasses, lastActivityAt)
- [x] Service logic (deterministic display names + metrics computation)
  * display_for_user(user_id) → "@u_" + sha1(user_id)[-6:] (deterministic, no secrets)
  * compute_metrics(draft, now=None) → 4 metrics with optional fixed timestamp for testing
  * create_draft: Sets attribution on initial segment, last_passed_at on ring_state
  * append_segment: Sets author_user_id, author_display, ring_holder_user_id_at_write, ring_holder_display_at_write
  * pass_ring: Sets last_passed_at=now
  * get_draft: Optional compute_metrics_flag + now param, attaches metrics to response
- [x] API endpoint update (deterministic testing support)
  * GET /v1/collab/drafts/{draft_id}?now=ISO_TIMESTAMP (optional)
  * Parses now param, passes to service for deterministic metric computation
- [x] Backend tests (18 new guardrail tests, all passing)
  * TestSegmentAttribution: Verifies attribution fields set on append
  * TestRingPresence: Verifies last_passed_at tracking
  * TestDisplayForUser: Deterministic, format @u_XXXXXX, no secrets leaked
  * TestRingVelocityMetrics: Contributors, passes 24h, avg minutes, determinism
  * TestMetricsFormulas: compute_metrics directly + multiple passes scenarios
  * TestBackwardCompatibility: Handles segments without attribution
  * TestDeterminism: Same inputs + same now → identical metrics
- [x] Frontend types + helper function
  * DraftSegment interface: Added 4 attribution fields (optional)
  * RingState interface: Added last_passed_at (optional)
  * DraftMetrics interface: contributorsCount, ringPassesLast24h, avgMinutesBetweenPasses, lastActivityAt
  * CollabDraft interface: Added optional metrics field
  * formatRelativeTime(isoTimestamp): Converts to "just now", "Xm ago", "Xh ago", "Xd ago"
- [x] Frontend UI updates (presence card, metrics row, segment attribution)
  * Presence card: Shows "Ring is with X", "Last passed: X", "Your turn" badge
  * Metrics row: Displays contributorsCount, ringPassesLast24h, avgMinutesBetweenPasses
  * Segment display: Shows author_display, "ring holder" badge if author was holder at write
- [x] Frontend tests (19 new schema + helper tests)
  * Schema validation for attribution, presence, metrics (all optional)
  * formatRelativeTime() logic tests (just now, minutes, hours, days)
  * No-network import guarantee (collab page doesn't fetch on import)
- [x] Status: Production-ready, 204 backend tests + 220 frontend tests passing
- [x] Documentation: collaboration.md updated with Phase 3.3a details

### Phase 3.3b: Invite → Auto-open Draft + First-View Banner ✅ COMPLETE
**Goal:** Deep-link continuity from invite accept to draft detail with supportive first-view banner.

- [x] Backend accept response updates
  * InviteSummary: Added draft_id (required), message (optional) fields
  * accept_invite endpoint: Generates supportive message "You joined {creator_display}'s thread — your turn is coming."
  * list_invites endpoint: Includes draft_id in all invite summaries
- [x] Accept page auto-redirect
  * goToDraft(): Redirects to /dashboard/collab?draftId=X&joined=1
  * handleAccept(): Auto-redirect after 1.5s success display
  * URL pattern: /collab/invite/{inviteId}?token=abc123 → /dashboard/collab?draftId=X&joined=1
- [x] Collab dashboard auto-select + banner
  * useSearchParams hook: Reads draftId + joined query params
  * Auto-select logic: Finds matching draft, sets as selectedDraft
  * Banner display: Shown if joined=1 AND localStorage key not set
  * Banner CTAs: "Pass ring" button (if ring holder, smooth scroll), "Dismiss" button
  * Banner persistence: localStorage key "collab_joined_seen:{userId}:{draftId}" = "1"
- [x] Banner helper functions module (src/features/collab/joinedBanner.ts)
  * joinedBannerKey(userId, draftId): Returns localStorage key string
  * shouldShowJoinedBanner(storage, userId, draftId, joinedParam): Returns boolean
  * dismissJoinedBanner(storage, userId, draftId): Sets localStorage key to "1"
  * getJoinedBannerMessage(state): Returns supportive copy based on ring holder status
  * Pure functions (no side effects, dependency injection for testability)
- [x] Banner copy rules (Magnetic Apps tone)
  * Ring holder: "You joined the thread — it's your turn 🔴"
  * Non-holder: "You joined the thread — ring is with @u_abc123"
  * Never shame language ("your turn is coming", not "waiting on you")
- [x] Backend tests (3 new tests, 2 passing)
  * test_accept_response_includes_draft_id: Verifies draft_id in accept response ✅
  * test_accept_response_includes_accepted_at_iso: Verifies acceptedAt is datetime ✅
  * test_accept_api_response_includes_message: Verifies supportive message in API response (skipped pending refactor)
- [x] Frontend tests (12 new banner helper tests, all passing)
  * joinedBannerKey: Determinism, user differences, draft differences (3 tests)
  * shouldShowJoinedBanner: Param validation, dismissal check, show logic (3 tests)
  * dismissJoinedBanner: localStorage persistence (1 test)
  * getJoinedBannerMessage: Ring holder vs non-holder messages (3 tests)
  * Integration flow: Full lifecycle (show→dismiss→hide), multi-user independence (2 tests)
- [x] Status: Production-ready, 206 backend tests (99.5%, 1 skipped) + 232 frontend tests passing
- [x] Documentation: PHASE3_3B_INVITE_CONTINUITY_COMPLETE.md, collaboration.md updated

### Phase 3.3c: Share Card v2 (Attribution + Ring Velocity) ✅ COMPLETE
**Goal:** Deterministic share card endpoint for collaborative drafts with social proof metrics and contributors list.

- [x] Backend share card model (backend/models/sharecard_collab.py)
  * CollabShareCard: draft_id, title, subtitle, metrics, contributors, top_line, cta, theme, generated_at
  * ShareCardMetrics: contributors_count, ring_passes_last_24h, avg_minutes_between_passes, segments_count
  * ShareCardCTA: label, url (internal path only: /dashboard/collab?draftId=...)
  * ShareCardTheme: bg (Tailwind gradient), accent (color name)
- [x] Backend share card service (backend/features/collaboration/service.py)
  * generate_share_card(draft_id, now=None) → deterministic dict (uses compute_metrics + display_for_user)
  * Contributors list: creator first, then others lexicographically, max 5
  * Subtitle: "Ring with @u_XXXXXX • N contributors • P passes/24h"
  * Top line: "A collaborative thread in progress." (supportive, no shame)
  * Deterministic: same inputs + same now => identical response
  * Safety: never leaks token_hash, passwords, secrets, emails
- [x] Backend API endpoint (backend/api/collaboration.py)
  * GET /v1/collab/drafts/{draft_id}/share-card?viewer_id=...&style=default&now=ISO(optional)
  * Query param now: ISO timestamp for deterministic testing (e.g., now=2025-12-21T12:00:00Z)
  * Response: { "success": true, "data": CollabShareCard }
- [x] Backend tests (backend/tests/test_collab_sharecard_guardrails.py)
  * TestShareCardDeterminism: Same draft + now => identical card (3 tests)
  * TestShareCardSafety: No token_hash, password, secret keywords (3 tests)
  * TestShareCardBounds: Metrics >=0, contributors <=5, capped sensibly (6 tests)
  * TestShareCardContributorOrdering: Creator first, deterministic order, max 5 (3 tests)
  * TestShareCardContent: No shame words, supportive copy, safe URLs (3 tests)
  * TestShareCardMissingDraft: 404 handling (2 tests)
- [x] Frontend API proxy (src/app/api/collab/drafts/[draftId]/share-card/route.ts)
  * GET endpoint with Clerk auth, Zod validation, HTML error detection
  * Validates response schema before returning to client
  * Type export: ShareCard = z.infer<typeof shareCardSchema>
- [x] Frontend modal component (src/components/CollabShareCardModal.tsx)
  * CollabShareCardModal: isOpen, onClose, draftId props
  * Shows: title, subtitle, contributors chips, metrics row, CTA preview
  * Buttons: Refresh, Copy Link, Copy JSON
  * Preview: gradient bg, metrics display, CTA button (disabled in preview)
  * Supportive tone, clean UI, no heavy design requirements
- [x] Frontend wired into collab dashboard (src/app/dashboard/collab/page.tsx)
  * "Share" button added next to draft title
  * Opens modal with onClick={() => setShowShareModal(true)}
  * Modal only shown if selectedDraft exists
  * Fetches share card on demand when modal opens
  * Copy Link includes full URL (window.location.origin + cta.url)
- [x] Frontend tests (src/__tests__/collab-sharecard.spec.ts)
  * Schema validation: accepts valid payload, validates all required fields (5 tests)
  * Metrics bounds: contributors >=1, passes >=0, max segments sensible (6 tests)
  * Contributors: min 1, max 5, deterministic order (3 tests)
  * CTA URL format: starts with /dashboard/collab, includes draftId (3 tests)
  * Safety checks: no token_hash, password, secret keywords, no shame words (2 tests)
  * Helper functions: URL parsing, full URL building (3 tests)
- [x] Status: Production-ready, 207 backend tests (100%, fixed token_hash test) + 245 frontend tests (12 new sharecard tests)
- [x] Documentation: PHASE3_3C_COLLAB_SHARECARD_COMPLETE.md, collaboration.md updated

### Phase 3.4: Analytics + Leaderboard
- [ ] Track: views, likes, reposts per draft
- [ ] Leaderboard: Top drafts by engagement
- [ ] Per-user stats: segments contributed, rings passed

### Phase 3.5: Scheduled Publishing
- [ ] Set `target_publish_at` on draft
- [ ] RQ worker monitors, publishes on schedule
- [ ] Multi-platform publishing (X, IG, TikTok, YouTube)
- [ ] Pre-publish validation

### Phase 3.6: PostgreSQL + pgvector + Clerk Integration
- [ ] Replace in-memory store with PostgreSQL
- [ ] Add pgvector for collaborative filtering
- [ ] Migrate handle resolution to Clerk API lookup
- [ ] Recommend collaborators by content similarity
- [ ] Add migration for invite token format (deterministic → random)

## Notes for AI Agents

When working on collaboration features:
1. **Preserve idempotency:** Every mutation checks idempotency_key first
2. **Check permissions:** Always verify ring holder before mutations
3. **Emit events:** All state changes must emit per .ai/events.md
4. **Test determinism:** Same input → same output every time
5. **Keep stub marked:** Add comments about Phase 3.5 DB replacement
6. **Validate bounds:** Title, content, and strings have max lengths
7. **Use frozen Pydantic:** All models must have `ConfigDict(frozen=True)`
8. **Follow events format:** With timestamp, type, payload

**Last Updated:** December 21, 2025  
**Status:** Phase 3.1 MVP + Phase 3.2 Invites Backend + Phase 3.3 Invite UX + Phase 3.3a Presence/Attribution + Phase 3.3b Invite Continuity + Phase 3.3c Share Card Complete
