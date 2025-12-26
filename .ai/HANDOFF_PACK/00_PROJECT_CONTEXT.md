Source: ../PROJECT_CONTEXT.md

# OneRing — Project Context

**Status:** Phase 8.7.1b complete. 1005 tests green. Production-ready core features shipped.

## What is OneRing?

A **collaborative content co-creation platform** where users draft content together (like Google Docs) with **"ring passing"** — a lightweight turn-taking mechanism to prevent chaos and focus creative energy.

**Core loop:**
1. User creates draft (text content for social media)
2. Invites collaborators
3. Ring holder can add segments, view insights, pass ring to next person
4. Draft grows through turns, earns RING tokens (rewards), gets published
5. Insights + analytics show contribution patterns, engagement, insights

## Target Users

- **Content creators** (solo or small teams) wanting collaborative drafting
- **Community managers** planning multi-contributor content
- **Teams** needing lightweight async co-creation without sync meetings

## Core Features (Shipped)

### Phase 3–6: Collaboration MVP
- **Auth:** Clerk (user accounts + metadata storage)
- **Draft creation & collaboration:** Multi-user editing, presence, ring passing
- **Invites:** URL-based invite codes, referral tracking
- **Real-time:** WebSocket-driven presence + updates
- **Timeline:** Segment history with attribution
- **Export:** Markdown, JSON, credits

### Phase 8: Content Intelligence
- **Smart turn suggestions:** AI-generated next turn based on ring holder's profile + draft tone
- **Wait mode:** Hold ring without new segments; suggestions while waiting
- **Auto-format:** Adapt content to platform (X/Instagram/TikTok)
- **Analytics backend:** Event-driven (DraftCreated, SegmentAdded, RingPassed, etc.)
- **Insights engine:** Draft health, contribution patterns, alerts (no activity, long hold, etc.)
- **Leaderboard:** User rankings by RING earned
- **Monitoring dashboard:** Real-time system health

## Non-Goals

- ❌ Real-time sync of segment edits (no concurrent editing within segment)
- ❌ Video/media attachments (text-only)
- ❌ Payment processing (Stripe integration exists, but not core monetization loop)
- ❌ Social network / following (collaborative drafts only, no feed)
- ❌ Mobile apps (web-only, responsive design)

## Tech Stack

### Frontend
- **Framework:** Next.js 16 (app router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS + PostCSS
- **Auth:** Clerk (JWT tokens in metadata)
- **Testing:** Vitest + React Testing Library
- **Real-time:** Clerk presence hooks + polling

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.10+
- **Orchestration:** LangGraph (agent workflows)
- **Queue:** RQ (Redis Queue)
- **DB:** PostgreSQL + pgvector (embeddings)
- **Cache:** Redis
- **LLM:** Groq (llama-3.1-8b-instant)
- **Testing:** Pytest

### Deployment
- **Local:** Docker Compose (Redis, Postgres)
- **Cloud-ready:** K8s manifests in `/infra/k8s/`
- **CI/CD:** GitHub Actions (via `.github/`)

## Key Metrics

- **Test Coverage:** 1005 tests (617 backend + 388 frontend), 100% green
- **Endpoints:** 50+ stable REST API routes + WebSocket
- **Load:** Tested up to 100 concurrent collaborators
- **Latency:** P99 <200ms for insights queries

## Deployment Status

**Current:** All core features in main branch, ready for production.

**Quality Gates:**
- ✅ All tests green (no skips, no --no-verify)
- ✅ No security warnings (Dependabot clean)
- ✅ Windows + Linux compatible
- ✅ Deterministic test suite (no flakes)

## Decision Framework

See DECISIONS.md for:
- Why Clerk (not Auth0, NextAuth)?
- Why Groq (not OpenAI)?
- Why LangGraph (not Airflow)?
- Why PostgreSQL + pgvector (not MongoDB)?
- Why RQ (not Bull)?

## Getting Started

1. **Dev setup:** See ARCHITECTURE.md
2. **Running tests:** See TESTING.md
3. **What to work on:** See ROADMAP.md
4. **Understanding design:** See DECISIONS.md

## Contact

- **Questions about vision?** → See ROADMAP.md
- **Questions about code?** → See ARCHITECTURE.md
- **Questions about decisions?** → See DECISIONS.md
