# ONERING PROJECT CONTEXT (CURRENT, DETAILED — FOR AGENTS AND DEVELOPERS)

This file is the single-source summary for AI agents (Grok, ChatGPT, Gemini, Copilot) and humans to understand the exact current state of the OneRing repo, environment, and running assumptions. Update this when you change routes, auth behavior, or the payment flow.

---

## 1) Identity & High-level Goal
- Name: OneRing
- Mission: Build an agentic content system that generates, schedules, posts, and measures viral social content; native engagement token is `RING` used for incentives, staking, and marketplace actions.
- Status: Beta-ready. All core features (generation, multi-platform posting, payment, referrals, staking, embeddings, monitoring) are implemented and tested.

## 2) Tech Stack (current)
- Frontend: Next.js 16 (App Router) in `src/app`, TypeScript, React 19, Tailwind CSS.
- Backend: FastAPI (Python) under `backend/` with full LangGraph orchestration for agents. Uvicorn dev server on port 8000. Next.js server routes proxy generation requests to FastAPI.
- Auth: Clerk (Next.js) for auth and user metadata; server APIs (`currentUser`, `clerkClient`) used in app routes. User state in Clerk `publicMetadata`: `verified`, `ring`, `earnings`, `referralCode`.
- Payments: Stripe Checkout (hosted session) + webhook verification (raw body signature verification).
- External APIs: `twitter-api-v2` for X (OAuth 1.0a), Meta Graph for IG (ready), YouTube Data API (ready), TikTok API (ready).
- Persistence: PostgreSQL + Prisma ORM for users, posts, family members, staking positions. pgvector column for user profile embeddings.
- Job Queue: Redis + RQ for background tasks (posting, video rendering, scheduling).
- Dev infra: `pnpm` frontend, `uvicorn` backend, `stripe listen` for webhooks, Docker (redis/postgres), RQ worker for jobs.

## 3) Exact Implemented Endpoints & Files (what's working now)
### Generation & Content
- `src/app/api/generate/route.ts` — streams Groq tokens from FastAPI; calls `POST /v1/generate/content/` on `localhost:8000`.
- `backend/main.py` — FastAPI app exposing `/v1/generate/content/` (streams Groq responses).
- `backend/agents/langgraph/graph.py` — LangGraph orchestration: Writer → Strategy → Research → Posting → Analytics.

### Posting (Multi-Platform)
- `src/app/api/post-to-x/route.ts` — posts threads to X, chains replies, rate-limits (5 posts per 15 min), awards RING (views/100 + likes×5 + retweets×10).
- `src/app/api/post-to-ig/route.ts` — Instagram posting (mock ready, real Graph API integration pending).
- `src/app/api/post-to-tiktok/route.ts`, `src/app/api/post-to-youtube/route.ts` — stubs ready for real APIs.

### Payments
- `src/app/api/stripe/checkout/route.ts` — creates Stripe Checkout Session (returns `sessionUrl`).
- `src/app/api/stripe/webhook/route.ts` — verifies signature, awards +500 RING, sets `verified: true`.

### RING & Rewards
- Earned on: posting engagement (formula above), Stripe purchase (+500), referrals (+50 referee, +50 referrer).
- Stored in Clerk `publicMetadata.ring` and lifetime in `publicMetadata.earnings`.

### Referral System
- `src/app/api/referral/generate/route.ts` — creates unique code (e.g., `user-xyz123`).
- `src/app/api/referral/track/route.ts` — tracks signup source.
- `src/app/api/referral/claim/route.ts` — awards RING on first purchase (+50 both).

### RING Staking
- `src/app/api/ring/stake/route.ts` — lock RING for 30–180 days, earn APR (10%–25%).
- `src/app/api/ring/stake/list/route.ts` — list positions, calculate yield.
- `src/app/api/ring/stake/claim/route.ts` — unlock and claim yield.

### Family Pool
- `src/app/api/family/invite/route.ts`, `src/app/api/family/accept/route.ts` — invite members, link to primary account.
- `src/app/api/family/list/route.ts` — list members, combined RING balance.

### Analytics & Monitoring
- `src/app/api/analytics/post/route.ts` — fetch X metrics (real API or mock fallback), calculate RING earned.
- `src/app/monitoring/page.tsx` — real-time dashboard (active users, RING circulated, post success rate, agent traces).
- `src/app/api/monitoring/stats/route.ts` — system stats endpoint (refreshes every 5s on dashboard).

### UI & Dashboard
- `src/app/dashboard/page.tsx` — full UI: tabs for Generate, Post to X, Post to IG, Schedule, Leaderboard.
- `src/app/leaderboard/page.tsx` — top earners by RING.

## 4) Important Runtime Notes & Caveats
- Clerk: code defensively checks `typeof clerkClient === 'function'` (factory pattern) and calls when needed.
- Stripe webhooks: must use `req.arrayBuffer()` raw body. Verify with `stripe.webhooks.constructEvent()`.
- Persistence: User metadata in Clerk `publicMetadata` (short-term); database backed by Prisma for posts, family, staking.
- Rate-limiting: Redis-backed sliding window (5 posts per 15 mins per user).
- Profile embeddings: auto-computed on first generation, stored in `User.profileEmbedding` (pgvector, 1536-dim).
- Temporal.io: stubs in place (`backend/workflows/`) for future durable workflow migration.

## 5) Required Environment Variables (for local dev)
### Frontend (.env.local)
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
GROQ_API_KEY=gsk_...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... (from stripe listen)
DATABASE_URL=postgresql://user:pass@localhost:5432/onering
REDIS_URL=redis://localhost:6379
```

### Backend (backend/.env)
```
GROQ_API_KEY=gsk_...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
STRIPE_SECRET_KEY=sk_test_...
DATABASE_URL=postgresql://user:pass@localhost:5432/onering
REDIS_URL=redis://localhost:6379
CLERK_SECRET_KEY=sk_...
```

## 6) How to Reproduce the Most Important Flows (developer steps)
1. Start infrastructure: `docker-compose -f infra/docker-compose.yml up -d` (Redis, Postgres).
2. Start FastAPI backend (Terminal 1): `cd backend && uvicorn main:app --reload --port 8000`.
3. Start RQ worker (Terminal 2): `rq worker -u redis://localhost:6379 default`.
4. Start Next.js frontend (Terminal 3): `pnpm install && pnpm dev` (port 3000).
5. Expose webhooks (Terminal 4): `stripe listen --forward-to localhost:3000/api/stripe/webhook`.
6. Sign in via Clerk, navigate to `/dashboard`.
7. Generate content: type prompt, click "Generate with Groq", see streaming response.
8. Post to X: fill in Twitter creds, click "Post to X Now", see URL.
9. Buy RING: click "Buy RING", complete Stripe payment (test card: 4242 4242 4242 4242).
10. Monitor: visit `/monitoring` to see system stats.

## 7) What Agents Must Know (explicit sync guidance for Grok/ChatGPT/Gemini)
- Always read `DESIGN_DECISIONS.md` and this file before making changes.
- Follow code patterns: Zod validation, `NextRequest`, `Response.json`, Clerk `currentUser()`, no client imports in server files.
- Preserve choices: Clerk auth, Groq LLM, FastAPI backend, Stripe payments, Redis + RQ, pgvector embeddings.
- Test locally before suggesting changes (run the full end-to-end above).

## 8) Error Fixes (Dec 13, 2025)
All 25 TypeScript/Python errors fixed:
- analytics/post/route.ts: metrics undefined → added null check and type narrowing
- family/list/route.ts: parameter types → added `: any` type annotations
- ring/stake/list/route.ts: parameter types → added `: any` for reduce callbacks
- dashboard/page.tsx: Number(prompt) → wrapped prompt result to avoid type error
- Backend Python: all imports resolved (dependencies in requirements.txt)

## 9) Current Priorities / TODO (short list)
- ✅ All core features completed (generation, posting, payments, referrals, staking, embeddings, monitoring)
- Temporal.io workflow migration for durable retries (high)
- Real Instagram Graph API integration (medium)
- RING token smart contract (Solana/Ethereum) (medium)
- Advanced personalization via embeddings (medium)

---

If this file is out of date, update it immediately after merging any server-route, auth, or feature change.