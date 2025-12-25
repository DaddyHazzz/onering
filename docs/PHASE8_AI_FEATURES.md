# Phase 8.1 — AI Turn Suggestions (Ring-Aware Assistant)

## What This Adds
- Ring-aware AI suggestions for drafts without mutating content.
- Modes: next segment, rewrite last segment, summarize so far (ring holder), and read-only commentary (non-holder).
- Platform-aware formatting: X, YouTube, Instagram, Blog (optional input).
- Fully additive: no API or data model changes required.

## Behavior
- Mutative modes (next, rewrite, summary) require holding the ring; otherwise `ring_required` is returned.
- Commentary is always allowed and respects the current draft context.
- Auth supports Clerk JWT or `X-User-Id` fallback; request IDs flow through responses.
- Rate limits: 10/min burst 5 per user for AI suggestions; standardized error contract on 429.
- Audit trail: `ai_suggest` action recorded with mode and platform metadata.
- Tracing: `api.ai_suggest` and `ai.suggest` spans wrap each request.

## Safety & Limits
- No draft mutations; suggestions are plain text previews.
- Ring enforcement reuses collaboration service rules.
- Soft formatting guards to keep X < 240 chars and sensible caps elsewhere.
- Observability: rate-limit counter increments via `ratelimit_block_total` with normalized paths.

## How To Use (API)
```
POST /v1/ai/suggest
{
  "draft_id": "...",
  "mode": "next" | "rewrite" | "summary" | "commentary",
  "platform": "x" | "youtube" | "instagram" | "blog" | null
}
```
Response:
```
{
  "data": {
    "mode": "next",
    "content": "...",
    "ring_holder": true,
    "platform": "x",
    "generated_at": "2025-12-24T00:00:00Z"
  },
  "request_id": "..."
}
```

## Frontend UX
- Draft page panel shows holder actions (next, rewrite, summary) and one-click insert-as-segment.
- Non-holder view renders supportive commentary: "When you get the ring, you might add…" with refresh.
- Disabled states when unauthenticated; loading and error states included.

## Testing
- Backend: ring enforcement, commentary allowance, rate-limit contract.
- Frontend: holder vs non-holder rendering, button enablement, preview + insert flow.

## Notes
- No breaking changes to existing APIs or draft mutation logic.
- Ready for future LLM adapter swap; prompt templates defined in `backend/features/ai/prompts.py`.
