# Design Decisions & Rationale

This document captures architectural and technology choices. Links to code illustrate how each decision is implemented.

## 1. Authentication: Clerk

**Decision:** Use Clerk (Next.js) for user management, SSO, and session handling.

**Why Clerk, not Auth0 / NextAuth?**
- ✅ Simplest "sign up → authenticate" flow for Next.js
- ✅ Built-in user metadata (publicMetadata) for storing RING balance, verified status, referral codes
- ✅ JWT tokens auto-embedded in request headers (no custom parsing)
- ✅ Low-friction onboarding (pre-built UI components)
- ✅ Integrates seamlessly with Vitest (mock `useUser()` hook)

**Caveat:** Clerk is a third-party service; offline auth not supported.

**See:**
- [src/app/layout.tsx](../src/app/layout.tsx) — ClerkProvider setup
- [src/app/api/**/route.ts](../src/app/api/) — Usage of `currentUser()` in server routes

---

## 2. Backend Framework: FastAPI + LangGraph

**Decision:** FastAPI for REST routes + LangGraph for agent orchestration.

**Why FastAPI, not Flask / Django?**
- ✅ Built-in async support (ideal for streaming Groq tokens)
- ✅ Automatic OpenAPI docs (no extra work)
- ✅ Pydantic models for validation (syncs with frontend Zod schemas)
- ✅ Performance: 3–5x faster than Flask for I/O-bound workloads

**Why LangGraph, not Airflow / Temporal?**
- ✅ Simple for small agent chains (Writer → Strategy → Posting)
- ✅ No infrastructure overhead (runs in-process)
- ✅ Groq-friendly (LangChain integrations built-in)
- ✅ Temporal stubs ready for future scaling

**See:**
- [backend/main.py](../backend/main.py) — FastAPI app setup
- [backend/agents/langgraph/graph.py](../backend/agents/langgraph/graph.py) — Agent orchestration
- [backend/agents/writer_agent.py](../backend/agents/writer_agent.py) — Content generation

---

## 3. Frontend Framework: Next.js 16 + App Router

**Decision:** Next.js 16 (app router) for frontend, TypeScript, Tailwind CSS.

**Why Next.js, not Vite / Remix?**
- ✅ Best-in-class TypeScript support
- ✅ Clerk integration pre-built
- ✅ Automatic code splitting (load time)
- ✅ Server components + edge runtime ready

**Why App Router, not Pages Router?**
- ✅ Cleaner route structure (`src/app/[id]/page.tsx`)
- ✅ Built-in streaming support (SSE friendly)
- ✅ Better for Clerk auth (`src/middleware.ts`)

**See:**
- [src/app/layout.tsx](../src/app/layout.tsx) — Layout setup
- [src/app/dashboard/page.tsx](../src/app/dashboard/page.tsx) — Main app
- [src/app/api/**/route.ts](../src/app/api/) — API route handlers

---

## 4. Testing: Vitest + Pytest (No Jest, No Mocha)

**Decision:** Vitest for frontend, Pytest for backend. No skipped tests; all green always.

**Why Vitest, not Jest?**
- ✅ ESM-native (better with TypeScript)
- ✅ Fast (Vite under the hood)
- ✅ Works with React Testing Library out of box
- ✅ Same syntax as Mocha/Jasmine (familiar)

**Why Pytest, not Nose2 / Unittest?**
- ✅ Simple, Pythonic syntax
- ✅ Fixtures > setup/teardown
- ✅ Excellent parametrization support
- ✅ Works with async/await

**Test Discipline:**
- ✅ 1005 tests total (617 backend + 388 frontend), all green
- ✅ Zero skipped tests in mainline
- ✅ NO `--no-verify` bypasses
- ✅ Fast gates + full gates (see [TESTING.md](TESTING.md))

**See:**
- [vitest.config.ts](../vitest.config.ts) — Frontend test config
- [backend/pytest.ini](../backend/pytest.ini) — Backend test config
- [backend/tests/](../backend/tests/) — Test files

---

## 5. Database: PostgreSQL + pgvector

**Decision:** PostgreSQL for primary data store, pgvector for embeddings.

**Why PostgreSQL, not MongoDB?**
- ✅ ACID transactions (ring passing, analytics consistency)
- ✅ Excellent JSON support (no schema migration hell)
- ✅ pgvector extension for embedding vectors
- ✅ Cost (open source, no vendor lock-in)

**Why pgvector, not Pinecone / Weaviate?**
- ✅ Keeps embeddings co-located with other data
- ✅ Single database to manage (simpler ops)
- ✅ ACID transactions include vector operations

**Caveat:** Vector similarity queries slower than dedicated DBs at scale.

**See:**
- [prisma/schema.prisma](../prisma/schema.prisma) — Data model with pgvector
- [src/lib/embeddings.ts](../src/lib/embeddings.ts) — Embedding computation
- [backend/models/collab.py](../backend/models/collab.py) — Pydantic models (single source)

---

## 6. Caching & Queues: Redis + RQ

**Decision:** Redis for caching + job queues, RQ for worker management.

**Why Redis, not Memcached?**
- ✅ Data structures (sets, sorted sets) useful for rate-limiting
- ✅ Pub/Sub for real-time updates
- ✅ Persistence options (RDB, AOF)

**Why RQ, not Bull / Celery?**
- ✅ Simple Python interface
- ✅ No message broker overhead (Redis is enough)
- ✅ Easy to debug (jobs stored as JSON in Redis)

**Caveat:** RQ lacks built-in Celery-style beat scheduling. Use cron for periodic tasks.

**See:**
- [backend/workers/queue.py](../backend/workers/queue.py) — Job enqueueing
- [backend/workers/worker.py](../backend/workers/worker.py) — Worker loop
- [src/app/api/post-to-x/route.ts](../src/app/api/post-to-x/route.ts#L50) — Rate-limiting example

---

## 7. LLM Provider: Groq

**Decision:** Groq (llama-3.1-8b-instant) as primary LLM.

**Why Groq, not OpenAI / Anthropic?**
- ✅ 10–20x faster inference (token streaming feels instant)
- ✅ Lower cost (~$0.05 per 1M tokens vs. $10+ for GPT-4)
- ✅ Open weights (Llama 3.1, auditable)
- ✅ Great for prototyping (no API keys jostling)

**Trade-off:** Quality slightly lower than GPT-4/Claude; acceptable for content generation.

**System Prompts:** Tuned for ring-aware suggestions. Explicit "no numbering" rules for viral thread generation.

**See:**
- [backend/agents/writer_agent.py](../backend/agents/writer_agent.py#L15) — System prompt
- [backend/agents/viral_thread.py](../backend/agents/viral_thread.py) — Platform-specific generation

---

## 8. Streaming: SSE (Server-Sent Events)

**Decision:** Use Server-Sent Events (SSE) for streaming Groq tokens to client.

**Why SSE, not WebSocket?**
- ✅ Unidirectional (server → client) ideal for token streaming
- ✅ Built into browsers (no Socket.io overhead)
- ✅ Proxy-friendly (HTTP under the hood)
- ✅ Auto-reconnect support

**How it works:**
1. Frontend: `fetch("/api/generate", { method: "POST" })`
2. Backend streams: `yield f"data: {token}\n\n"` (SSE format)
3. Frontend reads: `response.getReader()` → parse lines → append to UI

**See:**
- [src/app/api/generate/route.ts](../src/app/api/generate/route.ts#L80) — Streaming implementation
- [src/app/dashboard/page.tsx](../src/app/dashboard/page.tsx#L180) — Client-side reading

---

## 9. Real-Time: Polling + Clerk Presence

**Decision:** Polling for draft updates (no persistent WebSocket).

**Why Polling, not WebSocket?**
- ✅ Simpler to deploy (no long-lived connections)
- ✅ Works behind NAT / firewalls
- ✅ Load balancer friendly (stateless)
- ✅ Acceptable latency (500ms–2s refresh)

**Presence:** Clerk's built-in presence hooks for "who's editing now".

**See:**
- [src/app/dashboard/page.tsx](../src/app/dashboard/page.tsx#L200) — Polling loop
- [backend/features/collaboration/service.py](../backend/features/collaboration/service.py) — Draft state

---

## 10. Payments: Stripe Checkout

**Decision:** Stripe Checkout (hosted) for payment processing.

**Why Stripe Checkout, not custom form / Paddle?**
- ✅ PCI compliance handled by Stripe
- ✅ 3D Secure, Apple Pay, Google Pay built-in
- ✅ Webhook-driven (no polling)

**RING Award:** 500 RING on verified purchase + engagement formula for posting (views/100 + likes×5 + retweets×10).

**See:**
- [src/app/api/stripe/checkout/route.ts](../src/app/api/stripe/checkout/route.ts) — Session creation
- [src/app/api/stripe/webhook/route.ts](../src/app/api/stripe/webhook/route.ts) — Webhook verification

---

## 11. Collaboration Model: Ring Passing

**Decision:** Ring = one holder at a time; pass to invite next contributor.

**Why Ring Passing, not Free-for-All Editing?**
- ✅ Prevents chaos (clear turn order)
- ✅ Encourages async work (not live sync)
- ✅ Rewards contributors fairly (analytics per-holder)
- ✅ Matches social media workflow (drafts, approval cycles)

**Implementation:** RingState model with `current_holder_id`, `passed_at`, `holders_history`.

**See:**
- [backend/models/collab.py](../backend/models/collab.py) — RingState definition
- [backend/features/collaboration/service.py](../backend/features/collaboration/service.py#L98) — pass_ring() method

---

## 12. Insights & Alerts: Current State (not Aggregate)

**Decision:** Compute alerts from current draft state, not historical averages.

**Why Current State, not Aggregates?**
- ✅ Works with zero samples (e.g., zero ring passes)
- ✅ Reflects real-time issues (no lag)
- ✅ Deterministic (no division-by-zero edge cases)

**Example:** `LONG_RING_HOLD` alert uses `(now - ring_state.passed_at)` to compute current hold duration. Works even if ring never passed.

**See:**
- [backend/features/insights/service.py](../backend/features/insights/service.py#L325) — _current_holder_hold_seconds() method
- [backend/tests/test_insights_api.py](../backend/tests/test_insights_api.py#L180) — test_alerts_no_activity_and_long_hold

---

## 13. API Design: Stable Contracts + `now` Parameter

**Decision:** All time-based APIs accept optional `now` parameter for deterministic testing.

**Why `now` Parameter?**
- ✅ Tests don't need to mock system clock
- ✅ Easy to test "what happens 72h later?"
- ✅ Deterministic (same input → same output always)

**Example:**
```bash
GET /api/insights/drafts/{id}?now=2025-12-25T10:00:00Z
# Returns insights as if current time is 2025-12-25 10:00:00
```

**See:**
- [backend/api/insights.py](../backend/api/insights.py#L30) — `now` parameter parsing
- [backend/tests/test_insights_api.py](../backend/tests/test_insights_api.py#L150) — test usage

---

## 14. Error Handling: Meaningful Messages + Actionable Fixes

**Decision:** All errors include actionable next steps.

**Example:**
```json
{
  "error": "Twitter API 403 Not Permitted",
  "suggestedFix": "Check app permissions (needs Read+Write+DM). Regenerate keys in Twitter Developer Portal: https://developer.twitter.com/en/dashboard"
}
```

**See:**
- [src/app/api/post-to-x/route.ts](../src/app/api/post-to-x/route.ts#L80) — Error response

---

## 15. Code Organization: Features > Layers

**Decision:** Organize by feature (collaboration, insights, analytics) not by layer (models, services, routes).

**Why Features, not Layers?**
- ✅ Self-contained modules (easier to refactor)
- ✅ Clear ownership (one person → one feature)
- ✅ Faster navigation (related code together)

**Structure:**
```
backend/
  features/
    collaboration/  <- draft creation, ring passing
      service.py
      models.py
    insights/       <- insights engine
      service.py
      models.py
    analytics/      <- event store, reducers
      service.py
      models.py
  api/             <- route handlers
    collab/
    insights/
    analytics/
```

**See:**
- [backend/features/](../backend/features/) — Feature structure

---

## When to Revisit These Decisions

**Revisit if:**
- Scale exceeds single instance (→ multiple FastAPI servers)
- LLM quality becomes bottleneck (→ OpenAI fine-tuning)
- Polling latency unacceptable (→ WebSocket)
- PostgreSQL can't handle load (→ read replicas + caching)

**Do NOT revisit for:**
- Individual feature requests
- One-off performance tweaks
- Local dev convenience

Document the reason + date when revisiting.
