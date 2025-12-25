"""Export API: draft export with attribution.

Phase 8.3: Export drafts as markdown or JSON with optional credits.
"""

from fastapi import APIRouter, Path, Depends, Request

from backend.core.auth import get_current_user_id
from backend.core.errors import ValidationError, RateLimitError, NotFoundError
from backend.core.logging import get_request_id
from backend.core.metrics import ratelimit_block_total, normalize_path
from backend.core.tracing import start_span
from backend.features.timeline.export import export_service, ExportRequest
from backend.features.audit.service import record_audit_event
from backend.features.collaboration.service import get_draft

router = APIRouter(prefix="/v1/export", tags=["export"])

# Rate limits
EXPORT_DRAFT_RATE_LIMIT = 20


@router.post("/drafts/{draft_id}")
async def export_draft_endpoint(
    draft_id: str = Path(..., description="Draft ID"),
    body: ExportRequest = ExportRequest(format="markdown", include_credits=True),
    request: Request = None,
    user_id: str = Depends(get_current_user_id),
):
    """Export a draft in markdown or JSON format.
    
    Optionally includes a credits section showing contributor statistics.
    
    Request body:
    - format: "markdown" or "json"
    - include_credits: true/false (default true)
    
    Response includes:
    - filename: suggested download filename
    - content_type: MIME type
    - content: full export content
    """
    rid = getattr(request.state, "request_id", None) or get_request_id() if request else get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None) if request else None
    
    with start_span("api.export.draft", {"draft_id": draft_id, "format": body.format}):
        # Rate limit check
        if limiter:
            allowed = limiter.allow(
                f"export:{user_id}",
                per_minute=EXPORT_DRAFT_RATE_LIMIT,
                burst=5,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path("/v1/export/drafts/{draft_id}")})
                raise RateLimitError("Rate limit exceeded for export", request_id=rid)
        
        # Verify draft exists and user has access
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found", request_id=rid)
        
        # Check access: owner or collaborator
        if user_id != draft.creator_id and user_id not in draft.collaborators:
            from backend.core.errors import PermissionError
            raise PermissionError("You don't have access to this draft", request_id=rid)
        
        # Generate export
        try:
            result = export_service.export_draft(
                draft_id=draft_id,
                export_format=body.format,
                include_credits=body.include_credits
            )
        except NotFoundError:
            raise
        except Exception as exc:
            raise ValidationError(f"Error exporting draft: {str(exc)}", request_id=rid)
        
        # Record audit event
        record_audit_event(
            action="export_draft",
            user_id=user_id,
            draft_id=draft_id,
            request_id=rid,
            metadata={"format": body.format, "include_credits": body.include_credits}
        )
        
        return {"data": result.model_dump(), "request_id": rid}
