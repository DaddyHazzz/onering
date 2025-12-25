# API Reference (Canonical)

This document summarizes stable API contracts. For implementation details, see backend route files under backend/api/.

Last Updated: December 25, 2025

## Authentication
- All endpoints require Clerk-authenticated user unless stated as public.
- Pass `X-User-Id` header in tests to simulate authenticated user.

## Collaboration

- POST /api/collab/drafts
  - Create a new draft
  - Body: { title: string, platform: "x"|"ig"|"tiktok" }
  - Returns: { id, creator_id, ring_state, created_at }

- GET /api/collab/drafts/{draft_id}
  - Get draft by id
  - Returns: CollabDraft

- POST /api/collab/drafts/{draft_id}/segments
  - Add a segment
  - Body: { text: string }
  - Returns: updated draft

- POST /api/collab/drafts/{draft_id}/ring/pass
  - Pass ring to another collaborator
  - Body: { target_user_id: string }
  - Returns: { success: true, to_user_id }

## Analytics

- GET /api/collab/drafts/{draft_id}/analytics
  - Draft analytics snapshot
  - Query: optional now (ISO8601) for deterministic tests
  - Returns: { data: { views, contributors, ring_passes, ... }, computed_at }

- GET /v1/analytics/leaderboard
  - Leaderboard across users
  - Query: optional now
  - Returns: [{ user_id, ring_earned, posts }]

## Insights

- GET /api/insights/drafts/{draft_id}
  - Draft insights, recommendations, alerts
  - Query: optional now
  - Returns: {
      draft_id,
      insights: [{ type, severity, title, message, reason }],
      recommendations: [{ action, target_user_id?, reason, confidence }],
      alerts: [{ alert_type, triggered_at, threshold, current_value, reason }],
      computed_at
    }

Invariants:
- Alerts computed from current state (no averages) for determinism.
- LONG_RING_HOLD: triggered when (now - ring_state.passed_at) >= 24h.
- NO_ACTIVITY: triggered when (now - last_activity_ts) >= 72h.

## Generation

- POST /v1/generate/content/
  - Streams Groq tokens (SSE) for content generation
  - Body: { prompt: string, userId: string }
  - Returns: SSE stream of tokens

## Payments

- POST /api/stripe/checkout
  - Creates Stripe Checkout Session
  - Returns: { sessionUrl }

- POST /api/stripe/webhook (public)
  - Verifies signature and updates user metadata
  - On success: set verified=true, award RING

## Posting

- POST /api/post-to-x
  - Posts a thread to X (Twitter)
  - Splits on newlines; chains replies; rate-limited 5 per 15m
  - Returns: { urls: string[] }

Notes:
- All time-based endpoints accept optional `now` for deterministic tests.
- See .ai/TESTING.md for examples.
