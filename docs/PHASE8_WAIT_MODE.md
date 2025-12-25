# Phase 8.4 — Waiting for the Ring Mode

Status: COMPLETE (Dec 25, 2025)

Purpose: Productive workflows for collaborators while they wait for the ring — private scratch notes, queued suggestions for the ring holder, and lightweight segment votes.

Highlights
- Backend service: notes CRUD, suggestions queue/dismiss/consume, votes upsert/list
- API: 11 endpoints under /v1/wait with rate limits and auth
- Frontend: WaitForRingPanel with tabs (Notes, Suggestions, Votes)
- Safety: author privacy, ring-holder-only consume, collaborator access enforced
- Observability: tracing spans, audit logs for all mutations

API Endpoints
- POST /v1/wait/drafts/{draft_id}/notes — Create note
- GET /v1/wait/drafts/{draft_id}/notes — List notes
- PATCH /v1/wait/notes/{note_id} — Update note
- DELETE /v1/wait/notes/{note_id} — Delete note
- POST /v1/wait/drafts/{draft_id}/suggestions — Queue suggestion
- GET /v1/wait/drafts/{draft_id}/suggestions?status=queued|consumed|dismissed — List suggestions
- POST /v1/wait/suggestions/{suggestion_id}/dismiss — Dismiss suggestion (author)
- POST /v1/wait/suggestions/{suggestion_id}/consume — Consume suggestion (ring holder)
- POST /v1/wait/drafts/{draft_id}/segments/{segment_id}/vote — Upsert vote (+1/-1)
- GET /v1/wait/drafts/{draft_id}/votes — Per-segment totals + user vote

Contracts
- Notes: author-only visibility; 1–2000 chars
- Suggestions: kind ∈ {idea,rewrite,next_segment,title,cta}; 1–1000 chars; status transitions queued → consumed|dismissed
- Votes: one per user per segment (update overwrites); response lists all draft segments

Tests (8.4.1)
- Added backend/tests/test_waitmode_api.py covering: notes CRUD, suggestion dismiss + consume (holder-only), vote upsert + list
- Frontend suites green after fixes to PlatformVersionsPanel and ExportPanel

Usage Example
1. Collaborator writes private note:
POST /v1/wait/drafts/{id}/notes { content: "Next idea for hook" }
2. Collaborator queues suggestion:
POST /v1/wait/drafts/{id}/suggestions { kind: "cta", content: "Add a CTA at end" }
3. Ring holder consumes when ready:
POST /v1/wait/suggestions/{suggestion_id}/consume
4. Collaborators vote on segments:
POST /v1/wait/drafts/{id}/segments/{segment_id}/vote { value: 1 }

Notes
- Consume does not auto-append segments; ring holder chooses how to integrate content
- All endpoints require X-User-Id auth via get_current_user_id
- Rate limits: notes 120/min, suggestions 60/min, votes 240/min
