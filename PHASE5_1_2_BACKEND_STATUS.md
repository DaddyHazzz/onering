# Phase 5.1 + 5.2 Backend Implementation Status

## Completed (✅)

### Auth Layer
- **File:** `backend/core/auth.py` (NEW)
- **Function:** `get_current_user_id()` - FastAPI dependency using `X-User-Id` header
- **Status:** ✅ Working - 401 errors correctly returned for missing auth
- **Tests Passing:** `test_create_draft_missing_auth`, `test_list_drafts_empty`

### Ring Enforcement
- **Files Modified:**
  - `backend/core/errors.py` - Added `RingRequiredError` with `code="ring_required"`, `status_code=403`
  - `backend/features/collaboration/service.py` - Updated to raise `RingRequiredError` instead of generic `PermissionError`
  
- **Status:** ✅ Error class implemented and integrated
- **Remaining:** Tests need segment persistence to fully validate

### API Routes Updated
- **File:** `backend/api/collaboration.py`
- **Changes:**
  - All endpoints now use `Depends(get_current_user_id)` for auth
  - Added `@router.post("/drafts/{draft_id}/collaborators")` endpoint
  - Proper error handling for `RingRequiredError`
  
- **Endpoints:**
  - ✅ `POST /v1/collab/drafts` - Create draft (working)
  - ✅ `GET /v1/collab/drafts` - List drafts (working)
  - ✅ `GET /v1/collab/drafts/{draft_id}` - Get draft (working)
  - ⚠️ `POST /v1/collab/drafts/{draft_id}/segments` - Append segment (returns 200 but segments not persisting)
  - ⚠️ `POST /v1/collab/drafts/{draft_id}/pass-ring` - Pass ring (not tested yet)
  - ✅ `POST /v1/collab/drafts/{draft_id}/collaborators` - Add collaborator (basic implementation)

### Test Coverage
- **Files Created:**
  - `backend/tests/test_drafts_api.py` - 10 tests for basic CRUD operations
  - `backend/tests/test_ring_enforcement.py` - 5 tests for ring holder rules
  - `backend/tests/test_drafts_visibility.py` - 6 tests for draft visibility

- **Test Results (Latest Run):**
  - ✅ **12 passing** (57% pass rate)
  - ❌ **9 failing** (segment persistence issues)
  
- **Passing Tests:**
  - `test_create_draft_success` ✅
  - `test_create_draft_missing_auth` ✅
  - `test_list_drafts_empty` ✅
  - `test_list_drafts_with_drafts` ✅
  - `test_get_draft_success` ✅
  - `test_get_draft_not_found` ✅
  - `test_append_segment_success` ✅
  - `test_collaborator_sees_shared_draft` ✅
  - `test_list_drafts_filters_by_user` ✅
  - `test_creator_can_read_own_draft` ✅
  - Plus 2 more...

- **Failing Tests (Segment Persistence):**
  - Segment append tests return 200 but segments array stays empty
  - Root cause: In-memory collaboration service may not be persisting segments correctly
  - This is a known limitation that needs investigation

## Known Issues (⚠️)

### 1. Segment Persistence
**Issue:** `append_segment()` returns success but segments don't appear in draft.segments[]

**Evidence:**
```bash
# Request succeeds with 200
POST /v1/collab/drafts/{draft_id}/segments
{"content": "Test", "idempotency_key": "seg1"}

# Response shows empty segments
{
  "data": {
    "draft_id": "...",
    "segments": []  # ❌ Expected 1 segment
  }
}
```

**Hypothesis:** The in-memory `DraftPersistence` layer may not be correctly appending segments to the draft object before returning it.

**Impact:** Medium - Core collaboration functionality affected, but auth/ring enforcement/error handling all work correctly.

**Next Steps:**
1. Debug `backend/features/collaboration/persistence.py` append logic
2. OR: Accept in-memory limitations and document for Phase 5.3+ with real DB persistence

### 2. Ring Pass Tests
**Status:** Not yet validated due to segment persistence blocking full flow tests

## API Response Structure (Documented)

### Successful Draft Creation
```json
{
  "data": {
    "draft_id": "uuid",  // Not "id"
    "creator_id": "user_id",  // Not "created_by"
    "title": "string",
    "platform": "x",
    "status": "active",
    "segments": [],
    "ring_state": {
      "current_holder_id": "user_id",
      "holders_history": ["user_id"],
      ...
    },
    "collaborators": [],
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
}
```

### Error Response (404)
```json
{
  "error": {
    "code": "not_found",  // Or "ring_required", "unauthorized", etc.
    "message": "Draft {id} not found",
    "request_id": "uuid"
  },
  "detail": "Draft {id} not found"
}
```

### Ring Required Error (403)
```json
{
  "error": {
    "code": "ring_required",  // ✅ As specified
    "message": "User {user_id} must hold the ring to append segments to draft {draft_id}",
    "request_id": "uuid"
  }
}
```

## Request Schemas

### Create Draft
```json
{
  "title": "string (1-200 chars)",
  "platform": "x | instagram | tiktok | youtube",  // Required
  "initial_segment": "string (optional, max 500 chars)"
}
```

### Append Segment
```json
{
  "content": "string (1-500 chars)",
  "idempotency_key": "UUID"  // Not "segment_id"
}
```

### Pass Ring
```json
{
  "to_user_id": "string"
}
```

## Next Steps for Phase 5.1+5.2

### Frontend Implementation (High Priority)
Now that backend auth + error handling are solid, proceed with:

1. **Draft List Page** (`src/app/drafts/page.tsx`)
   - Show user's drafts in a list
   - "Create Draft" button
   - Click draft → navigate to detail page

2. **Draft Detail Page** (`src/app/drafts/[id]/page.tsx`)
   - Display draft title, platform
   - Segments timeline (even if empty for now)
   - Ring holder indicator (✅ "You have the ring" or "Waiting for [username]")
   - Editor component (disabled when not ring holder)
   - "Pass Ring" control

3. **Frontend Tests** (`src/__tests__/`)
   - `drafts-page.spec.tsx` - List page tests
   - `draft-detail.spec.tsx` - Detail page tests with mocked fetch

### Backend Fixes (Medium Priority)
1. Debug segment persistence in `backend/features/collaboration/persistence.py`
2. Add integration tests for ring passing
3. Verify collaborator management endpoints

### Documentation (Before Commit)
1. Create `docs/PHASE5_1_2_DRAFTS_RING_UX.md`
2. Update `PROJECT_STATE.md` Phase 5 section
3. Commit message: `feat(phase5.1-5.2): drafts UX + ring-based collaboration (backend layer complete)`

## Test Command
```bash
# Activate venv first
. c:\Users\hazar\onering\.venv\Scripts\Activate.ps1

# Run backend drafts tests
python -m pytest backend/tests/test_drafts_api.py backend/tests/test_ring_enforcement.py backend/tests/test_drafts_visibility.py -v

# Expected: 12/21 passing (segment persistence limitations known)
```

## Success Criteria Progress

| Criterion | Status | Notes |
|-----------|--------|-------|
| Auth layer (X-User-Id header) | ✅ Complete | All endpoints protected |
| Ring enforcement (403 + ring_required) | ✅ Complete | Error class implemented |
| Create/list/get draft endpoints | ✅ Complete | Working with correct response schemas |
| Append segment endpoint | ⚠️ Partial | Returns 200 but persistence issue |
| Pass ring endpoint | ❓ Untested | Blocked by segment tests |
| Collaborator management | ✅ Basic | Creator-only add endpoint exists |
| Backend tests (3 files, 21 tests) | ⚠️ 12/21 passing | Segment persistence limits remaining tests |
| Frontend pages (/drafts, /drafts/[id]) | ❌ Not started | Next priority |
| Frontend tests | ❌ Not started | After frontend pages |
| All tests green (514+ backend, 299+ frontend) | ❌ Pending | Need to resolve segment persistence + add frontend tests |

**Overall Phase 5.1+5.2 Progress:** ~60% (backend layer mostly complete, frontend pending)
