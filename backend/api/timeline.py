"""Timeline API: history and attribution endpoints.

Phase 8.3: Provides timeline events and export functionality.
"""

from fastapi import APIRouter, Query, Path, Depends, Request
from typing import Optional

from backend.core.auth import get_current_user_id
from backend.core.errors import AppError, ValidationError, RateLimitError, NotFoundError
from backend.core.logging import get_request_id
from backend.core.metrics import ratelimit_block_total, normalize_path
from backend.core.tracing import start_span
from backend.features.timeline.service import timeline_service
from backend.features.timeline.export import export_service, ExportRequest
from backend.features.audit.service import record_audit_event
from backend.features.collaboration.service import get_draft

router = APIRouter(prefix="/v1/timeline", tags=["timeline"])

# Rate limits
TIMELINE_GET_RATE_LIMIT = 60
ATTRIBUTION_GET_RATE_LIMIT = 60


@router.get("/drafts/{draft_id}")
async def get_timeline_endpoint(
    draft_id: str = Path(..., description="Draft ID"),
    limit: int = Query(200, ge=1, le=500, description="Maximum events to return"),
    asc: bool = Query(True, description="Sort ascending (oldest first)"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    request: Request = None,
    user_id: str = Depends(get_current_user_id),
):
    """Get timeline events for a draft.
    
    Returns chronological history of actions on the draft:
    - Draft creation
    - Segments added
    - Ring passes
    - Collaborator additions
    - AI suggestions
    - Format generations
    """
    rid = getattr(request.state, "request_id", None) or get_request_id() if request else get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None) if request else None
    
    with start_span("api.timeline.get", {"draft_id": draft_id, "limit": limit}):
        # Rate limit check
        if limiter:
            allowed = limiter.allow(
                f"timeline:{user_id}",
                per_minute=TIMELINE_GET_RATE_LIMIT,
                burst=10,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path("/v1/timeline/drafts/{draft_id}")})
                raise RateLimitError("Rate limit exceeded for timeline", request_id=rid)
        
        # Verify draft exists and user has access
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found", request_id=rid)
        
        # Check access: owner or collaborator
        if user_id != draft.creator_id and user_id not in draft.collaborators:
            from backend.core.errors import PermissionError
            raise PermissionError("You don't have access to this draft", request_id=rid)
        
        # Fetch timeline
        try:
            result = timeline_service.get_timeline(
                draft_id=draft_id,
                limit=limit,
                cursor=cursor,
                asc_order=asc
            )
        except Exception as exc:
            raise ValidationError(f"Error fetching timeline: {str(exc)}", request_id=rid)
        
        # Record audit event
        record_audit_event(
            action="timeline_get",
            user_id=user_id,
            draft_id=draft_id,
            request_id=rid,
            metadata={"limit": limit, "asc": asc, "cursor": cursor}
        )
        
        return {"data": result.model_dump(), "request_id": rid}


@router.get("/drafts/{draft_id}/attribution")
async def get_attribution_endpoint(
    draft_id: str = Path(..., description="Draft ID"),
    request: Request = None,
    user_id: str = Depends(get_current_user_id),
):
    """Get contributor attribution for a draft.
    
    Returns statistics about who contributed which segments,
    including segment counts and date ranges.
    """
    rid = getattr(request.state, "request_id", None) or get_request_id() if request else get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None) if request else None
    
    with start_span("api.timeline.attribution", {"draft_id": draft_id}):
        # Rate limit check
        if limiter:
            allowed = limiter.allow(
                f"attribution:{user_id}",
                per_minute=ATTRIBUTION_GET_RATE_LIMIT,
                burst=10,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path("/v1/timeline/drafts/{draft_id}/attribution")})
                raise RateLimitError("Rate limit exceeded for attribution", request_id=rid)
        
        # Verify draft exists and user has access
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found", request_id=rid)
        
        # Check access: owner or collaborator
        if user_id != draft.creator_id and user_id not in draft.collaborators:
            from backend.core.errors import PermissionError
            raise PermissionError("You don't have access to this draft", request_id=rid)
        
        # Fetch attribution
        try:
            result = timeline_service.get_attribution(draft_id=draft_id)
        except Exception as exc:
            raise ValidationError(f"Error fetching attribution: {str(exc)}", request_id=rid)
        
        # Record audit event
        record_audit_event(
            action="attribution_get",
            user_id=user_id,
            draft_id=draft_id,
            request_id=rid,
            metadata={}
        )
        
        return {"data": result.model_dump(), "request_id": rid}
