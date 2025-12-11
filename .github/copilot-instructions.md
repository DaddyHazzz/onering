<!-- .github/copilot-instructions.md - Guidance for AI coding agents working on OneRing -->

# OneRing — Copilot Instructions

Purpose
- Short, actionable guidance for AI coding agents to become productive in this repo.

Quick overview
- Monorepo-style project with a Next.js 16 (app router) frontend in `src/app` and a small FastAPI backend skeleton in `backend/`.
- Frontend uses TypeScript, Tailwind (via `postcss.config.mjs` + `src/app/globals.css`), and Clerk for auth (`@clerk/nextjs`).

Key workflows (local)
- Install deps: prefer `pnpm install` (repo contains `pnpm-lock.yaml`); `npm install` also works.
- Start frontend dev server: `pnpm dev` (runs `next dev`).
- Build for production: `pnpm build` then `pnpm start`.
- Lint: `pnpm lint`.
- Backend dev (see `backend/README.md`): create Python venv, `pip install -r requirements.txt`, run Redis via `docker-compose -f infra/docker-compose.yml up -d`, run `uvicorn main:app --reload --port 8000`, and start an RQ worker with `rq worker -u redis://localhost:6379 default`.

Architecture notes (important to preserve)
- Frontend: `src/app` is an app-router Next.js project. Server routes are implemented as route handlers under `src/app/api/*/route.ts` and use `NextRequest` and `Response.json`.
- Authentication: `src/app/layout.tsx` wraps the app in `ClerkProvider`; client components use `UserButton` and `useUser` from `@clerk/nextjs`.
- Styling: Tailwind is wired via `postcss.config.mjs` and `src/app/globals.css` (importing `tailwindcss`).
- TypeScript: `tsconfig.json` enforces `strict: true` and maps `@/*` to `./src/*`.

Critical integration points
- Groq usage: `src/app/api/generate/route.ts` — server route calls `groq-sdk` chat completions (model: "llama-3.1-8b-instant") with a system prompt. Env var: `GROQ_API_KEY`.
- X (Twitter) posting: `src/app/api/post-to-x/route.ts` — uses `twitter-api-v2`, posts threads line-by-line, replies are chained. Env vars: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, optional `TWITTER_USERNAME` for return URL.
- Assets: `public/` holds SVGs used across the UI (`public/next.svg`, `public/vercel.svg`, etc.).

Common code patterns to follow
- Client vs Server components: client components include `"use client"` at top (e.g., `src/app/dashboard/page.tsx`). Keep server-only logic out of client components.
- API routes: validate inputs with `zod` (`schema.parse(body)`), use `NextRequest` and return `Response.json(...)` for consistent responses.
- Posting threads: `post-to-x` splits content on newlines, trims, and posts each line; when chaining replies it passes `reply: { in_reply_to_tweet_id }` to `client.v2.tweet`.

Environment & secrets (set before running)
- Frontend services expect at least: `GROQ_API_KEY` and the Twitter credentials listed above.
- Clerk requires configuration (see Clerk docs) — `src/app/layout.tsx` assumes Clerk is configured in environment.

Where to look first (high value files)
- `src/app/api/generate/route.ts` — content generation flow.
- `src/app/api/post-to-x/route.ts` — thread-posting flow and Twitter integration.
- `src/app/dashboard/page.tsx` — client UI that calls the two routes.
- `src/app/layout.tsx` and `src/app/globals.css` — auth wrapper and styling.
- `infra/docker-compose.yml` and `backend/README.md` — Redis and backend worker instructions.

Debugging tips
- Reproduce frontend issues with `pnpm dev` and check server route logs in the terminal where Next is running.
- For X posting problems, add console logs in `src/app/api/post-to-x/route.ts` and ensure Twitter keys are valid and app has write permission.
- For backend worker problems, ensure Redis is running (see `infra/docker-compose.yml`) and verify `rq worker` is connected to the correct Redis URL.

Constraints & boundaries
- Do not change authentication strategy — the app uses Clerk; any auth changes must remain compatible.
- Keep Groq model selection in `generate/route.ts` explicit — it encodes product behavior (viral-post prompt + model choice).

Rate-limiting requirement
- All posting logic must implement a simple rate-limiting check (for example, using Redis) before calling external APIs to prevent platform blocks. A future task will migrate posting to a Temporal-based queue for more robust throttling and retries.

If you modify or add server routes
- Follow existing patterns: `zod` for validation, typed `NextRequest`, `Response.json` for replies, and avoid client-side imports in server files.

Questions for maintainers
- Which Clerk environment variables are configured in CI/hosting? If unspecified, assume the standard Next.js/Clerk vars listed below.

Agent Communication Protocol
- Protocol: Frontend server routes (e.g., `src/app/api/generate/route.ts`) must act as a proxy to the FastAPI backend over a simple REST API during development.
- Endpoint: POST `http://localhost:8000/v1/generate/content/` (dev). Payload: JSON { prompt: string, userId?: string, context?: object }.
- Streaming: The Next.js route handler should establish a streaming connection to the FastAPI endpoint (for example, `fetch()` with a ReadableStream or `axios` with `responseType: 'stream'`) to forward incremental tokens/events back to the client UI in real time.
- Future state: The FastAPI endpoint will trigger the LangGraph agent chain and manage Temporal workflows; `src/app/api/generate/route.ts` will become a thin proxy to that endpoint.

Backend Architecture
- The backend is a FastAPI application located in `/backend` with an RQ worker for background tasks.
- Future agent workflows orchestrated by LangGraph and scheduled/reliable via Temporal.io.
- Repo layout expectations: `/backend/services`, `/backend/agents`, `/backend/api` are the canonical places for backend services, agent definitions, and HTTP adapters.
- Startup (dev):
	1. Create and activate Python venv: `python -m venv .venv` then `.venv\Scripts\activate` on Windows.
	2. `pip install -r backend/requirements.txt` (or `requirements.txt` at repo root if present).
	3. Start Redis: `docker-compose -f infra/docker-compose.yml up -d`.
	4. Start FastAPI: `uvicorn backend.main:app --reload --port 8000` (or `uvicorn main:app` if `backend/` is the working dir).
	5. Start worker: `rq worker -u redis://localhost:6379 default`.

Database Layer
- The project uses PostgreSQL + TimescaleDB + `pgvector` for vector embeddings and memory features.
- Store dense embeddings and long-term memory in `pgvector` columns; expect helpers in `/backend/models` and DB schema/migrations in `/infra/database`.
- Migrations: place Alembic or similar migrations under `/backend/models/migrations` or `/infra/database/migrations` following existing repo conventions.

Agentic System Requirements
- All AI agents must follow patterns defined in `docs/AGENTS_OVERVIEW.md` (do not invent new agent types).
- LangGraph is the orchestration layer for chaining agent components.
- Temporal.io will be used for workflow reliability and retries in production.

Context Sync Rules
- All AI models (Grok, ChatGPT, Gemini, Copilot, etc.) must follow the architecture and constraints defined in `docs/DESIGN_DECISIONS.md` and `.ai/context.md`.
- AI coding agents MUST NOT redesign the architecture or introduce new technologies beyond those already listed in `context.md` and `docs/*`.

Clerk environment variables (examples)
- NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY — client-side publishable key used by Clerk UI.
- CLERK_SECRET_KEY — server-side secret key for Clerk server operations.
- Add any other keys present in your Clerk dashboard (session/callback URLs are configured in Clerk dashboard, not in code).

If anything here is outdated or you'd like more examples, tell me which area to expand.


If anything here is outdated or you'd like more examples, tell me which area to expand.
