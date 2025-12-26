Source: ../ARCHITECTURE.md

Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# Architecture

## System Diagram

```
┌─────────────────────────────┐
│   Frontend (Next.js 16)     │
│   - App Router              │
│   - Tailwind CSS            │
│   - Clerk Auth              │
│   - Vitest + RTL            │
└──────────────┬──────────────┘
               │ REST + WebSocket
               │ /api/*, /ws/*
               ▼
┌──────────────────────────────────┐
│  Backend (FastAPI + LangGraph)   │
│  - Authentication (Clerk JWT)    │
│  - REST routes (/v1/*)           │
│  - WebSocket (presence, updates) │
│  - LangGraph agents              │
│  - RQ worker queues              │
└──────────────┬───────────────────┘
               │
      ┌────────┼────────┬──────────────┐
      ▼        ▼        ▼              ▼
   Groq    PostgreSQL  Redis       S3/Files
   (LLM)   (primary)   (cache,     (media,
            + pgvector queues)      exports)
```

## Backend Architecture

### Entry Point: FastAPI Main App
**File:** `backend/main.py`
- Mounts routes from `backend/api/`
- Configures Clerk middleware
- Runs on port 8000
- Supports both HTTP and WebSocket

### Authentication Layer
**Clerk + JWT:**
- User signs in via frontend
- Clerk issues JWT token
- Backend verifies via `from_clerk_header` middleware
- User metadata stored in Clerk publicMetadata (RING balance, verified status, etc.)

### API Routes

**Core collaboration routes** (`backend/api/collab/`):
- `POST /api/collab/drafts` — Create draft
- `GET /api/collab/drafts/{draft_id}` — Get draft
- `POST /api/collab/drafts/{draft_id}/invite` — Invite collaborator
- `POST /api/collab/drafts/{draft_id}/ring/pass` — Pass ring to user
- `POST /api/collab/drafts/{draft_id}/segments` — Add segment to draft

**Analytics routes** (`backend/api/analytics/`):
- `GET /api/collab/drafts/{draft_id}/analytics` — Get draft analytics
- `GET /v1/analytics/leaderboard` — Get user rankings (optional `now` param for testing)

**Insights routes** (`backend/api/insights/`):
- `GET /api/insights/drafts/{draft_id}` — Get draft insights, recommendations, alerts

**Other routes:**
- Authentication, user profile, staking, referrals, etc.

### Data Models

**Core models** (`backend/models/collab.py`):
- `CollabDraft` — Frozen Pydantic model representing a draft
  - `id`, `creator_id`, `title`, `platform`, `created_at`
  - `ring_state` (RingState) — who holds ring, pass history, hold time
  - `segments` — list of text segments with contributor info
  - `analytics_summary` — aggregated stats (views, unique_contributors, etc.)

- `RingState` — current ring holder info
  - `current_holder_id`, `holders_history`, `passed_at` (when holder started holding)

- `DraftAnalytics` — event-driven analytics (frozen model)
  - `views`, `contributions`, `ring_passes`, `time_to_publish`, etc.
  - Computed deterministically from event stream

### Agents (LangGraph)

**File:** `backend/agents/langgraph/graph.py`

**Workflow:**
1. **Writer Agent** — Generate initial content (or next turn)
2. **Strategy Agent** — Review content + suggest refinements
3. **Posting Agent** — Format for platform + post to X/IG/TikTok
4. **Analytics Agent** — Log event + compute metrics

**Streaming:**
- Backend supports Server-Sent Events (SSE)
- Groq tokens stream character-by-character to frontend

### Services

**Collaboration Service** (`backend/features/collaboration/service.py`):
- `create_draft()` — Create new draft with creator as ring holder
- `pass_ring()` — Pass ring to another collaborator
- `add_segment()` — Append text segment to draft

**Insights Service** (`backend/features/insights/service.py`):
- `compute_draft_insights()` — Compute insights, recommendations, alerts
- Uses helper `_current_holder_hold_seconds()` to compute hold duration
- Triggers alerts based on thresholds (LONG_RING_HOLD > 24h, NO_ACTIVITY > 72h, etc.)

**Analytics Service** (`backend/features/analytics/service.py`):
- `reduce_draft_analytics()` — Fold events into aggregated metrics
- `reduce_leaderboard()` — Compute user rankings

### Persistence

**PostgreSQL:**
- All draft, user, segment, analytics data
- pgvector column for user profile embeddings (for AI personalization)

**Redis:**
- Session cache
- RQ job queue
- Rate-limiting counters

## Frontend Architecture

### App Router (Next.js 16)

**Layout** (`src/app/layout.tsx`):
- Clerk provider setup
- Global styles (Tailwind)
- Navigation layout

**Pages:**
- `/` — Landing (redirects to `/dashboard` if signed in)
- `/dashboard` — Main collaborative editor + insights view
- `/monitoring` — Real-time system health dashboard
- `/api/*` — Route handlers (proxy to backend, Stripe webhook handlers, etc.)

### Components

**Key components:**
- `CollabEditor.tsx` — Draft editor, ring holder indicator, segment list
- `InsightsPanel.tsx` — Shows insights, recommendations, alerts
- `AnalyticsPanel.tsx` — Leaderboard, contribution chart, metrics
- `DraftAnalyticsModal.tsx` — Per-draft analytics breakdown
- `AISuggestionsPanel.tsx` — Ring holder suggestions for next turn

### Testing

**Vitest + React Testing Library:**
- 388 tests total (100% green)
- Test files in `src/__tests__/`
- No skipped tests
- Uses role-based selectors (accessible + stable)

**Key test patterns:**
```typescript
// Mock API
vi.mock("@/lib/collabApi");

// Render with Clerk user
render(<Component draftId={mockDraftId} />);

// Wait for async loads
await waitFor(() => expect(screen.getByText(/pattern/)).toBeInTheDocument());

// Verify interactions
fireEvent.click(screen.getByRole("button", { name: /action/i }));
expect(mockFn).toHaveBeenCalledWith(expected);
```

## Deployment Targets

### Local Development
```bash
docker-compose -f infra/docker-compose.yml up -d  # Redis + Postgres
uvicorn backend.main:app --reload --port 8000    # Backend
pnpm dev                                           # Frontend
```

### Docker Deployment
- `infra/docker/Dockerfile` for backend
- `infra/docker/Dockerfile.frontend` for Next.js
- Both assume Redis + Postgres available

### Kubernetes (K8s)
- Manifests in `infra/k8s/`
- Deployment, Service, ConfigMap, Secret templates
- Ready for scaling

## Key Design Decisions

See DECISIONS.md for:
- Why Clerk (not Auth0)?
- Why PostgreSQL + pgvector (not MongoDB)?
- Why RQ (not Bull/Temporal)?
- Why LangGraph (not Airflow)?
- Why Groq (not OpenAI)?

## Testing Strategy

See TESTING.md for:
- Fast gates vs. full gates
- How to run single test file
- How to debug
- Windows PowerShell commands

## Data Flow Examples

### Creating a Draft
```
Frontend: POST /api/collab/drafts
  ↓
Backend: create_draft()
  - Store in PostgreSQL
  - Initialize ring_state with creator
  - Emit DraftCreated event
  ↓
Insights: compute_draft_insights()
  - Check thresholds
  - Generate recommendations
  ↓
Frontend: GET /api/insights/drafts/{id}
  - Receives insights + alerts
```

### Passing Ring
```
Frontend: POST /api/collab/drafts/{id}/ring/pass
  ↓
Backend: pass_ring(target_user_id)
  - Update ring_state.current_holder_id
  - Add to ring_state.holders_history
  - Emit RingPassed event
  - Update ring_state.passed_at = now
  ↓
Analytics: reduce_draft_analytics()
  - Recompute passed count, hold durations
  ↓
Insights: _current_holder_hold_seconds()
  - Check new holder's time (reset to 0)
  - Generate new recommendations for new holder
```

### AI Content Generation
```
Frontend: POST /api/generate
  ↓
Backend: stream Groq tokens
  - Invoke Writer Agent
  - Stream response character-by-character (SSE)
  ↓
Frontend: display as text streams in
  - "Groq is cooking..." → disappears
  - Content appears token by token
```
