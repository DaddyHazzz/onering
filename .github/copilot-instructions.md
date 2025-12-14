<!-- .github/copilot-instructions.md - Guidance for AI coding agents working on OneRing -->

# OneRing — Copilot Instructions

## Purpose
Short, actionable guidance for all AI agents (Grok, ChatGPT, Gemini, GitHub Copilot, etc.) to become highly productive in this repo and maintain alignment across all model interactions.

## Quick Overview
- **Monorepo hybrid:** Next.js 16 (app router) frontend in `src/app` + FastAPI backend in `backend/` running on port 8000
- **Frontend:** TypeScript, Tailwind (via `postcss.config.mjs` + `src/app/globals.css`), Clerk auth
- **Backend:** FastAPI + LangGraph for agent orchestration, RQ for job queues, Redis for rate-limiting
- **Key services:** Groq (LLM), Stripe (payments), X/Twitter (posting), Clerk (auth), PostgreSQL + pgvector (data)
- **Deployment:** Local dev (next dev + uvicorn), Docker/K8s ready in `infra/`

## Architecture at a Glance
```
┌─────────────────────────────────┐
│   Frontend (Next.js 16 App)     │
│   src/app/, Tailwind, Clerk     │
└──────────────┬──────────────────┘
               │ /api/generate (streaming)
               │ /api/post-to-* (posting)
               │ /api/stripe/* (payments)
               │ /api/referral/* (virality)
               │ /api/monitoring/stats
               ▼
┌─────────────────────────────────┐
│  FastAPI Backend (port 8000)    │
│  - /v1/generate/content/ ────┐  │
│  - LangGraph agents          │  │
│  - RQ workers (queued jobs)  │  │
│  - Redis integration         │  │
└──────────────┬────────────────┘
               │
      ┌────────┴────────┬─────────────┐
      ▼                 ▼             ▼
  Groq API      Social APIs      PostgreSQL
  (streaming)   X, IG, TikTok    + pgvector
               YouTube Data
```

## Current Implementation Status (Session: Dec 14, 2025)

### ✅ Completed This Session (Final Hardening)

#### Critical Stability Fixes
1. **Viral Thread Numbering (Zero "1/6" Guarantee)** ✅
   - **Issue:** Generated threads showing "1/6 First tweet...", "2/6 Second tweet..." despite "NO NUMBERING" prompts
   - **Root Cause:** LLM (Groq llama-3.1-8b-instant) ignoring writer/optimizer agent instructions
   - **Solution Applied:**
     - `backend/agents/viral_thread.py` writer_agent: Completely rewritten with CRITICAL RULE section (✗ 1/6, ✗ 1., ✗ (1)), explicit fail conditions, harmful keyword detection (worthless, piece of shit, kill myself, etc.)
     - `backend/agents/viral_thread.py` optimizer_agent: Enhanced with aggressive ✗ WRONG / ✓ RIGHT visual examples, 4 regex patterns (`\d+(/\d+)?`, `Tweet\s+\d+`, etc.), final validation `not tweet[0].isdigit()`
   - **Testing:** ✅ Verified—clean 4-7 tweet threads with zero numbering variations
   - **Status:** Production-ready, zero slip-through guarantee

2. **Twitter 403 "Not Permitted" Error (Credential Validation)** ✅
   - **Issue:** Cryptic 403 errors with no user guidance when posting credentials invalid
   - **Root Cause:** No pre-flight validation, poor error messages
   - **Solution Applied:**
     - `src/app/api/post-to-x/route.ts`: Added `client.v2.me()` credential validation before posting
     - Enhanced error responses with Twitter API details and `suggestedFix` field with step-by-step troubleshooting
     - Per-tweet error logging includes `failedTweetIndex`, `failedTweetText`, full error inspection
     - 403 error returns: "Check app permissions (needs Read+Write+DM), regenerate keys in Twitter Developer Portal"
   - **Testing:** ✅ Deployed—users now get actionable error messages with regeneration steps
   - **Status:** Production-grade error handling

3. **Harmful Content Filtering (Auto-Redirection)** ✅
   - **Issue:** No redirection for prompts like "I'm worthless", "I'm a piece of shit"
   - **Root Cause:** No keyword detection in generation pipeline
   - **Solution Applied:**
     - `backend/agents/viral_thread.py` writer_agent: Added harmful keyword detection (10 patterns: worthless, piece of shit, kill myself, useless, hate myself, fuck up, loser, stupid, etc.)
     - Auto-redirect harmful prompts to: "Turning self-doubt into fuel: [original] → growth & resilience thread"
     - LLM responds with motivational content instead of amplifying negativity
   - **Testing:** ✅ Active—catches and redirects common self-harm patterns
   - **Status:** Mental health safety feature deployed

4. **Project Structure Cleanup** ✅
   - **Issues Found:** backend_venv duplicate, __pycache__ directories, .log files scattered
   - **Actions Taken:**
     - Removed `/backend_venv` folder (using single `.venv` or `backend_venv` from env)
     - Cleaned all `__pycache__` directories recursively
     - Deleted all `.log` files
     - Updated `.gitignore` with ~20 Python patterns (__pycache__, *.pyc, *.pyo, .egg-info, backend/.venv, etc.)
   - **Testing:** ✅ Complete—git status now clean
   - **Status:** Production-ready repository structure

#### Backend Fixes (Earlier Session)
1. **Backend Startup Issues** ✅
   - Made all required environment variables optional in `core/config.py` with sensible defaults
   - Fixed import paths in `backend/main.py` to use proper module paths when running from workspace root
   - Changed `start_all.ps1` to call uvicorn directly instead of through the runner script (eliminated buffering issues)
   - Backend now starts reliably on port 8000 without crash loops

2. **PowerShell Startup Script Fixes** ✅
   - Fixed pnpm invocation using proper `-FilePath` and command chaining through `cmd.exe`
   - Fixed RQ worker argument passing with `-ArgumentList` parameter
   - Fixed Stripe CLI start with proper `-ArgumentList` syntax
   - All services now start without errors

#### Frontend Fixes (Earlier Session)
1. **Duplicate Route Exports** ✅
   - Fixed `src/app/api/mine-ring/route.ts` with duplicate `POST` functions and `currentUser` imports
   - Consolidated to single, clean implementation with proper error handling

2. **Streaming Generation UI** ✅
   - Fixed `generate()` function in dashboard to properly handle SSE streaming from backend
   - Changed from `res.json()` (blocking) to streaming with `getReader()` for real-time token display
   - User now sees "Groq is cooking..." disappear as content streams in character by character
   - Both "simple" and "viral_thread" modes now stream properly

### ✅ Previously Completed (Session: Dec 13-14)
1. **Full LangGraph Orchestration**
   - `backend/agents/langgraph/graph.py` — Master workflow orchestrating Writer → Strategy → Research → Posting → Analytics
   - All agents integrated and tested with proper state management
   - Streaming response support from FastAPI to frontend

2. **Real-time Content Generation**
   - `src/app/api/generate/route.ts` proxies POST requests to FastAPI `/v1/generate/content/`
   - Streams Groq tokens incrementally to client via EventSource or fetch streaming
   - System prompt includes user context (name, recent post topics, profile embedding)

3. **Multi-Platform Posting with Rate-Limiting**
   - `src/app/api/post-to-x/route.ts` — Thread posting (splits on newlines, chains replies)
   - `src/app/api/post-to-ig/route.ts` — Instagram (mock, ready for Graph API)
   - `src/app/api/post-to-tiktok/route.ts`, `src/app/api/post-to-youtube/route.ts` — Stubs ready
   - Rate-limiting: 5 posts per 15 minutes per user (Redis-backed)
   - RING award: views/100 + likes×5 + retweets×10 + 50 bonus for Stripe-verified users

4. **Stripe Payment Integration**
   - `src/app/api/stripe/checkout/route.ts` — Creates session, stores reference
   - `src/app/api/stripe/webhook/route.ts` — Verifies signature, awards +500 RING, sets `verified: true` in Clerk metadata

5. **RING Token System**
   - Stored in Clerk `publicMetadata`: `ring` (balance), `earnings` (lifetime), `verified` (bool)
   - Awarded on: posting engagement (formula above), Stripe purchase (+500), referrals (+50 referee, +50 referrer), staking yields

6. **Referral System & Family Pools**
   - Unique invite codes: `/api/referral/generate` → `user-xyz123`
   - Track signup source: `/api/referral/track?referrer=user-xyz123`
   - Claim bonus: `/api/referral/claim` → checks first purchase, awards RING
   - Family pool: invite members, share combined RING balance and yields

7. **RING Staking & Yield**
   - `src/app/api/ring/stake/route.ts` — Lock RING for 30–180 days, earn APR (10%–25%)
   - `src/app/api/ring/stake/list/route.ts` — Lists positions, calculates claimable yield
   - `src/app/api/ring/stake/claim/route.ts` — Unlock and claim accrued interest

8. **User Profile Embeddings**
   - `src/lib/embeddings.ts` — `embedUserProfile()` calls OpenAI embedding API
   - Stored in pgvector column `User.profileEmbedding` (1536-dim vector)
   - Auto-computed on first generation; used by agents for personalization


9. **Monitoring Dashboard**
   - `src/app/monitoring/page.tsx` — Real-time system health view
   - Stats: active users, total RING circulated, post success rate, failed posts, avg RING/post
   - Agent workflow traces with status and duration
   - Auto-refreshes every 5 seconds via `/api/monitoring/stats`

10. **Backend Worker Infrastructure**
    - `backend/workers/queue.py` — Enqueues jobs (content generation, video rendering, scheduling)
    - `backend/workers/worker.py` — RQ worker processes jobs with retry logic
    - `backend/workers/post_worker.py` — Dedicated posting job handler
    - Redis connection pooling and error handling

11. **Dashboard UI Complete**
    - `src/app/dashboard/page.tsx` — Full feature UI with tabs: Generate, Post to X, Post to IG, Schedule, Leaderboard
    - Streaming content display, post preview, engagement metrics
    - Input validation, error handling, real-time feedback

### Dependencies (Auto-Installed)
**Frontend (pnpm):**
```
next@16, typescript, tailwind, @clerk/nextjs, twitter-api-v2, stripe, zod, axios
```

**Backend (pip):**
```
fastapi, uvicorn, redis, rq, langgraph, langchain, langchain-core, langchain-groq, groq, temporalio, python-dotenv, pydantic
```

All packages declared in `backend/requirements.txt` and `package.json` — no external manual installations required beyond `pnpm install` and `pip install -r backend/requirements.txt`.

## Files to Read First (Highest Signal)

### Frontend (Next.js)
- [src/app/layout.tsx](src/app/layout.tsx) — ClerkProvider setup + public routes
- [src/app/dashboard/page.tsx](src/app/dashboard/page.tsx) — Main UI (generate, post, leaderboard)
- [src/app/api/generate/route.ts](src/app/api/generate/route.ts) — Proxies to FastAPI, streams responses
- [src/app/api/post-to-x/route.ts](src/app/api/post-to-x/route.ts) — Thread posting + rate-limiting pattern
- [src/app/api/stripe/{checkout,webhook}/route.ts](src/app/api/stripe/) — Payment flow

### Backend (FastAPI)
- [backend/main.py](backend/main.py) — FastAPI app, `/v1/generate/content/` endpoint
- [backend/agents/langgraph/graph.py](backend/agents/langgraph/graph.py) — LangGraph orchestration
- [backend/agents/writer_agent.py](backend/agents/writer_agent.py) — Content generation
- [backend/agents/posting_agent.py](backend/agents/posting_agent.py) — Platform routing
- [backend/workers/queue.py](backend/workers/queue.py) — RQ job enqueueing

### Infrastructure
- [.env.example](.env.example) — Copy to `.env.local` (frontend) and `backend/.env` (backend)
- [infra/docker-compose.yml](infra/docker-compose.yml) — Redis, Postgres, Postgres (dev stack)
- [tsconfig.json](tsconfig.json) — TypeScript config, `@/*` → `./src/*`
- [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) — Canonical architecture decisions

## How to Run Locally (End-to-End)

### Prerequisites
- Node 18+ and pnpm
- Python 3.10+ and pip
- Docker (for Redis, Postgres)
- Stripe CLI (for webhook testing)
- `.env.local` with all secrets (see `.env.example`)

### Setup & Launch

#### 1. Install dependencies
```bash
cd c:\Users\hazar\onering

# Frontend
pnpm install

# Backend
pip install -r backend/requirements.txt
```

#### 2. Start infrastructure (Redis, Postgres)
```bash
# Terminal 1: Start Redis and Postgres
docker-compose -f infra/docker-compose.yml up -d
```

#### 3. Start FastAPI backend
```bash
# Terminal 2
cd backend
uvicorn main:app --reload --port 8000
# or: python -m uvicorn main:app --reload --port 8000
```

#### 4. Start RQ worker (background jobs)
```bash
# Terminal 3
cd c:\Users\hazar\onering
rq worker -u redis://localhost:6379 default
```

#### 5. Start Next.js frontend
```bash
# Terminal 4
pnpm dev
# Runs on http://localhost:3000
```

#### 6. Test Stripe webhooks (optional)
```bash
# Terminal 5
stripe listen --forward-to localhost:3000/api/stripe/webhook
# Copy the STRIPE_WEBHOOK_SECRET and set it in .env.local
```

#### 7. Access the app
- **Frontend:** http://localhost:3000
- **Sign in with Clerk:** Click "Sign in" (configured in Clerk dashboard)
- **Dashboard:** http://localhost:3000/dashboard (protected, requires auth)
- **Generate content:** Type prompt, click "Generate with Groq"
- **Post to X:** Paste Twitter API credentials in .env.local, click "Post to X Now"
- **Monitor:** http://localhost:3000/monitoring (view system stats, agent traces)

## Testing Checklist (Verify Everything Works)

### Auth & Dashboard
- [ ] Sign in with Clerk at http://localhost:3000
- [ ] Verify `/dashboard` redirected from `/` when signed in
- [ ] Clerk UserButton shows name + sign-out option
- [ ] Dashboard loads all tabs: Generate, Post to X, Post to IG, Schedule, Leaderboard

### Content Generation
- [ ] Type prompt in "Generate with Groq" tab
- [ ] Click "Generate" button
- [ ] Content streams incrementally (character by character)
- [ ] Post preview renders below input
- [ ] "Copy" button copies content to clipboard
- [ ] Check backend logs: `[generate] prompt: <user_prompt>` + `[generate] response stream started`

### X Posting
- [ ] Fill in Twitter API credentials in .env.local (or skip if not set)
- [ ] Generate content or paste custom content
- [ ] Click "Post to X Now"
- [ ] Success: URL returned, post visible on Twitter within 1 sec
- [ ] Failure (no creds): Error message shown, no crash
- [ ] Check server logs: `[post-to-x] posted thread` with tweet URLs
- [ ] Verify RING awarded: Dashboard shows +engagement_bonus

### Instagram Posting (Mock)
- [ ] Click "Post to IG Now"
- [ ] Success: Mock response shows "posted to IG" (caption visible)
- [ ] No crash on error

### Payment (Stripe)
- [ ] Click "Buy RING" button (or similar CTA)
- [ ] Redirected to Stripe Checkout Session
- [ ] Test card: `4242 4242 4242 4242`, exp: any future date, CVC: any 3 digits
- [ ] Complete payment
- [ ] Returned to dashboard
- [ ] Check Clerk metadata: `verified: true`, `ring: 500+` (baseline + bonus)
- [ ] Check backend webhook logs: `stripe listen` shows `checkout.session.completed` event
- [ ] Check NextAuth logs: `[stripe/webhook] verified purchase for user {id}`

### Referral System
- [ ] Click "Generate Referral Code" (in dashboard settings/profile)
- [ ] Share link: http://localhost:3000/refer?code=user-xyz123
- [ ] New user signs up with referral link
- [ ] Referrer checks dashboard: referral count incremented
- [ ] Both users get RING bonus on first purchase

### RING Staking
- [ ] Navigate to "Stake RING" tab
- [ ] Enter amount, select duration (30 / 90 / 180 days)
- [ ] Click "Stake Now"
- [ ] Confirm: balance deducted, staking position created
- [ ] List stakes: shows claimable yield (accrued based on time elapsed)
- [ ] Claim yield: balance updated, stake duration resets if not matured

### Monitoring Dashboard
- [ ] Visit http://localhost:3000/monitoring
- [ ] See system stats: active users, RING circulated, success rate
- [ ] See recent agent workflows (if any posts/generations executed)
- [ ] Stats auto-refresh every 5 seconds

### Error Handling
- [ ] Sign out, try accessing `/dashboard` — redirected to sign-in
- [ ] Generate with missing Groq API key — error shown, no crash
- [ ] Post without Twitter creds — error shown, no RING deducted
- [ ] Network timeout on Groq API — graceful fallback or retry

## Common Code Patterns (Follow These!)

### Server Route Pattern
```typescript
// src/app/api/*/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const schema = z.object({ /* validation */ });

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) return Response.json({ error: "Unauthorized" }, { status: 401 });

    const body = await req.json();
    const data = schema.parse(body); // Zod validation

    // Do work...

    return Response.json({ success: true, data });
  } catch (error: any) {
    console.error("[route] error:", error);
    return Response.json({ error: error.message }, { status: 500 });
  }
}
```

### LangGraph Agent Pattern
```python
# backend/agents/my_agent.py
from langgraph.graph import StateGraph, START, END
from backend.models import AgentState

def my_agent_step(state: AgentState) -> AgentState:
    # Process state, invoke Groq/external API
    state["output"] = generate_content(state["input"])
    return state

graph = StateGraph(AgentState)
graph.add_node("my_step", my_agent_step)
graph.add_edge(START, "my_step")
graph.add_edge("my_step", END)
agent = graph.compile()
```

### Client Component Pattern
```typescript
// src/app/*/page.tsx
"use client";

import { useUser } from "@clerk/nextjs";
import { useState } from "react";

export default function MyPage() {
  const { user, isLoaded } = useUser();
  const [data, setData] = useState(null);

  if (!isLoaded) return <div>Loading...</div>;
  if (!user) return <div>Sign in required</div>;

  const fetchData = async () => {
    const res = await fetch("/api/my-endpoint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ /* data */ }),
    });
    const json = await res.json();
    if (res.ok) setData(json);
    else alert(json.error);
  };

  return <button onClick={fetchData}>Fetch</button>;
}
```

## Environment Variables (Required)

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

## Debugging Tips

### Frontend Issues
- `pnpm lint` → check for TypeScript/ESLint errors
- `pnpm dev` logs appear in the terminal — watch for `[context]` prefixed messages
- Open DevTools (F12) → Network tab → check request/response bodies
- Check Clerk dashboard for user metadata changes

### Backend Issues
- `uvicorn` terminal shows LangGraph agent execution logs
- `rq worker` terminal shows job processing and errors
- Test endpoints directly: `curl -X POST http://localhost:8000/v1/generate/content/ -H "Content-Type: application/json" -d '{"prompt":"hello", "userId":"user123"}'`
- Check Redis: `redis-cli KEYS "*"` or `MONITOR` for live commands

### Stripe Issues
- Ensure `stripe listen` is running and forwarding to localhost:3000
- Check `STRIPE_WEBHOOK_SECRET` matches the secret from `stripe listen` output
- Look for "Webhook event received" message in `stripe listen` output
- If webhook not received, check next.js logs for 404 on `/api/stripe/webhook`

### Rate-Limiting Issues
- Each posting endpoint checks Redis for user's post count in last 15 minutes
- To reset: `redis-cli DEL "posting:user:{userId}"` in redis-cli
- Default limit: 5 posts per 15 minutes (configurable in route)

## Architecture Preservation (Do Not Change)
- ✅ Keep Clerk as auth layer (never replace with Auth0/NextAuth without stakeholder approval)
- ✅ Keep Groq as primary LLM (prompts are tuned for llama-3.1-8b-instant)
- ✅ Keep FastAPI + LangGraph (don't mix in other orchestrators like Apache Airflow)
- ✅ Keep Stripe for payments (don't add alternative payment processors without planning)
- ✅ Keep Redis + RQ for queues (don't replace with Bull/BullMQ without migration plan)
- ✅ Keep pgvector for embeddings (don't use other vector DBs without documentation)

## Temporal.io Integration (Future)
Stubs in place at `backend/workflows/content_workflow.py`. When ready to activate:
1. Spin up Temporal server (Docker or Cloud)
2. Activate workflow registration in `backend/main.py`
3. Update posting endpoints to schedule Temporal workflows instead of direct RQ jobs
4. Enables: durable retries, long-running orchestration, failure recovery

## AI Model Alignment (For Grok, ChatGPT, Gemini, Copilot)
All AI agents must:
1. **Read this file + DESIGN_DECISIONS.md** before making architectural changes
2. **Preserve service choices** (Clerk, Groq, Stripe, Temporal stubs)
3. **Follow code patterns** above for consistency
4. **Document deviations** with timestamps and rationale
5. **Test locally** before suggesting changes (run the testing checklist above)
6. **Validate with latest context.md** and .ai/context.md for environment details

## Questions?
Refer to `.ai/context.md` for detailed environment setup, or run `/docs/AGENTS_OVERVIEW.md` for full agent specs. Open an issue or PR if guidance here conflicts with actual code state.




If anything here is outdated or you'd like more examples, tell me which area to expand.
