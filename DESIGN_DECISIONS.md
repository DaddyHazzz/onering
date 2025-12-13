# OneRing Design Decisions (Canonical & Current)

This document captures high-level, long-lived architectural decisions and the current implementation status / caveats so that agents and humans make consistent choices.

1) Backend
- Decision: FastAPI (Python) as the canonical backend for agent orchestration and heavy-lifting; LangGraph for agent chains and workflow orchestration.
- Current: A minimal FastAPI skeleton exists in `backend/`. Most generation and fast-response flows are proxied through Next.js server routes during dev, but long-term agent flows live in FastAPI + LangGraph.

2) Frontend
- Decision: Next.js (app router) + TypeScript + Tailwind + shadcn for UI primitives.
- Current: The app router is implemented in `src/app` (Next.js 16). Server routes are under `src/app/api/*/route.ts` and are actively used for Stripe, posting, and proxying to backend generation endpoints.

3) Database & Vector Memory
- Decision: PostgreSQL + TimescaleDB for time-series and `pgvector` for embeddings/memory.
- Current: Schema and migrations are planned; current prototyping stores user state in Clerk `publicMetadata` and temporary in-memory structures. Migrate to Postgres + Redis (for rate-limiting) next.

4) Auth
- Decision: Clerk (Next.js) for user management, SSO, and JWT/session handling.
- Current: `src/app/layout.tsx` integrates Clerk; server routes use `currentUser()` and `clerkClient`. Note: `clerkClient` may be a callable factory in some runtimes — server code defensively supports both an object and a function return.

5) Posting Integrations
- Decision: Use `twitter-api-v2` for X (OAuth 1.0a), Meta Graph for IG/FB, YouTube Data API for video.
- Current: X posting is implemented in `src/app/api/post-to-x/route.ts` (thread posting logic, reply chaining, + ring awarding). IG posting is mocked and will be wired to real Graph API once access tokens and app review considerations are handled.

6) Payments & Monetization
- Decision: Stripe Checkout (hosted) + webhook verification to mark users verified and award RING.
- Current: `src/app/api/stripe/checkout/route.ts` creates a Checkout Session and returns `sessionUrl`. `src/app/api/stripe/webhook/route.ts` verifies signatures via raw body and updates Clerk metadata (+500 RING). Ensure `STRIPE_WEBHOOK_SECRET` matches the `stripe listen` forwarded secret during dev.

7) Agents & Orchestration
- Decision: LangGraph manages multi-agent chains; Temporal.io will be used later for durable workflows and retries.
- Current: Agent orchestration is in the design phase. The generate request currently proxies to Groq or the FastAPI prototype; full LangGraph integrations are the next major milestone.

8) Rate-limiting, Queues & Reliability
- Decision: Use Redis for rate-limiting and job queues; RQ or Temporal for background tasks.
- Current: In-memory `Map` based rate-limiting exists in posting endpoints as a placeholder — replace with Redis sliding-window counters. Background scheduling uses simple in-route scheduling or RQ worker hooks in `backend/` for prototyping.

9) Security & Webhooks
- Decision: Verify all webhooks using raw payload signatures; idempotency and replay protection required for production.
- Current: Stripe webhook verification implemented using `arrayBuffer()` and `stripe.webhooks.constructEvent()`. Webhook endpoint is allowed through `src/proxy.ts` public paths during dev.

10) Observability & Debugging
- Decision: Strong server-side logs for payment and posting flows; use Stripe CLI for webhook debugging and ngrok for external testing.
- Current: Many routes log essential events (checkout.session.completed, post success). Dev server sometimes reports source-map warnings only — non-fatal.

11) Migration & Next Steps (short roadmap)
- Finish connecting `src/app/api/generate/route.ts` to FastAPI streaming responses (high priority).
- Replace Clerk `publicMetadata` persistence with Postgres-backed user table + pgvector for embeddings (medium-high).
- Replace in-memory rate-limits with Redis and move posting to a queued worker (Temporal or RQ) for retries and backoff (high).
- Harden checkout/webhook idempotency and monitoring (medium).

If you deviate from these decisions, document why and open a PR that updates this file.
