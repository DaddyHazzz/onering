"""
backend/api/collaboration.py
Collaboration API: create drafts, append segments, pass ring.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional
from backend.features.collaboration.service import (
    create_draft,
    get_draft,
    list_drafts,
    append_segment,
    pass_ring,
    generate_share_card,
)
from backend.models.collab import (
    CollabDraftRequest,
    SegmentAppendRequest,
    RingPassRequest,
)

router = APIRouter(prefix="/v1/collab", tags=["collaboration"])


@router.post("/drafts")
async def create_draft_endpoint(user_id: str, request: CollabDraftRequest):
    """Create new collaboration draft"""
    try:
        draft = create_draft(user_id, request)
        return {"data": draft.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drafts")
async def list_drafts_endpoint(user_id: str):
    """List drafts involving user"""
    try:
        drafts = list_drafts(user_id)
        return {
            "data": [d.model_dump() for d in drafts],
            "count": len(drafts),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drafts/{draft_id}")
async def get_draft_endpoint(
    draft_id: str,
    now: Optional[str] = Query(None, description="Fixed timestamp for deterministic testing (ISO format)")
):
    """Fetch draft by ID with optional metrics (Phase 3.3a)"""
    # Parse optional now parameter
    now_dt = None
    if now:
        try:
            now_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ISO timestamp format for 'now' parameter")
    
    draft = get_draft(draft_id, compute_metrics_flag=True, now=now_dt)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
    return {"data": draft.model_dump()}


@router.post("/drafts/{draft_id}/segments")
async def append_segment_endpoint(
    draft_id: str, user_id: str, request: SegmentAppendRequest
):
    """Append segment to draft (idempotent)"""
    try:
        draft = append_segment(draft_id, user_id, request)
        return {"data": draft.model_dump()}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/pass-ring")
async def pass_ring_endpoint(draft_id: str, user_id: str, request: RingPassRequest):
    """Pass ring to another user (idempotent)"""
    try:
        draft = pass_ring(draft_id, user_id, request)
        return {"data": draft.model_dump()}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/drafts/{draft_id}/share-card")
async def get_share_card_endpoint(
    draft_id: str,
    viewer_id: Optional[str] = Query(None, description="User viewing the card"),
    style: str = Query("default", description="Card style"),
    now: Optional[str] = Query(None, description="ISO timestamp for deterministic testing"),
):
    """Get share card for collaborative draft (Phase 3.3c)"""
    try:
        # Parse now param if provided (for deterministic testing)
        now_dt = None
        if now:
            now_dt = datetime.fromisoformat(now)
        
        share_card = generate_share_card(draft_id, now_dt)
        return {
            "success": True,
            "data": share_card,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))