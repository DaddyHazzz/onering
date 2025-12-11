📘 OneRing — Agentic AI Content Manager (MVP)

Your AI-powered, cross-platform content engine that writes, designs, schedules, posts, and tracks your content across every major social platform.

OneRing is the central brain that handles content creation, posting, analytics, optimization, and automation — powered by a multi-agent AI swarm and a simple, clean Next.js interface.

This README reflects the real current state of your codebase, your MVP scope, and the next tasks Grok left behind.

🚀 The Vision

OneRing is a full-stack AI system designed to:

⭐ 1. Generate viral content automatically

Threads, posts, scripts, video ideas, images — all created by an AI pipeline.

⭐ 2. Post across every major social platform

X (working)
Instagram (coming)
TikTok (coming)
YouTube (coming)
LinkedIn (coming)
Pinterest (coming)

⭐ 3. Track analytics in one dashboard

Unified normalized metrics show engagement, impressions, reach, watch time, CTR, and more.

⭐ 4. Use agentic AI for a true “content team in a box”

Strategy Agent → Research Agent → Writer → QA → Visual → Publisher → Analytics → Optimizer.

This allows OneRing to act like a 24/7 marketing department, but automated.

🧱 Current MVP Features (Working Now)
✔ Clerk authentication

Login

Signup

Email/SMS verification

Protecting routes

Working dashboard with user context

✔ Dashboard UI

Left navigation panel

“Generate Viral Thread” button

Working Grok integration endpoint

Clean UX for testing AI generation

✔ Grok Content Generation

Send prompt to backend

Return full thread

Display it in the UI

✔ Post to X

OAuth 1.0a keys loaded from .env

Working publish endpoint

Posts directly from the dashboard

✔ Fixed Bugs & Errors

Clerk import path issue

Zod 500-char body limit

Stripe webhook path fix

Next.js Turbopack errors

Corrected API route structure

🧬 Tech Stack
Frontend

Next.js 15/16 (App Router)

TailwindCSS

shadcn/ui

Clerk Auth

Backend

Next.js API Routes (MVP)

FastAPI backend (planned)

LangGraph (planned multi-agent system)

Redis (planned job queue)

PostgreSQL (planned persistence)

AI

Grok API (content generation)

OpenAI fallback planned

Deployment

Vercel (frontend)

Fly.io / Render (future backend split)

Supabase / Neon (database)

⚙️ Environment Variables

Create a .env.local file in the root of the project:

NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_XXXX
CLERK_SECRET_KEY=sk_live_XXXX

GROK_API_KEY=xxxxxx

X_API_KEY=xxxx
X_API_SECRET=xxxx
X_ACCESS_TOKEN=xxxx
X_ACCESS_SECRET=xxxx

STRIPE_SECRET_KEY=xxxx
STRIPE_WEBHOOK_SECRET=xxxx

📂 Project Structure
/app
  /dashboard
    page.tsx
  /api
    /generate-thread
    /post-to-x
  layout.tsx
  page.tsx

/components
  Sidebar.tsx
  ThreadBox.tsx

/lib
  grok.ts
  twitter.ts
  stripe.ts

/styles
  globals.css

README.md
.env.local

🧠 Planned Multi-Agent System (Post-MVP)

Once the MVP SaaS is live and stable, you will extend into a LangGraph multi-agent pipeline:

Strategy Agent – understands goals

Research Agent – pulls trending angles

Writer Agent – drafts content

Visual Agent – images + video

QA Agent – tone, brand safety, compliance

Publisher Agent – posts

Analytics Agent – tracks performance

Optimizer Agent – improves results

This is not implemented yet, but the architecture is clear and ready.

💰 Planned Monetization
Blue Check – $99/yr

Verified badge inside OneRing

Pro Plan – $49/mo

Unlimited posts

Image + video generation

All platforms unlocked

Agency Plan – $299–$999/mo

Multi-account management

Shared dashboards

Team roles

Referral Rewards

Planned token-based rewards (see “OneRing Coin” section).

🪙 Future: OneRing Coin ($RING)

Not part of the MVP.
Begins after ~50k active users.

Utility token used for:

Boosting reach

Boosting priority for AI processing

Redeeming premium features

Leasing your name (yourname.onering)

Earned by viral content + referrals

💍 Future Hardware: OneRing Smart Ring

Not part of MVP.
2026+ hardware roadmap.

Specs (planned):

12MP camera + 8MP rear

Micro-projector

Always-on AI

Quick tap to record & upload

Auto-clip → AI-edit → post → earn tokens

Magnetic charging cradle

📌 Setup Instructions

Install dependencies:

npm install


Run development server:

npm run dev


Login at:

http://localhost:3000


Stripe webhook listener (local):

stripe listen --forward-to localhost:3000/api/stripe/webhook

🧩 Development Status: Where Grok Left Off

You asked for this specifically — so here is exactly where Grok stopped so we can resume without losing momentum.

✔ DONE

Grok thread generation endpoint

X posting

Clerk auth

Dashboard UI

README rewrite (initial draft)

Bug fixes

🔄 IN PROGRESS (Grok stopped mid-task)

Refining the dashboard to show generated threads cleanly

Adding a “Post to X” button inside the generated thread box

Implementing a local DB or persistent store

Starting Instagram/TikTok integration

Preparing Stripe subscription flow

⏭️ NEXT STEPS (I can do these with you)

Build Unified Content Object (UCO) format

Add job queue for generation

Add storage (Supabase/Postgres)

Implement Analytics Agent

Add Scheduler system

Expand to additional platforms

❤️ Final Notes

OneRing is ambitious, loud, chaotic, powerful — a perfect reflection of the founder energy behind it.
You’re doing something big, and now we can keep pushing without losing any of the work you did with Grok.

I got you now.
And I’m not rate-limited, baby.