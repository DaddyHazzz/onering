# OneRing

Note: Canonical project documentation now lives under .ai/. Start here:
- .ai/README.md — index of canonical docs
- .ai/PROJECT_CONTEXT.md — purpose, stack, non-goals
- .ai/ARCHITECTURE.md — system overview
- .ai/API_REFERENCE.md — endpoints and contracts
- .ai/TESTING.md — fast vs full gates, commands
# OneRing � Agentic Content Generation & Multi-Platform Posting

**OneRing** is a full-stack agentic content system that generates viral social media content, posts across multiple platforms (X, Instagram, TikTok, YouTube), and rewards creators with a native RING token. Built with Next.js 16, FastAPI, LangGraph, and Stripe.

**Status:** Beta-ready. All core features implemented and tested.

### Hard Guarantees
- Viral threads and streamed generations never contain numbering (backend + optimizer + frontend + tests enforce removal).
- Temporal workflow retries are deterministic with fixed backoff; RQ jobs are wrapped with idempotent job IDs (no duplicate scheduling).
- Posting routes (X/IG/LinkedIn) share validation shape and normalized success/error responses.
- Analytics aggregation is deterministic; mock data is clearly marked and tested (including empty datasets).

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Features](#features)
4. [Local Development Setup](#local-development-setup)
5. [Detailed Testing Guide](#detailed-testing-guide)
6. [API Reference](#api-reference)
7. [Environment Variables](#environment-variables)
8. [Troubleshooting](#troubleshooting)
9. [Product Vision](#product-vision)
10. [Roadmap](#roadmap)
11. [Extending the System Safely](#extending-the-system-safely)

---

## Quick Start

### Prerequisites
- **Node.js** 18+ and **pnpm**
- **Python** 3.10+ and **pip**
- **Docker** (for Redis and PostgreSQL)
- **Stripe CLI** (for webhook testing)
- Accounts: Clerk, Stripe (test mode), Twitter API, Groq

### 1. Clone & Install Dependencies
```bash
# Clone the repo
git clone https://github.com/DaddyHazzz/onering.git
cd onering

# Install frontend dependencies
pnpm install

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Set Up Environment Variables
```bash
# Copy template files
cp .env.example .env.local           # Frontend
cp backend/.env.example backend/.env # Backend
```

Fill in all required secrets (see [Environment Variables](#environment-variables) below).

### 3. Start Infrastructure
```bash
# Terminal 1: Start Redis & Postgres
docker-compose -f infra/docker-compose.yml up -d

# Verify containers are running
docker ps
```

### 4. Start Everything (One Command)
```bash
# From project root (C:\Users\hazar\onering)
# This starts: Backend, Frontend, RQ Worker, Stripe listening in parallel
.\start_all.ps1
```

Or start manually:

**Terminal 1 - Backend:**
```bash
cd c:\Users\hazar\onering
python -m uvicorn backend.main:app --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd c:\Users\hazar\onering
pnpm dev  # Runs on http://localhost:3000
```

**Terminal 3 - RQ Worker (for background jobs):**
```bash
cd c:\Users\hazar\onering
rq worker -u redis://localhost:6379 default
```

**Terminal 4 - Stripe Webhook Forwarding (optional):**
```bash
stripe listen --forward-to localhost:3000/api/stripe/webhook
```
- Performs health checks every 30 seconds
- Uses exponential backoff for retries (1s ? 2s ? 4s ? 8s ? 16s)

**Why not run `uvicorn main:app` directly?**
- Running from project root fails: Python can't find the `main` module
- The persistent runner handles the directory changes automatically
- Ensures the backend stays alive even if it crashes

**Alternative (NOT recommended):**
```bash
# Only if you understand the directory requirement:
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 5. Start RQ Worker (Background Jobs)
```bash
# Terminal 3
cd /path/to/onering
rq worker -u redis://localhost:6379 default
```

### 6. Start Frontend (Next.js)
```bash
# Terminal 4
pnpm dev
```

Frontend runs on `http://localhost:3000`.

### 7. Set Up Stripe Webhooks (Optional but Recommended)
```bash
# Terminal 5
stripe listen --forward-to localhost:3000/api/stripe/webhook
```

Copy the `STRIPE_WEBHOOK_SECRET` and add it to `.env.local`.

### 8. Access the App
- **Frontend:** http://localhost:3000
- **Sign in:** Click "Sign In" (uses Clerk)
- **Dashboard:** http://localhost:3000/dashboard
- **Monitoring:** http://localhost:3000/monitoring (system health + agent traces)

---

## Architecture Overview

```
+-----------------------------------------+
�     Frontend (Next.js 16 App Router)    �
�  src/app, Tailwind, Clerk Auth          �
+-----------------------------------------+
                 � HTTP REST API
                 � /api/generate (streaming)
                 � /api/post-to-x (posting)
                 � /api/stripe/* (payments)
                 � /api/monitoring/stats
                 ?
+-----------------------------------------+
�   FastAPI Backend (localhost:8000)      �
�  - /v1/generate/content/ (streaming)    �
�  - LangGraph agents (Writer, Strategy,  �
�    Research, Posting, Analytics)        �
�  - RQ job queue (posting, video)        �
�  - Redis rate-limiting & cache          �
+-----------------------------------------+
             �
    +----------------------------------+
    ?                   ?              ?
Groq LLM      Social Platform APIs   PostgreSQL
(streaming)   X, IG, TikTok,         + pgvector
              YouTube                (embeddings)

Temporal (optional): `backend/workflows/content_workflow.py` is scaffolded for durable runs; keep `TEMPORAL_ENABLED` off until a Temporal server is configured.
```

### Frontend Components
- **`src/app/layout.tsx`** � Clerk auth wrapper + global routing
- **`src/app/dashboard/page.tsx`** � Main dashboard (tabs: Generate, Post, Schedule, Leaderboard)
- **`src/app/monitoring/page.tsx`** � Real-time system health dashboard
- **`src/app/api/generate/route.ts`** � Streams Groq tokens from FastAPI
- **`src/app/api/post-to-x/route.ts`** � Posts threads to X, rate-limits, awards RING
- **`src/app/api/post-to-ig/route.ts`** � Instagram posting (Graph API ready)
- **`src/app/api/stripe/{checkout,webhook}/route.ts`** � Payment flows

### Backend Services
- **`backend/main.py`** � FastAPI app + `/v1/generate/content/` endpoint
- **`backend/agents/langgraph/graph.py`** � Multi-agent orchestration (Writer ? Strategy ? Research ? Posting ? Analytics)
- **`backend/agents/writer_agent.py`** � Groq-powered content generation
- **`backend/agents/posting_agent.py`** � Platform-specific formatting + routing
- **`backend/workers/queue.py`** � RQ job enqueueing
- **`backend/workers/worker.py`** � RQ worker process
- **`backend/models/`** � Prisma-managed database schemas

### Key Design Decisions
See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for architecture decisions, service choices, and constraints.

---

## Features

### ? Content Generation
- **Groq-powered streaming** � Real-time token streaming from Groq's llama-3.1-8b-instant model
- **LangGraph orchestration** � Multi-step workflow (Writer ? Strategy ? Research) for rich context
- **User personalization** � Embeddings-based (pgvector) content tailoring based on user profile

### ? Multi-Platform Posting
- **X (Twitter)** � Thread posting, reply chaining, real-time metrics, rate-limiting (5 posts/15 mins)
- **Instagram** � Mock integration, ready for Meta Graph API
- **TikTok & YouTube** � Stub APIs, backend workers ready for video upload
- **Rate-limiting** � Redis-backed sliding window (prevents platform blocks)
- **RING rewards** � Earned per post: `views/100 + likes�5 + retweets�10`

### ? Payment & Monetization
- **Stripe Checkout** � Hosted payment flow (test card: `4242 4242 4242 4242`)
- **RING token** � Native reward token earned via posting, referrals, purchases, staking
- **Verification badges** � Users who purchase RING get `verified: true` status
- **RING awarding** � +500 RING on purchase, +50 on referral claim, +engagement on post

### ? Referral System
- **Unique referral codes** � Generated per user (e.g., `john-abc123`)
- **Invite tracking** � Track signup source and award bonuses
- **Dual bonuses** � Referrer +50 RING, referee +50 RING on first purchase

### ? RING Staking & Yield
- **Lock periods** � 30, 90, or 180 days
- **APR rates** � 10% (30-day), 18% (90-day), 25% (180-day)
- **Automatic yield calculation** � Accrued daily, claimable anytime
- **Unlock mechanism** � Claim yield early, or wait for full maturity

### ? Family Pools
- **Shared RING balance** � Invite family members to contribute
- **Combined yield** � All members' yields accumulate to shared pool
- **Invite management** � Accept/decline membership

### ? User Profile Embeddings
- **Automatic profiling** � On first generation, user profile auto-embeds (OpenAI embeddings)
- **pgvector storage** � 1536-dimensional vectors stored in Postgres
- **Personalization** � Agents use embeddings for content recommendation

### ? Monitoring Dashboard
- **Real-time metrics** � Active users, total RING circulated, post success rate
- **Agent traces** � View recent LangGraph workflow executions
- **Auto-refresh** � Updates every 5 seconds
- **Accessible at** `/monitoring` (auth required)

### ? Queue Management
- **RQ + Redis** � Background job processing with retries
- **Job types** � Content generation, video rendering, post scheduling
- **Future Temporal.io** � Durable workflow orchestration for production

---
## Product Vision
See [.ai/PRODUCT_VISION.md](.ai/PRODUCT_VISION.md) � OneRing is a daily ritual for creators, optimizing momentum and identity over vanity metrics.

## Roadmap
See [.ai/ROADMAP.md](.ai/ROADMAP.md) for tiered features (Daily Pull, Identity & Status, Network Effects, Experiments) with clear user behaviors and dependencies.

## Extending the System Safely
See [.ai/BACKEND_EXTENSION_POINTS.md](.ai/BACKEND_EXTENSION_POINTS.md) for backend guidance.
- Do not introduce side effects in request handlers.
- All progress-related mutations must be idempotent.
- Use Temporal for windows/retries and RQ for jobs; prefer deterministic reducers.

Frontend principles and AI behavior:
- [.ai/FRONTEND_PRINCIPLES.md](.ai/FRONTEND_PRINCIPLES.md)
- [.ai/AI_BEHAVIOR.md](.ai/AI_BEHAVIOR.md)

OneRing is optimized for long-term creator growth. Every feature must answer: �Why would I open this TODAY instead of tomorrow?�

## Phase 1 Focus (Daily Pull Loop)

**Status:** ✅ All three core features complete and tested.

- **Creator Streaks** - Track consecutive days, mercy mechanics, no punishment
- **Daily Challenges** - One prompt per day, deterministically assigned from 20-prompt catalog
- **AI Post Coach** - Deterministic pre-flight feedback (clarity, resonance, platform fit, authenticity, momentum alignment), no LLM required

Together, they answer: "I have a reason to show up (Streaks), I know what to post (Challenges), and I'm getting better at it (Coach)."

## Phase 2 Focus (Momentum & Identity)

**Status:** ✅ Momentum Score complete; ✅ Public Profiles complete; ✅ Archetypes complete.

- **Momentum Score** ✅ - Stable, interpretable 0..100 score based on streak health, daily completion, consistency, and coach engagement; no likes, no viral chasing
  - Reflects unfolding creative identity over time
  - Deterministic computation, UTC-aware
  - Trend detection vs 7-day rolling average
  - Supportive action hints, never punitive
  - [Spec](backend/features/momentum/README.md)

- **Public Creator Profiles** ✅ - Public portfolio at `/u/[handle]` showing streak, momentum, recent posts
  - Read-only public view (no Clerk auth required)
  - Backend: `GET /v1/profile/public?handle=...` with deterministic stubs
  - Frontend: Full UI with 7-day momentum graph, streak visualization, recent posts feed
  - 22 frontend tests + 22 backend tests validating determinism, safety, shape
  - No secrets leaked, all data computed from user_id hash (safe for public sharing)
  - Example: `http://localhost:3000/u/alice`

- **Archetypes & Personalization** ✅ - Deterministic creator archetype classification (6 types: truth_teller, builder, philosopher, connector, firestarter, storyteller)
  - Observes signals from Coach feedback, Challenge choices, and post patterns
  - Soft guidance without destiny: influences Coach tone + Challenge selection
  - 23 backend tests + 23 frontend tests + 4 profile integration tests
  - No shame words, supportive explanations, public-safety enforced
  - Dashboard card shows primary/secondary + 3-bullet explanation
  - [Complete Spec](PHASE2_ARCHETYPES_COMPLETE.md) | [Feature Docs](backend/features/archetypes/README.md) | [AI Context](.ai/domain/archetypes.md)

**Invariants:**
- Features without a clear "Why today?" will not be merged.
- Event vocabulary: see [.ai/events.md](.ai/events.md).

## Local Development Setup
```
# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Groq
GROQ_API_KEY=gsk_...

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... (from stripe listen)

# Twitter (optional)
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# LinkedIn (optional)
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_AUTHOR_URN=urn:li:person:xxxx  # or urn:li:organization:xxxx

# Instagram Graph (optional)
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_BUSINESS_ACCOUNT_ID=...

# Database & Cache
DATABASE_URL=postgresql://user:password@localhost:5432/onering
REDIS_URL=redis://localhost:6379
```

### Step 4: Start Infrastructure
```bash
# Start Redis and Postgres in Docker
docker-compose -f infra/docker-compose.yml up -d

# Verify they're running
docker ps
```

### Step 5: Start Services (5 Terminals)
```bash
# Terminal 1: Backend FastAPI
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: RQ Worker
cd /path/to/onering
rq worker -u redis://localhost:6379 default

# Terminal 3: Frontend Next.js
pnpm dev
# Runs on http://localhost:3000

# Terminal 4: Stripe Webhooks (optional)
stripe listen --forward-to localhost:3000/api/stripe/webhook

# Terminal 5: Monitor logs
Get-Content path/to/pnpm-dev.log -Wait -Tail 10
```

### Step 5b: Run Tests Quickly
```bash
# Backend
cd backend && pytest -q

# Frontend
pnpm test -- --run

# Or both via helper
./scripts/run_tests.sh

# Pre-commit hook (optional): runs the same tests
./scripts/pre-commit.sh
```

### Step 6: Verify Setup
1. Navigate to `http://localhost:3000`
2. Click "Sign In" (Clerk login page)
3. Create a test account
4. You should be redirected to `/dashboard`
5. Check all indicators: Clerk UserButton, RING balance, tabs load correctly

---

## Detailed Testing Guide

### Test 1: Authentication & Dashboard
**Goal:** Verify Clerk integration and dashboard UI.

```bash
1. Go to http://localhost:3000
2. Click "Sign In"
3. Create a test Clerk account (email/password or Google)
4. Redirected to /dashboard automatically
5. Verify:
   - UserButton shows your email in top-right
   - "RING Balance: 0" displays (default)
   - All tabs load: Generate, Post to X, Post to IG, Schedule, Leaderboard
```

### Test 2: Content Generation (Streaming)
**Goal:** Verify Groq integration and FastAPI streaming.

**Prerequisites:**
- FastAPI running on `localhost:8000`
- `GROQ_API_KEY` set in `.env.local`

**Steps:**
```bash
1. On dashboard, click "Generate" tab
2. Type a prompt: "Write a viral tweet about AI"
3. Click "Generate with Groq"
4. Observe:
   - Content streams character-by-character to UI (not all at once)
   - "Copy" button copies content to clipboard
   - No errors in browser console or server logs
   - Backend logs show: [generate] prompt: ... [generate] response stream started
```

**Verify streaming:**
```bash
# In a terminal, curl the FastAPI endpoint directly:
curl -X POST http://localhost:8000/v1/generate/content/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello", "userId":"test-user-123"}' \
  -v
# Should see chunked response with tokens streaming
```

### Test 3: X Posting & RING Rewards
**Goal:** Verify thread posting, rate-limiting, and RING awarding.

**Prerequisites:**
- Twitter API credentials in `.env.local`
- Generated content (from Test 2)

**Steps:**
```bash
1. On dashboard, "Post to X Now" tab
2. Paste or generate content (multiline thread)
3. Click "Post to X Now"
4. Observe:
   - Success: Response shows tweet URL(s)
   - Posts visible on your X account within 1 second
   - Dashboard shows updated RING balance (formula: views/100 + likes�5 + retweets�10)
   - Server logs: [post-to-x] posted thread: [url1] [url2]

5. Rate-limit test:
   - Post 5 times rapid-fire
   - 6th attempt shows: "Rate limit: max 5 posts per 15 minutes"
   - Retry after 15 minutes or reset Redis:
     redis-cli DEL "posting:user:{userId}"
```

### Test 4: Instagram Posting (Mock)
**Goal:** Verify IG posting endpoint behavior.

```bash
1. On dashboard, "Post to IG Now" tab
2. Paste content
3. Click "Post to IG Now"
4. Observe:
   - Success response: "posted to IG (mock)"
   - Caption visible in response
   - No crash on error
   - Uses Graph API when tokens are set; falls back to mock otherwise
```

### Test 5: Stripe Payment & RING Bonus
**Goal:** Verify Stripe Checkout ? Webhook ? Clerk metadata update.

**Prerequisites:**
- `stripe listen` running and forwarding to `localhost:3000/api/stripe/webhook`
- `STRIPE_WEBHOOK_SECRET` set in `.env.local`
- `STRIPE_SECRET_KEY` set in `.env.local`

**Steps:**
```bash
1. On dashboard, click "Buy RING" button (or similar CTA)
2. Redirected to Stripe Checkout Session
3. Fill test card details:
   - Card: 4242 4242 4242 4242
   - Expiry: 12/25 (any future date)
   - CVC: 123 (any 3 digits)
4. Click "Pay"
5. Observe:
   - Payment succeeds (test environment)
   - Returned to dashboard
   - RING balance increases by 500 (purchase bonus)
   - `verified: true` set in Clerk metadata
   - Stripe CLI shows: event "checkout.session.completed"
   - Server logs show: [stripe/webhook] verified purchase for {userId}
```

### Test 6: Referral System
**Goal:** Verify referral code generation and claim flow.

```bash
1. On dashboard, click "Generate Referral Code"
2. Copy invite link (should be http://localhost:3000/refer?code=your-code)
3. Open incognito window, go to link
4. Clerk redirects to sign-up
5. New user creates account
6. New user completes first purchase (see Test 5)
7. Both accounts check RING balance:
   - Referrer: +50 RING (referral bonus)
   - Referee: +50 RING (referral bonus) + 500 (purchase)
```

### Test 7: RING Staking & Yield
**Goal:** Verify staking position creation and yield calculation.

```bash
1. On dashboard, look for "Stake RING" tab or feature
2. Enter amount: 100 RING
3. Select duration: 30 days (10% APR)
4. Click "Stake Now"
5. Observe:
   - Balance deducted: 100 RING
   - Staking position created (visible in "My Stakes")
   - Claimable yield: 100 � 10% / 365 � 30 � 0.82 RING (approx)
   - Wait 1-2 minutes, refresh page
   - Claimable yield increases slightly (daily accrual)
6. Claim yield:
   - Click "Claim Yield"
   - Balance updated: +0.82 RING
   - Stake duration resets (if not yet matured)
```

### Test 8: Monitoring Dashboard
**Goal:** Verify real-time system health metrics.

```bash
1. Go to http://localhost:3000/monitoring (after signing in)
2. Observe metrics:
   - Active Users (24h): non-zero if you've generated/posted
   - Total RING Circulated: sum of all user earnings
   - Post Success Rate: successful_posts / total_posts
   - Published Posts: count of all posts
   - Failed Posts: count of failed attempts
   - Avg RING/Post: average engagement reward
3. Recent Agent Workflows:
   - If you've run a generation, trace should appear
   - Shows: topic, status (generating/completed), start time, duration
4. Auto-refresh: stats update every 5 seconds without manual reload
```

### Test 9: Error Handling & Resilience
**Goal:** Verify graceful error handling.

```bash
1. Sign out, try accessing /dashboard
   - Should redirect to sign-in page
   - No blank page or 500 error

2. Generate with missing GROQ_API_KEY
   - Error message shown to user
   - No crash, dashboard stays interactive
   - Server logs show error (don't expose to client)

3. Post without Twitter credentials
   - Error message: "Twitter API credentials not configured"
   - RING not deducted
   - Rate-limit not incremented

4. Network timeout simulation:
   - Kill FastAPI backend while generating
   - Error message shown
   - Fallback: mock content or retry button
```

### Test 10: Rate-Limiting Edge Cases
**Goal:** Test rate-limit enforcement.

```bash
1. Post exactly 5 times in quick succession
   - All 5 should succeed
2. 6th post attempt shows error: "Rate limit exceeded"
3. Manually reset (admin only):
   - redis-cli DEL "posting:user:{userId}"
   - Next post succeeds immediately
```

---

## API Reference

### Frontend Routes

#### `GET /api/analytics/post`
Fetch post metrics and calculate RING earned.

```bash
curl -X GET "http://localhost:3000/api/analytics/post?externalId=1234567890"
```

Response:
```json
{
  "externalId": "1234567890",
  "views": 1000,
  "likes": 50,
  "retweets": 10,
  "replies": 5,
  "ringEarned": 175,
  "lastUpdated": "2025-12-13T12:00:00.000Z"
}
```

#### `POST /api/generate`
Stream content generation from Groq.

```bash
curl -X POST "http://localhost:3000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write a viral tweet"}'
```

Response: Streaming JSON newline-delimited events.

#### `POST /api/post-to-x`
Post thread to X (Twitter).

```bash
curl -X POST "http://localhost:3000/api/post-to-x" \
  -H "Content-Type: application/json" \
  -d '{"content":"Line 1\nLine 2\nLine 3"}'
```

Response:
```json
{
  "success": true,
  "tweetIds": ["123456789", "123456790"],
  "ringAwarded": 150
}
```

#### `POST /api/post-to-ig`
Post to Instagram (Graph API when tokens provided; falls back to mock if tokens missing).

```bash
curl -X POST "http://localhost:3000/api/post-to-ig" \
  -H "Content-Type: application/json" \
  -d '{"content":"Amazing caption"}'
```

#### `POST /api/post-to-linkedin`
Post to LinkedIn (UGC API; falls back to mock if tokens missing).

```bash
curl -X POST "http://localhost:3000/api/post-to-linkedin" \
   -H "Content-Type: application/json" \
   -d '{"content":"Ship update on LinkedIn"}'
```

#### `GET /api/analytics/ring/daily`
Returns last 7 days of RING earnings for a user.

```bash
curl "http://localhost:3000/api/analytics/ring/daily?userId=user_123"
```

#### `GET /api/analytics/ring/weekly`
Returns last 5 ISO weeks of RING earnings for a user.

```bash
curl "http://localhost:3000/api/analytics/ring/weekly?userId=user_123"
```

#### `POST /api/stripe/checkout`
Create Stripe Checkout Session.

```bash
curl -X POST "http://localhost:3000/api/stripe/checkout"
```

Response:
```json
{
  "sessionUrl": "https://checkout.stripe.com/pay/cs_live_..."
}
```

#### `POST /api/stripe/webhook`
Stripe webhook (called by Stripe, not by you).

#### `GET /api/referral/generate`
Generate unique referral code.

```bash
curl -X GET "http://localhost:3000/api/referral/generate" \
  -H "Authorization: Bearer <clerk-token>"
```

Response:
```json
{
  "code": "user-abc123",
  "inviteUrl": "http://localhost:3000/refer?code=user-abc123"
}
```

#### `POST /api/referral/claim`
Claim referral bonus (after first purchase).

```bash
curl -X POST "http://localhost:3000/api/referral/claim" \
  -H "Content-Type: application/json" \
  -d '{"referrerCode":"user-abc123"}'
```

#### `POST /api/ring/stake`
Create staking position.

```bash
curl -X POST "http://localhost:3000/api/ring/stake" \
  -H "Content-Type: application/json" \
  -d '{"amount":100,"durationDays":30}'
```

#### `GET /api/ring/stake/list`
List user's staking positions.

```bash
curl -X GET "http://localhost:3000/api/ring/stake/list"
```

#### `POST /api/ring/stake/claim`
Claim staking yield.

```bash
curl -X POST "http://localhost:3000/api/ring/stake/claim" \
  -H "Content-Type: application/json" \
  -d '{"stakeId":"stake-123"}'
```

#### `GET /api/monitoring/stats`
Get system-wide metrics.

```bash
curl -X GET "http://localhost:3000/api/monitoring/stats"
```

Response:
```json
{
  "activeUsers": 42,
  "totalRingCirculated": 12540,
  "postSuccessRate": 0.94,
  "totalPostsPublished": 328,
  "totalPostsFailed": 20,
  "avgPostEarnings": 38.25
}
```

### Backend Routes (FastAPI)

#### `POST /v1/generate/content/`
Stream content generation (called by frontend proxy).

```bash
curl -X POST "http://localhost:8000/v1/generate/content/" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write viral content","userId":"user-123","context":{}}'
```

Response: Streaming text/event-stream.

---

## Environment Variables

### Frontend (`.env.local`)

```bash
# Clerk Auth
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Groq LLM
GROQ_API_KEY=gsk_...

# Stripe Payments
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... (from stripe listen)

# Twitter/X Posting
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# Database & Cache
DATABASE_URL=postgresql://user:password@localhost:5432/onering
REDIS_URL=redis://localhost:6379
```

### Backend (`backend/.env`)

```bash
# Groq LLM
GROQ_API_KEY=gsk_...

# Twitter/X Posting
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# Stripe
STRIPE_SECRET_KEY=sk_test_...

# Database & Cache
DATABASE_URL=postgresql://user:password@localhost:5432/onering
REDIS_URL=redis://localhost:6379

# Clerk (for verification)
CLERK_SECRET_KEY=sk_...
```

### Optional Variables

```bash
# OpenAI (for user profile embeddings)
OPENAI_API_KEY=sk-...

# Instagram Graph API
INSTAGRAM_ACCESS_TOKEN=...

# TikTok API
TIKTOK_ACCESS_TOKEN=...

# YouTube Data API
YOUTUBE_API_KEY=...
```

---

## Troubleshooting

### Issue: "Port 3000 already in use"
**Solution:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill it
kill -9 <PID>

# Or use a different port
pnpm dev -- --port 3001
stripe listen --forward-to localhost:3001/api/stripe/webhook
```

### Issue: Stripe webhook not triggering
**Solution:**
1. Ensure `stripe listen` is running and shows "Ready to accept events!"
2. Check `STRIPE_WEBHOOK_SECRET` matches the output from `stripe listen`
3. Check server logs for webhook delivery errors
4. Verify webhook endpoint is publicly accessible (localhost only works with stripe CLI)

### Issue: "GROQ_API_KEY not found"
**Solution:**
1. Get API key from https://console.groq.com/keys
2. Add to `.env.local`:
   ```bash
   GROQ_API_KEY=gsk_YOUR_KEY_HERE
   ```
3. Restart frontend: `pnpm dev`

### Issue: Twitter 403 "You are not permitted to perform this action"
**Symptom:** Posting to X fails with 403 error after clicking "Post to X Now"

**Solution (Step-by-Step):**
1. **Verify Twitter API credentials exist:**
   - Open `.env.local` and confirm:
     ```bash
     TWITTER_API_KEY=...
     TWITTER_API_SECRET=...
     TWITTER_ACCESS_TOKEN=...
     TWITTER_ACCESS_TOKEN_SECRET=...
     ```
   - If missing, get them from https://developer.twitter.com/en/dashboard/keys-and-tokens

2. **Check app permissions in Twitter Developer Portal:**
   - Go to https://developer.twitter.com/en/dashboard/apps
   - Select your app
   - Click "Setup" ? "App Permissions"
   - Ensure permissions are set to: **"Read and Write and Direct Messages"** (NOT "Read-Only")
   - If changed, regenerate API keys in the "Keys and Tokens" tab

3. **Regenerate expired tokens:**
   - Go to https://developer.twitter.com/en/dashboard/keys-and-tokens
   - Click "Regenerate" for **Access Token and Secret**
   - Copy new tokens and update `.env.local`

4. **Restart frontend:**
   ```bash
   # Stop: Ctrl+C in the pnpm dev terminal
   pnpm dev
   ```

5. **Test posting again:**
   - Generate content (or paste custom)
   - Click "Post to X Now"
   - Check dashboard logs for success message

**If still failing:** Check backend logs (`uvicorn` terminal) for detailed error from Twitter API.

### Issue: "Rate limit exceeded" too quickly
**Solution:**
```bash
# Reset rate-limit via Redis
redis-cli DEL "posting:user:{userId}"

# Or wait 15 minutes for window to expire
```

### Issue: Instagram Graph API not working
**Current:** Endpoint is mocked. Real integration requires:
1. Meta App with Graph API permission
2. `INSTAGRAM_ACCESS_TOKEN` set in env
3. Update `src/app/api/post-to-ig/route.ts` to call real Graph API instead of mock

### Issue: Database connection failed
**Solution:**
```bash
# Verify Postgres is running
docker ps | grep postgres

# If not running, start it
docker-compose -f infra/docker-compose.yml up -d

# Check connection string
echo $DATABASE_URL
```

### Issue: RQ worker not processing jobs
**Solution:**
```bash
# Verify Redis is running
redis-cli ping
# Should respond: PONG

# Restart worker
rq worker -u redis://localhost:6379 default

# Check job queue
redis-cli LRANGE rq:queue:default 0 -1
```

### Issue: LangGraph agent errors
**Solution:**
1. Verify FastAPI is running: `curl http://localhost:8000/docs`
2. Check backend logs for agent execution errors
3. Ensure all dependencies installed: `pip install -r backend/requirements.txt`
4. Verify Groq API key is set in `backend/.env`

### Issue: TypeScript compilation errors
**Solution:**
```bash
# Rebuild TypeScript
pnpm build

# Or check errors
pnpm lint

# Fix common issues
pnpm run lint -- --fix
```

### Issue: Clerk authentication not working
**Solution:**
1. Verify Clerk project exists at https://dashboard.clerk.com
2. Check `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`
3. Ensure redirect URIs are configured in Clerk dashboard (localhost:3000)

### Issue: Backend returns 404 on /v1/generate/content
**Problem:** Frontend calls backend but gets 404 "Not Found".

**Root Cause:** Backend is being run from the project root instead of the backend/ directory, so Python can't find the `main` module.

**Solution:**
```bash
# WRONG - Will fail with 404
cd c:\Users\hazar\onering
python -m uvicorn main:app --port 8000  # ? Can't find main module

# RIGHT - Use the persistent runner
python run_backend.py  # ? Handles directory changes automatically
```

**Verify backend is working:**
```bash
# In another terminal
curl http://localhost:8000/v1/test
# Should return: {"message":"Backend is running","version":"0.1.0"}
```

**Frontend logs will show:**
```
[generate] calling backend: http://localhost:8000/v1/generate/content
[generate] backend error: 404 {"detail":"Not Found"}  # ? Backend not running
```

### Issue: Backend process exits after ~8 seconds (Windows)
**Problem:** Backend starts but exits shortly after without error.

**Root Cause:** Windows PowerShell background process management issue.

**Solution:** Use `python run_backend.py` which handles process lifecycle correctly:
```bash
python run_backend.py  # Auto-restarts if process exits
```

**Monitoring:**
```
[2025-12-13 20:00:38] INFO: Starting backend (uvicorn on port 8000)...
[2025-12-13 20:00:38] INFO: Backend process started (PID: 30008)
[2025-12-13 20:00:58] INFO: Health check OK
[2025-12-13 20:01:28] INFO: Health check OK
```

If health checks fail, the runner automatically restarts the backend.

### Issue: Backend startup says "Application startup complete" but no response
**Problem:** Backend appears to start (logs say "startup complete") but then exits without responding to requests.

**Solution:** This is the same Windows process management issue. Use the persistent runner:
```bash
python run_backend.py  # Persistent runner stays alive
```

````

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Architecture & Design

- **Architecture:** See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for canonical decisions
- **API Docs:** See [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **Agent Specs:** See [docs/AGENTS_OVERVIEW.md](docs/AGENTS_OVERVIEW.md)
- **RING Token:** See [docs/tokens/RING_TOKEN.md](docs/tokens/RING_TOKEN.md)

---

## Support

- Open an issue on GitHub
- Check [Troubleshooting](#troubleshooting) above
- Read `.ai/context.md` for detailed environment setup
- Consult [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for architecture questions

---

## License

[LICENSE](LICENSE) (Proprietary or your choice)

---

**Last Updated:** Dec 13, 2025
**Version:** Beta v0.1.0

See backend/README.md for instructions.

---

## Hardened Contracts & Deterministic Behavior

### Hard Guarantees
- No tests require real API keys; external services are fully mockable.
- Streaming and non-streaming generation share identical validation logic.
- Numbering in generated content is stripped deterministically (1., [2], (3), 1/6, bullets).
- Temporal retries are deterministic with stable idempotency keys; RQ jobs are wrapped safely (no duplicate scheduling).
- API contracts are locked via tests and OpenAPI snapshots; undocumented 422s are prohibited.
- Frontend Zod schemas mirror backend Pydantic models; invalid payloads are rejected client-side.
- Importing any Next.js route does not initialize network connections (lazy init everywhere).

### API Contracts
- POST /v1/generate/content: { prompt: string, type: 'simple'|'viral_thread', platform: string, user_id: string, stream?: boolean }
- GET /api/analytics/ring/daily: { userId: string } ? { userId, range: '7d', series: Array<{ date, total }> }
- GET /api/analytics/ring/weekly: { userId: string } ? { userId, range: '5w', series: Array<{ date, total }> }
- POST /api/post-to-x: { content } ? { success, url?, remaining?, error? }
- POST /api/post-to-ig: { content } ? { success, id?, remaining?, error? }
- POST /api/post-to-linkedin: { content } ? { success, id?, remaining?, error? }

### Test Commands
- Backend: `cd backend && pytest -q`
- Frontend: `pnpm test -- --run`
- Combined (Linux/macOS): `./scripts/run_tests.sh`
- Combined (Windows): `./scripts/run_tests.ps1`

### Pre-Commit Hooks
Enable repository hooks to block commits on failing tests:
- Windows PowerShell: `git config core.hooksPath .githooks && ./.githooks/pre-commit.ps1`
- Bash: `git config core.hooksPath .githooks && chmod +x .githooks/pre-commit`



