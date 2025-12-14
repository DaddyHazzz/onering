# OneRing Design Decisions (Canonical & Current)

This document captures high-level, long-lived architectural decisions and the current implementation status / caveats so that agents and humans make consistent choices.

## 1) Backend
**Decision:** FastAPI (Python) as the canonical backend for agent orchestration, LangGraph for agent chains, and Temporal.io for durable workflows.
**Current:** Full FastAPI + LangGraph integration in place. FastAPI runs on `localhost:8000` during dev. Server routes in `src/app/api/*` proxy generation requests to `POST http://localhost:8000/v1/generate/content/` with streaming responses back to client. FastAPI includes:
- `/v1/generate/content/` — POST endpoint that streams Groq responses or invokes LangGraph agents
- RQ worker pool in `backend/workers/` for background posting, video rendering, and data processing
- Agent orchestration via LangGraph under `backend/agents/langgraph/` (Writer, Strategy, Research, Analytics, Posting agents)
- Redis queue integration for job scheduling and retry logic

## 2) Frontend
**Decision:** Next.js (app router) + TypeScript + Tailwind + shadcn for UI primitives.
**Current:** App router fully implemented in `src/app/` (Next.js 16). Server routes under `src/app/api/*/route.ts` use NextRequest/Response semantics. Key routes:
- `/api/generate/route.ts` — streams Groq tokens to client, proxies to FastAPI
- `/api/post-to-x/route.ts`, `/api/post-to-ig/route.ts` — platform-specific posting with rate-limiting
- `/api/stripe/{checkout,webhook}/route.ts` — payment flows
- `/api/referral/*`, `/api/promo/claim`, `/api/monitoring/stats` — platform features
- `/monitoring/page.tsx` — real-time system health dashboard with auto-refresh

## 3) Database & Vector Memory
**Decision:** PostgreSQL + TimescaleDB for time-series, pgvector for embeddings, Prisma as ORM.
**Current:** Prisma schema includes User, Post, Family, StakingPosition models. User profiles auto-embed on first generation via `profileEmbedding: Unsupported("vector(1536)")` column. Embeddings computed using user metadata (name, recent posts) and stored in pgvector for personalization downstream.

## 4) Auth
**Decision:** Clerk (Next.js) for user management, SSO, and session handling.
**Current:** `src/app/layout.tsx` wraps app in ClerkProvider. Server routes use `currentUser()` from `@clerk/nextjs/server`. User metadata stored in Clerk's `publicMetadata` fields: `verified` (bool), `ring` (RING balance), `earnings` (total earnings), `referralCode` (invite code). `clerkClient` safely handles both callable factory and direct object patterns.

## 5) Posting Integrations (X, Instagram, TikTok, YouTube)
**Decision:** `twitter-api-v2` for X (OAuth 1.0a). Meta Graph API for IG (stub ready). YouTube Data API for video uploads.
**Current:**
- **X:** `src/app/api/post-to-x/route.ts` posts threads by splitting content on newlines, chains replies via `reply.in_reply_to_tweet_id`, includes rate-limiting check (5 posts per 15 minutes), awards RING (views/100 + likes×5 + retweets×10).
- **Instagram:** `src/app/api/post-to-ig/route.ts` (mock success) — ready for real Graph API integration.
- **TikTok/YouTube:** Stubs in place; backend workers handle video rendering and upload queuing.

## 6) Payments & Monetization
**Decision:** Stripe Checkout (hosted) + webhook verification to mark users verified and award RING.
**Current:**
- `src/app/api/stripe/checkout/route.ts` — creates Checkout Session, stores in Redis/temp store, returns `sessionUrl` for redirect.
- `src/app/api/stripe/webhook/route.ts` — verifies signature using raw `arrayBuffer()`, listens for `checkout.session.completed`, updates Clerk metadata (`verified: true`, `ring += 500`).
- RING award formula tuned for posting engagement + Stripe verification bonus.

## 7) Agents & Orchestration
**Decision:** LangGraph manages multi-agent chains (Writer → Strategy → Research → Posting). Temporal.io reserved for future durable workflows.
**Current:**
- **LangGraph graph** in `backend/agents/langgraph/graph.py` orchestrates sequential agent execution.
- **Writer agent** (`backend/agents/writer_agent.py`) — Groq-powered content generation with user profile context
- **Strategy agent** (`backend/agents/strategy_agent.py`) — analyzes market trends, recommends posting times
- **Research agent** (`backend/agents/research_agent.py`) — gathers trending topics, competitor analysis
- **Posting agent** (`backend/agents/posting_agent.py`) — routes content to X, IG, TikTok with platform-specific formatting
- **Analytics agent** (`backend/agents/analytics_agent.py`) — fetches post metrics, calculates RING earned
- All agents input/output standardized JSON for chaining.

## 8) Rate-limiting, Queues & Reliability
**Decision:** Redis for rate-limiting, RQ + Temporal for job queues and retries.
**Current:**
- Rate-limiting checks in `/api/post-to-*` routes use Redis SETEX with sliding windows (5 posts per 15 minutes per user).
- `backend/workers/queue.py` enqueues long-running jobs (content generation, video rendering, post scheduling).
- `backend/workers/worker.py` processes jobs from RQ queue with built-in retries.
- Temporal.io integration stubs in place for future durable workflow orchestration (`backend/workflows/content_workflow.py`).

## 9) Security & Webhooks
**Decision:** Verify all webhooks using raw payload signatures; idempotency and replay protection required.
**Current:**
- Stripe webhook verifies signature via `stripe.webhooks.constructEvent(body, signature, secret)` with raw body from `arrayBuffer()`.
- Public routes (webhooks, health checks) whitelisted in `src/proxy.ts` for Stripe CLI testing.
- All posting endpoints authenticated via Clerk JWT; X/IG credentials stored in `.env.local` (not in code).

## 10) Observability & Monitoring
**Decision:** Server-side structured logging, Stripe CLI for webhook debugging, /monitoring dashboard for system health.
**Current:**
- All endpoints log with `console.log("[context] event")` pattern for easy filtering.
- `src/app/monitoring/page.tsx` — real-time dashboard showing:
  - Active users (24h), total RING circulated, post success rate
  - Published vs. failed posts, average RING per post
  - Recent agent workflow traces with status and duration
  - Auto-refreshes every 5 seconds via `/api/monitoring/stats`
- Stripe webhook logs visible in `stripe listen` CLI output during dev.

## 11) Embeddings & Personalization
**Decision:** User profile embeddings stored in pgvector for content recommendation and personalization.
**Current:**
- `src/lib/embeddings.ts` — `embedUserProfile()` function converts user metadata (name, bio, recent post topics) to OpenAI embeddings.
- On first content generation, user profile auto-embeds if not already set.
- Embeddings stored in User.profileEmbedding (pgvector column).
- LangGraph agents can fetch user embeddings to tailor content (future: vector similarity for cohort analysis).

## 12) Referral System & Virality
**Decision:** URL-based referral codes, RING bonuses for referrer and referee.
**Current:**
- `src/app/api/referral/generate/route.ts` — creates unique code for user (e.g., `john-xyz123`)
- `src/app/api/referral/track/route.ts` — increments referral count on signup
- `src/app/api/referral/claim/route.ts` — awards RING to referrer (+50) and referee (+25) on first purchase
- Invite links auto-populated in dashboard with shareable URL pattern `/refer?code=john-xyz123`

## 13) RING Staking & Yield
**Decision:** User can stake RING tokens for fixed terms and earn APR-based yields.
**Current:**
- `src/app/api/ring/stake/route.ts` — creates StakingPosition with amount, duration, APR
- `src/app/api/ring/stake/list/route.ts` — lists user's stakes, calculates claimable yield based on elapsed time
- `src/app/api/ring/stake/claim/route.ts` — claims accrued yield and unlocks RING (if matured)
- APR rates configurable per staking tier (e.g., 10% for 30-day lock, 25% for 180-day lock)

## 14) Family Pool & Shared Earnings
**Decision:** Users can invite family members to contribute to a shared RING pool for shared decision-making.
**Current:**
- `src/app/api/family/invite/route.ts` — generates family invite link
- `src/app/api/family/accept/route.ts` — accepts invite, links member to primary account
- `src/app/api/family/list/route.ts` — lists family members and calculates combined RING balance
- Family members inherit referral bonuses and staking yields on their contributions

## 15) Migration & Next Steps (Updated Roadmap)
**Completed (This Session):**
- ✅ Full LangGraph agent orchestration (Writer → Strategy → Research → Posting → Analytics)
- ✅ Real-time generation with Groq streaming to client
- ✅ Multi-platform posting (X, IG stubs, TikTok/YouTube ready)
- ✅ Stripe payment integration with RING reward
- ✅ Referral system with invite tracking
- ✅ RING staking with yield calculation
- ✅ User profile embeddings in pgvector
- ✅ Monitoring dashboard with system health metrics
- ✅ Rate-limiting and queue management via Redis + RQ
- ✅ Family pool feature (shared earnings across members)

**High Priority (Next Sprints):**
- Temporal.io workflow migration for durable content generation + posting retries
- Real Instagram Graph API integration + OAuth flow
- RING token smart contract (Solana or Ethereum) for on-chain composability
- Advanced personalization via embedding-based cohort analysis

**Medium Priority:**
- Video rendering optimization (better encoding profiles, CDN integration)
- A/B testing framework for content variants
- Advanced analytics dashboard (post-by-post RING attribution)

**Constraints to Preserve:**
- Keep Clerk as auth layer (do not change without stakeholder approval)
- Keep Groq as primary LLM (switching requires full prompt re-tuning)
- Rate-limiting thresholds (5 posts per 15 mins per user) must not exceed platform ToS
- All secrets remain in `.env.local` and `.env` (never commit)

If you deviate from these decisions, document why and open a PR that updates this file.
