
Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

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
  - Auth: Collaborators only (creator + invited collaborators)
  - Query: optional `now` (ISO8601) for deterministic tests
  - Returns:
    ```json
    {
      "draft_id": "draft-123",
      "insights": [
        {
          "type": "stalled|dominant_user|low_engagement|healthy",
          "severity": "critical|warning|info",
          "title": "string",
          "message": "string",
          "reason": "string (for explainability)",
          "metrics_snapshot": { /* context-specific metrics */ }
        }
      ],
      "recommendations": [
        {
          "action": "pass_ring|invite_user|add_segment|review_suggestions",
          "target_user_id": "string (optional)",
          "reason": "string",
          "confidence": 0.0-1.0
        }
      ],
      "alerts": [
        {
          "alert_type": "no_activity|long_ring_hold|single_contributor",
          "triggered_at": "ISO8601",
          "threshold": "string (e.g. '72h+ no activity')",
          "current_value": "number|string",
          "reason": "string (why alert triggered)"
        }
      ],
      "computed_at": "ISO8601"
    }
    ```

Invariants:
- All insights computed deterministically from draft state
- Alerts based on current state (no averages), works with zero ring passes
- LONG_RING_HOLD: uses `ring_state.passed_at` for current holder duration
- NO_ACTIVITY: threshold 72h since last activity
- SINGLE_CONTRIBUTOR: <2 contributors with 5+ segments
- Access: 403 if not collaborator

## Generation

- POST /v1/generate/content/
  - Streams Groq tokens (SSE) for content generation
  - Body: { prompt: string, userId: string }
  - Returns: SSE stream of tokens
  - Optional (Phase 10.1): when enforcement enabled, a final SSE event `event: enforcement`
    includes `{ request_id, mode, decisions, qa_summary, would_block, required_edits, audit_ok }`.
  - Non-streaming responses include optional `enforcement` field with the same shape.

### Enforcement Metadata (Phase 10.1)

Optional metadata may be attached to generation responses (non-breaking). In advisory mode, content is never blocked; metadata provides visibility.

- `enforcement` object (optional, advisory/enforced modes only):
  ```json
  {
    "status": "off|advisory|enforced",
    "workflowId": "uuid",
    "policyVersion": "2025-12-25",
    "checks": ["profanity", "tos_compliance", "length"],
    "warnings": ["tweet length near 280 chars"]
  }
  ```

Backward compatibility guarantees:
- Field is optional; omission means enforcement disabled.
- Existing streaming token contract remains unchanged; metadata may be sent as initial JSON envelope or terminal summary event (implementation detail).

### Enforcement Failure Error Shape

In enforced mode, failures include actionable `suggestedFix`.

Example:
```json
{
  "error": {
    "code": "QA_REJECTED",
    "message": "Content contains banned terms",
    "suggestedFix": "Remove profanity and re-generate. See brand safety policy.",
    "details": {
      "banned": ["fuck", "shit"],
      "check": "profanity"
    }
  }
}
```

Additional examples:
- `HARMFUL_CONTENT`: "Detected self-harm phrasing" → suggestedFix: "Refocus on growth/resilience; use provided redirection topic."
- `CIRCUIT_BREAKER_TRIPPED`: "Optimizer failed 3x" → suggestedFix: "Proceed with writer draft; retry later."

Notes:
- Error shape is additive; does not alter HTTP status conventions.
- `suggestedFix` follows existing patterns (see X 403 credential guidance).

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
  - Optional (Phase 10.1): accepts `enforcement` payload from generation; enforced mode
    blocks publishing unless `enforcement.qa_summary.status === "PASS"`.

Notes:
- All time-based endpoints accept optional `now` for deterministic tests.
- See .ai/TESTING.md for examples.

### Backward Compatibility (Phase 10.1)

- Enforcement metadata is optional and non-breaking.
- Failure error shape adds fields under `error` without changing existing keys.
- Advisory rollout ensures content flow unaffected while instrumentation is verified.
