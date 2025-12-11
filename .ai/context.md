# ONERING PROJECT CONTEXT (DO NOT MODIFY ARCHITECTURE)

## 1. CORE IDENTITY
- **Name:** OneRing
- **Concept:** Agentic AI Content Management System + Crypto Token ($RING) + Future Hardware.
- **Narrative:** "Fat Felon Elon", "Revenge Arc", Chaotic/Viral/High-Energy.
- **Goal:** Automate content creation (Strategy -> Research -> Write -> Post) via an AI Agent Swarm.

## 2. TECH STACK (STRICT)
- **Frontend:** Next.js 15 (App Router), Tailwind CSS, shadcn/ui, Lucide React.
- **Backend:** FastAPI (Python), LangGraph (Agent Orchestration).
- **Database:** PostgreSQL + TimescaleDB + pgvector (for memory).
- **Auth:** Clerk (Next.js middleware protection).
- **Infrastructure:** Temporal.io (Workflow reliability), Redis (Caching).

## 3. CURRENT STATUS (LIVE)
- [x] Login System (Clerk) functional.
- [x] Dashboard UI (Shell) functional.
- [x] "Generate Viral Thread" button (Mocked/Basic).
- [x] X (Twitter) OAuth 1.0a connection established.
- [!] **FOCUS:** Connecting the frontend "Generate" button to the FastAPI backend stream.

## 4. DIRECTIVES FOR AI
1. **No Hallucinations:** Do not invent new libraries. Use what is listed above.
2. **File Structure:** - Frontend: `/app`, `/components`, `/lib`
   - Backend: `/api`, `/agents`, `/workflows`
3. **Tone:** Code should be clean, commented, and production-ready. Comments can be slightly humorous/edgy.