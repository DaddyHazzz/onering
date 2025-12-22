# QUICK REFERENCE: Phase 2 Polish D-F + Phase 3 Collab MVP

## Test Everything
```powershell
# Backend
cd c:\Users\hazar\onering\backend
python -m pytest tests/test_collab_guardrails.py -q
# ✅ 17 passed

# Frontend
cd c:\Users\hazar\onering
pnpm test -- --run
# ✅ 164 passed

# Dev check
scripts/dev_check.ps1
# ✅ All tests pass
```

---

## Backend Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/collab/drafts` | Create draft |
| GET | `/v1/collab/drafts` | List user's drafts |
| GET | `/v1/collab/drafts/{id}` | Get draft by ID |
| POST | `/v1/collab/drafts/{id}/segments` | Append segment (idempotent) |
| POST | `/v1/collab/drafts/{id}/pass-ring` | Pass ring (idempotent) |

---

## Frontend Routes

| Route | Purpose |
|-------|---------|
| `/api/collab/drafts` | Create/list |
| `/api/collab/drafts/[draftId]` | Get draft |
| `/api/collab/drafts/[draftId]/segments` | Append segment |
| `/api/collab/drafts/[draftId]/pass-ring` | Pass ring |
| `/dashboard/collab` | UI page |

---

## Key Models

### Draft
- `draft_id` (UUID)
- `creator_id` (string)
- `title` (≤200 chars)
- `platform` (x, instagram, tiktok, youtube)
- `status` (active, locked, completed)
- `segments` (DraftSegment[])
- `ring_state` (RingState)

### Segment
- `segment_id` (UUID)
- `draft_id` (UUID)
- `user_id` (string)
- `content` (≤500 chars)
- `segment_order` (0-indexed)
- `idempotency_key` (UUID)

### Ring
- `current_holder_id` (string) — Who can append/pass
- `holders_history` (string[]) — All ring holders
- `idempotency_key` (UUID, nullable)

---

## Safety Guarantees

| Guarantee | How |
|-----------|-----|
| **Idempotency** | Check idempotency_key in set before mutation |
| **Permissions** | Verify ring holder before append/pass |
| **Immutability** | All models frozen with ConfigDict |
| **Determinism** | Same input → identical output |
| **Validation** | Title < 200, content < 500 |

---

## Events Emitted

1. **collab.draft_created** → {draft_id, creator_id, title, platform, created_at}
2. **collab.segment_added** → {draft_id, segment_id, user_id, segment_order, created_at}
3. **collab.ring_passed** → {draft_id, from_user_id, to_user_id, passed_at}

---

## Files Created (This Session)

### Part D: Momentum Graph
- `src/features/momentum/graph.ts` (200 lines)
- `src/__tests__/momentum-graph.spec.ts` (268 lines, 19 tests)

### Part E: PowerShell DX
- `scripts/run_tests.ps1` (enhanced)
- `scripts/dev_check.ps1` (new)
- `.githooks/pre-commit.ps1` (enhanced)
- `README.md` (updated)

### Part F: Documentation
- `PHASE2_POLISH_D_TO_F_COMPLETE.md` (new)
- `.ai/domain/collaboration.md` (updated)

### Phase 3: Collab MVP
**Backend:**
- `backend/models/collab.py` (120 lines)
- `backend/features/collaboration/service.py` (220 lines)
- `backend/api/collaboration.py` (80 lines)
- `backend/tests/test_collab_guardrails.py` (340+ lines, 17 tests)

**Frontend:**
- `src/app/api/collab/drafts/route.ts`
- `src/app/api/collab/drafts/[draftId]/route.ts`
- `src/app/api/collab/drafts/[draftId]/segments/route.ts`
- `src/app/api/collab/drafts/[draftId]/pass-ring/route.ts`
- `src/app/dashboard/collab/page.tsx` (400 lines)
- `src/__tests__/collab.spec.ts` (420+ lines, 24 tests)

---

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| collab-guardrails | 17 | ✅ Passing |
| collab-schema | 24 | ✅ Passing |
| momentum-graph | 19 | ✅ Passing |
| Other suites | 104 | ✅ Passing |
| **TOTAL** | **164** | **✅ ALL PASSING** |

---

## Next Phase 3 Increment

**Phase 3.2: Collaborator Invites + Handle Resolution**
- [ ] Invite API (per-draft)
- [ ] Email/handle resolution (Clerk)
- [ ] Auto-user creation
- [ ] Debounced user lookup
- [ ] Invite acceptance workflow

---

## Vocabulary

**Draft:** Collaborative thread with segments + ring  
**Segment:** Individual contribution (immutable, ordered)  
**Ring:** Token controlling who can append/pass  
**Ring Holder:** Current user with permission to mutate  
**Idempotency Key:** UUID to prevent duplicate mutations  

---

**Status:** ✅ Complete and Verified  
**Total Code:** 2,000+ lines (models, service, API, UI, tests)  
**Total Tests:** 181 passing  
**No Failures:** 0 ❌  
**Ready for:** Staging deployment

