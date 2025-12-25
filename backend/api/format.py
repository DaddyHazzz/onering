"""FastAPI routes for format generation (Phase 8.2)."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import get_current_user_id
from backend.core.ratelimit import InMemoryRateLimiter, RateLimitConfig
from backend.core.logging import get_request_id
from backend.features.audit.service import record_audit_event
from backend.core.tracing import start_span
from backend.features.collaboration.service import get_draft
from backend.features.format.templates import Platform
from backend.features.format.validators import FormatRequest, FormatOptions
from backend.features.format.service import format_service, FormatGenerateResponse

router = APIRouter(prefix="/v1/format", tags=["format"])
logger = logging.getLogger(__name__)

# Create rate limiter with 20 requests per minute (2 per 6 seconds), burst of 10
_config = RateLimitConfig(enabled=True, per_minute_default=20, burst_default=10)
rate_limiter = InMemoryRateLimiter(_config)

@router.post("/generate", response_model=FormatGenerateResponse)
async def format_generate(
    request: FormatRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate platform-specific formatted outputs from a draft.
    
    Rate limit: 20/min with burst of 10
    
    Request:
    {
        "draft_id": "uuid",
        "platforms": ["x", "youtube", "instagram", "blog"],  # optional, null = all
        "options": {
            "tone": "professional",
            "include_hashtags": true,
            "include_cta": true,
            "hashtag_count": 5,
            "hashtag_suggestions": ["growthhacking", "startup"],
            "cta_text": "Join my community",
            "cta_suggestions": []
        }
    }
    
    Response:
    {
        "draft_id": "uuid",
        "outputs": {
            "x": {
                "platform": "x",
                "blocks": [...],
                "plain_text": "...",
                "character_count": 280,
                "block_count": 1,
                "warnings": []
            },
            "youtube": {...}
        }
    }
    """
    user_id = get_current_user_id
    request_id = get_request_id()
    
    logger.debug(f"[format/generate] user_id={user_id}, draft_id={request.draft_id}, request_id={request_id}")
    
    try:
        # Rate limit check
        allowed = rate_limiter.allow(
            f"format:{user_id}",
            per_minute=20,
            burst=10,
        )
        if not allowed:
            logger.warning(f"[format/generate] rate_limit_exceeded, user_id={user_id}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after 1 minute.",
            )
        
        with start_span("format_generate", {"draft_id": request.draft_id, "user_id": user_id}):
            # Fetch draft
            draft = get_draft(request.draft_id)
            if not draft:
                logger.error(f"[format/generate] draft_not_found, draft_id={request.draft_id}")
                raise HTTPException(status_code=404, detail="Draft not found")
            
            # Check access (user must be collaborator or owner)
            is_owner = draft.owner_id == user_id
            is_collab = any(c["user_id"] == user_id for c in draft.collaborators)
            if not (is_owner or is_collab):
                logger.warning(f"[format/generate] access_denied, user_id={user_id}, draft_id={request.draft_id}")
                raise HTTPException(status_code=403, detail="Not a collaborator on this draft")
            
            # Convert platforms if provided
            platforms = None
            if request.platforms:
                try:
                    platforms = [Platform(p) for p in request.platforms]
                except ValueError as e:
                    logger.error(f"[format/generate] invalid_platform, error={e}")
                    raise HTTPException(status_code=400, detail=f"Invalid platform: {e}")
            
            # Generate formatted outputs
            response = format_service.format_draft(draft, platforms, request.options)
            
            # Audit log
            record_audit_event(
                action="format_generate",
                user_id=user_id,
                metadata={
                    "draft_id": request.draft_id,
                    "platform_count": len(response.outputs),
                    "request_id": request_id
                }
            )
            
            logger.info(f"[format/generate] success, draft_id={request.draft_id}, platforms={len(response.outputs)}")
            return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[format/generate] error, draft_id={request.draft_id}, error={e}")
        raise HTTPException(status_code=500, detail="Format generation failed")
