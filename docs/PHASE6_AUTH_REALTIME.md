# Phase 6 — Auth, Real-Time Collab, and Production Hardening

**Status**: STARTING (Dec 23, 2025)  
**Current Tests**: Backend 535/535 ✅ | Frontend 299/299 ✅  
**Current Auth**: X-User-Id header + localStorage (TEMPORARY)

---

## Phase 6 Overview

Phase 6 is a **system transition phase** moving from working prototype → production platform.

### Three Major Workstreams

1. **Phase 6.1 — Real Auth (Clerk Integration)**
   - Replace fake user identity with real users
   - Add Clerk frontend + backend validation
   - Support X-User-Id during transition (no breaking changes)

2. **Phase 6.2 — Real-Time Collab (WebSockets)**
   - Ring passes propagate instantly
   - Segment appends appear live
   - Optimistic UI with conflict safety

3. **Phase 6.3+ — Production Hardening**
   - Rate limiting, audit logging, security
   - Environments (local, staging, prod)
   - Deployment infrastructure

---

## PHASE 6.1 — REAL AUTH (CLERK INTEGRATION)

### Goal
Replace fake auth with real Clerk users — without breaking anything.

### Current State
```
Frontend:
  - localStorage["test_user_id"] → X-User-Id header
  - No real user identity

Backend:
  - get_current_user_id() reads X-User-Id header
  - No user persistence (no users table)
  - All collaborator IDs are just strings

Collab Endpoints:
  - POST /v1/collab/drafts
  - GET /v1/collab/drafts
  - GET /v1/collab/drafts/{id}
  - POST /v1/collab/drafts/{id}/segments
  - POST /v1/collab/drafts/{id}/pass-ring
  - POST /v1/collab/drafts/{id}/collaborators
  ↑ ALL depend on X-User-Id header
```

### Target State (Phase 6.1 END)
```
Frontend:
  - useUser() from @clerk/nextjs
  - X-User-Id header → Authorization Bearer {JWT} header
  - Graceful fallback to read-only if unauthenticated

Backend:
  - get_current_user_id() validates Clerk JWT
  - Falls back to X-User-Id for backward compatibility
  - users table persists Clerk users
  - Upsert on first auth request
  - All draft/segment queries now reference real user IDs

Auth Flow:
  1. User signs in with Clerk
  2. Clerk JWT in Authorization header
  3. Backend validates JWT
  4. Upsert user into DB
  5. Return user_id from DB
```

### Implementation Steps

#### STEP 1: Clerk Frontend Setup
**Files to modify**: `src/app/layout.tsx`, `.env.local`

1. Install @clerk/nextjs
2. Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY in .env.local
3. Wrap <ClerkProvider> in layout.tsx
4. Replace localStorage auth with useUser()

#### STEP 2: Update collabApi to use Clerk
**File to modify**: `src/lib/collabApi.ts`

1. Add new function: `getClerkJWT()`
2. Update `apiFetch()` to send Authorization header instead of X-User-Id
3. Fallback to X-User-Id if no Clerk user (for tests)

#### STEP 3: Clerk Backend Integration
**Files to modify**: `backend/core/auth.py`, `backend/core/config.py`

1. Add PyJWT + cryptography to requirements.txt
2. Implement `verify_clerk_jwt()` function
3. Update `get_current_user_id()`:
   ```python
   async def get_current_user_id(request: Request):
       # Try Clerk JWT first
       auth_header = request.headers.get("Authorization", "")
       if auth_header.startswith("Bearer "):
           jwt_token = auth_header[7:]
           try:
               user_id = verify_clerk_jwt(jwt_token)
               return user_id
           except:
               pass  # Fall through to X-User-Id
       
       # Fall back to X-User-Id for backward compatibility
       x_user_id = request.headers.get("X-User-Id")
       if x_user_id:
           return x_user_id
       
       # No auth found
       raise HTTPException(status_code=401, detail="Unauthorized")
   ```

#### STEP 4: Users Table
**Files to create**: `backend/models/users.py` (if not exists)
**Files to modify**: `backend/core/database.py`

Create users table with:
- id (PK): Clerk user ID
- email
- username
- created_at
- updated_at
- metadata (JSON)

#### STEP 5: User Upsert on Auth
**Files to create**: `backend/features/users/service.py`
**Files to modify**: `backend/core/auth.py`

After validating JWT:
```python
async def ensure_user_exists(clerk_user_id: str, email: str):
    # Upsert Clerk user into DB
    user = get_or_create_user(
        id=clerk_user_id,
        email=email
    )
    return user
```

#### STEP 6: Update Tests
**Files to modify**: 
- `backend/tests/test_collab_*.py`
- Frontend tests using mock Clerk

New test helpers:
- `create_test_jwt(user_id)` — Generate mock JWT for tests
- `mock_clerk_user(user_id, email)` — Mock frontend Clerk user

#### STEP 7: Database Migration
**Files to create**: `backend/migrations/001_create_users_table.py` (if using Alembic)

OR: Just call `create_all_tables()` in main.py (current approach)

---

## Exit Criteria for Phase 6.1

- [ ] Clerk SDK installed (frontend + backend)
- [ ] Frontend: useUser() replaces localStorage
- [ ] Backend: JWT validation + X-User-Id fallback
- [ ] Users table created and upserted
- [ ] All 535 backend tests still green
- [ ] All 299 frontend tests still green
- [ ] No breaking API changes
- [ ] Graceful read-only fallback if auth fails
- [ ] Docs updated: AUTH.md created

---

## PHASE 6.2 — REAL-TIME COLLAB (WEBSOCKETS)

### Goal
When ONE user edits/passes ring → ALL viewers update instantly.

### Architecture

**Backend**:
```python
@app.websocket("/v1/ws/drafts/{draft_id}")
async def websocket_endpoint(websocket: WebSocket, draft_id: str):
    # Validate user via Clerk JWT
    # Join draft_id room
    # Broadcast events:
    # - segment_added
    # - ring_passed
    # - collaborator_added
    # - draft_updated
```

**Frontend**:
```typescript
const useDraftSocket = (draftId: string) => {
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/v1/ws/drafts/${draftId}`);
    ws.onmessage = (event) => {
      // Update local state based on event type
    };
    ws.onerror = () => {
      // Fallback to polling
    };
  }, [draftId]);
};
```

---

## PHASE 6.3+ — OPTIMISTIC UI + HARDENING

### Optimistic Append
- Show segment immediately
- Roll back if backend rejects

### Optimistic Ring Pass
- Disable editor instantly
- Revert if rejected

### Conflict Handling
- If two users append simultaneously:
  - Both show as pending
  - Backend processes first
  - UI reconciles to truth

---

## Timeline Estimate

- Phase 6.1 (Auth): 4-6 hours
- Phase 6.2 (WebSockets): 6-8 hours
- Phase 6.3+ (Hardening): 4-6 hours
- Testing + docs: 2-3 hours

**Total**: ~20 hours

---

## DO NOT FORGET

❌ DO NOT break existing API contracts
❌ DO NOT remove X-User-Id support
❌ DO NOT introduce WebSocket without fallback
❌ DO NOT let tests fail mid-phase
❌ DO NOT skip authentication on any collab endpoint

✅ DO keep X-User-Id working during transition
✅ DO support both auth methods at once
✅ DO test every change immediately
✅ DO update docs as you go
✅ DO gracefully degrade to read-only if auth fails

---

## Success Metrics (End of Phase 6)

- [ ] Real users exist in database
- [ ] Auth required on all collab endpoints
- [ ] Real-time updates work (WebSockets OR polling fallback)
- [ ] Ring passes propagate instantly
- [ ] Optimistic UI works without conflicts
- [ ] 535+ backend tests passing
- [ ] 299+ frontend tests passing
- [ ] App deploys cleanly to staging
- [ ] Zero auth bypass vulnerabilities
- [ ] Docs complete (AUTH.md, REALTIME.md, DEPLOYMENT.md)

---

## Begin Phase 6.1 Now

1. ✅ PART 0: Read auth baseline (DONE)
2. ⏳ PART 1: Add Clerk to frontend (NEXT)
3. ⏳ PART 2: Update backend auth bridge
4. ⏳ PART 3-6: Complete Phase 6.1
5. ⏳ Test gate + commit
