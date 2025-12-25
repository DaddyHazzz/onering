"""AI suggestion API (Phase 8.1).

Provides ring-aware, additive-only AI suggestions for drafts.
"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, field_validator

from backend.core.auth import get_current_user_id
from backend.core.errors import AppError, ValidationError, RateLimitError
from backend.core.logging import get_request_id
from backend.core.metrics import ratelimit_block_total, normalize_path
from backend.core.tracing import start_span
from backend.features.ai.service import suggest_ai_response
from backend.features.audit.service import record_audit_event

router = APIRouter(prefix="/v1/ai", tags=["ai"])

AI_RATE_LIMIT_PER_MINUTE = 10
AI_RATE_LIMIT_BURST = 5


class AISuggestRequest(BaseModel):
    draft_id: str
    mode: Literal["next", "rewrite", "summary", "commentary"]
    platform: Optional[Literal["x", "youtube", "instagram", "blog"]] = None

    @field_validator("draft_id")
    @classmethod
    def draft_id_required(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("draft_id is required")
        return value


@router.post("/suggest")
async def ai_suggest_endpoint(
    body: AISuggestRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)

    with start_span("api.ai_suggest", {"draft_id": body.draft_id, "mode": body.mode, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"ai:{user_id}",
                per_minute=AI_RATE_LIMIT_PER_MINUTE,
                burst=AI_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for AI suggestions", request_id=rid)

        try:
            result = suggest_ai_response(
                user_id=user_id,
                draft_id=body.draft_id,
                mode=body.mode,
                platform=body.platform,
            )
        except AppError:
            raise
        except Exception as exc:
            # Normalize any unexpected errors to validation for consistent contracts
            raise ValidationError(str(exc), request_id=rid)

        record_audit_event(
            action="ai_suggest",
            user_id=user_id,
            draft_id=body.draft_id,
            request_id=rid,
            metadata={"mode": body.mode, "platform": body.platform or "default"},
        )

        return {"data": result, "request_id": rid}
