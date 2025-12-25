# OneRing System Architecture (Moved)

Note: Canonical architecture lives at .ai/ARCHITECTURE.md. This legacy file may be stale.

## Overview
OneRing is an agentic AI content platform built as a distributed multi-service system:
- **Frontend**: Next.js 15, Tailwind, shadcn, Clerk Auth
- **Backend**: FastAPI, LangGraph agent pipeline, Redis RQ workers
- **DB Layer**: PostgreSQL + TimescaleDB + pgvector
- **Infra**: Docker, Redis, optional Temporal.io
- **Agents**: Strategy → Research → Writer → Visual → Video → QA → Posting → Analytics

## High-Level Flow
1. User triggers content generation.
2. Frontend calls backend `/api/posts/generate`.
3. Backend queues LangGraph workflow via Redis → Worker.
4. Worker executes multi-agent chain.
5. Posting Agent publishes to platforms.
6. Analytics Agent stores metrics in Timescale.
7. Frontend dashboard displays results.
