# ONERING PROJECT CONTEXT (CURRENT, DETAILED — FOR AGENTS AND DEVELOPERS)

This file is the single-source summary for AI agents (Grok, ChatGPT, Gemini, Copilot) and humans to understand the exact current state of the OneRing repo, environment, and running assumptions. Update this when you change routes, auth behavior, or the payment flow.

---

## 1) Identity & High-level Goal
- Name: OneRing
- Mission: Build an agentic content system that generates, schedules, posts, and measures viral social content; native engagement token is `RING` used for incentives and marketplace actions.

## 2) Tech Stack (current)
- Frontend: Next.js 16 (App Router) in `src/app`, TypeScript, React 19, Tailwind CSS.
- Backend: FastAPI (Python) skeleton under `backend/` for agent orchestration; Next.js server routes in `src/app/api/*/route.ts` act as proxies in dev.
- Auth: Clerk (Next.js) for auth and user metadata; server APIs (`currentUser`, `clerkClient`) used in app routes.
- Payments: Stripe Checkout (hosted session) + webhook verification (raw body signature verification in `src/app/api/stripe/webhook/route.ts`).
- External APIs: `twitter-api-v2` for X (OAuth 1.0a), Meta Graph for IG (mocked/in-progress), others planned.
- Persistence: Short-term: Clerk `publicMetadata` for prototyping user state (posts, ring, promos). Long-term: Postgres + Timescale + pgvector (planned).
- Dev infra: `pnpm` for frontend, `uvicorn` for backend dev, `stripe` CLI and `ngrok` for webhook testing, Redis and RQ worker for background tasks (backend).

## 3) Exact Implemented Endpoints & Files (what's working now)
- `src/app/api/generate/route.ts` — proxy to Groq/llama or FastAPI generation (streaming proxy placeholder).
- `src/app/api/post-to-x/route.ts` — posts thread lines to X using `twitter-api-v2`, chains replies, updates Clerk metadata and awards +50 RING per post.
- `src/app/api/post-to-ig/route.ts` — IG posting placeholder (mocked); updates metadata when simulated.
- `src/app/api/stripe/checkout/route.ts` — creates Stripe Checkout Session (returns `sessionUrl` to client). Uses `currentUser()` server-side to bind `client_reference_id`.
- `src/app/api/stripe/webhook/route.ts` — receives Stripe webhook, uses `req.arrayBuffer()` raw body, `stripe.webhooks.constructEvent()`, extracts `client_reference_id` and updates Clerk metadata (+500 RING, `verified: true`). Note: file includes a runtime guard for `clerkClient` being callable vs object.
- `src/app/api/mine-ring/route.ts` — quick dev API to add RING to a user (POST amount).
- `src/app/api/referral/*` — create/claim referral codes and award +200 RING to both referrer and claimer (persists into Clerk `publicMetadata.claimedReferrals`).
- `src/app/api/promo/claim/route.ts` — promo codes (FIRST100, FELONFOUNDER) one-time claim enforcement; updates Clerk metadata.
- `src/app/api/viewership/route.ts` — mock view/like metrics for posts.
- `src/app/api/market/lease/route.ts` — name leasing for RING (deducts from Clerk metadata).
- `src/app/api/schedule-post/route.ts` — schedule helper (mocked, replays via endpoint or RQ worker later).
- `src/proxy.ts` — custom proxy layer to replace legacy `middleware.ts`. Protects `/dashboard` and `/api/*` routes via Clerk middleware while allowing some public routes (webhook, sign-in callback).
- `src/app/dashboard/page.tsx` — client dashboard UI: `UserButton`, RING display, generate UI, post history, checkout redirect, referrals, promos, mine-ring button, and posting flows.

## 4) Important Runtime Notes & Caveats
- Clerk: we use `clerkClient` in server routes. Some environments/typings present `clerkClient` as a callable factory; code defensively checks `typeof clerkClient === 'function'` and calls it when necessary. Use `client.users.getUser()` / `client.users.updateUser()`.
- Stripe webhooks: must use `req.arrayBuffer()` (or raw body access) to verify signatures. The webhook route expects `STRIPE_WEBHOOK_SECRET` to match the forwarding secret from `stripe listen`.
- Stripe TypeScript quirk: stripe package typings lock `apiVersion` to a narrow literal; the webhook file uses `"2022-11-15" as any` to avoid a TypeScript literal mismatch. This is non-functional at runtime but resolves TS errors.
- Proxy vs middleware: legacy `src/middleware.ts` was removed and replaced with `src/proxy.ts` to avoid Next 16 conflicts. If you add middleware, ensure no duplicate middleware files exist.
- Persistence: current production-grade persistence is not implemented — Clerk `publicMetadata` and in-memory Maps are used for prototyping. Move to Postgres/Redis for reliability.
- Rate-limiting: simple in-memory `Map` is used in posting endpoints; replace with Redis sliding window in production.
- Dev server port: dev server must run on the port that `ngrok` or Stripe CLI forwards to (commonly 3000). Stale node processes can occupy port 3000 -> kill them if needed.

## 5) Required Environment Variables (for local dev)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (Clerk client)
- `CLERK_SECRET_KEY` (server-side Clerk secret)
- `STRIPE_SECRET_KEY` (sk_test_*)
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (pk_test_*)
- `STRIPE_PRICE_ID` (price used for Checkout)
- `STRIPE_WEBHOOK_SECRET` (set to the value from `stripe listen` when forwarding)
- `GROQ_API_KEY` (if using Groq model for generation) OR backend FastAPI endpoint running
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET` (X posting)

## 6) How to Reproduce the Most Important Flows (developer steps)
1. Start frontend dev server: `pnpm install` then `pnpm dev` (ensure it runs on port 3000 or the port you will forward).
2. Expose your dev server to the internet (Stripe webhooks / OAuth callbacks):
   - Option A (Stripe CLI): run `stripe listen --forward-to localhost:3000/api/stripe/webhook` and copy the webhook secret into `STRIPE_WEBHOOK_SECRET` in `.env.local`.
   - Option B (ngrok): run `ngrok http 3000` and configure Stripe/Clerk callback URLs to the ngrok domain.
3. Create a Stripe Checkout session from the dashboard (`Get Verified`), complete payment with test card `4242 4242 4242 4242`.
4. Confirm the webhook delivery in the Stripe CLI window and check server logs for `checkout.session.completed` handling and Clerk metadata update.

## 7) What Agents Must Know (explicit sync guidance for Grok/ChatGPT/Gemini)
- Always read this file before making code changes. It contains the canonical list of active endpoints, runtime caveats, and dev-run steps.
- When asked to produce or modify code involving: auth, payments, external posting, or scheduling, reference the exact files listed in section 3 and preserve the patterns described (server routes, `zod` validation, `Response.json`, no client-only imports in server files).
- Do not change the authentication provider (Clerk) or replace the payment provider (Stripe) without an explicit maintainer instruction.

## 8) Current Priorities / TODO (short list)
- Verify end-to-end Stripe Checkout -> webhook -> Clerk metadata update using Stripe CLI or ngrok (high priority).
- Replace in-memory rate-limiters and Clerk metadata persistence with Redis/Postgres (medium).
- Wire `src/app/api/generate/route.ts` to the backend FastAPI streaming endpoint for real streaming of model tokens (high for product demo).
- Harden webhook handling (retries, idempotency keys) and protect webhook endpoint with a small rate-limiter (low-medium).

---

If this file is out of date, update it immediately after merging any server-route or auth-related change.