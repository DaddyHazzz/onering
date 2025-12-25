"""Wait mode API endpoints (Phase 8.4).

Provides REST API for:
- Scratch notes (private notes about drafts)
- Queued suggestions (ideas for ring holder to consume)
- Segment votes (lightweight feedback)

All endpoints require auth and enforce collaborator access.
"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.core.auth import get_current_user_id
from backend.core.errors import AppError, RateLimitError
from backend.core.logging import get_request_id
from backend.core.metrics import ratelimit_block_total, normalize_path
from backend.core.tracing import start_span
from backend.features.waitmode.service import waitmode_service
from backend.features.waitmode.models import (
    CreateNoteRequest,
    UpdateNoteRequest,
    CreateSuggestionRequest,
    VoteRequest,
)


router = APIRouter(prefix="/v1/wait", tags=["waitmode"])

# Rate limits
NOTES_RATE_LIMIT_PER_MINUTE = 120
NOTES_RATE_LIMIT_BURST = 30
SUGGESTIONS_RATE_LIMIT_PER_MINUTE = 60
SUGGESTIONS_RATE_LIMIT_BURST = 15
VOTES_RATE_LIMIT_PER_MINUTE = 240
VOTES_RATE_LIMIT_BURST = 60


# ===== NOTES ENDPOINTS =====

@router.post("/drafts/{draft_id}/notes")
async def create_note(
    draft_id: str,
    body: CreateNoteRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Create a private scratch note.
    
    Rate limit: 120/min with burst of 30
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.create_note", {"draft_id": draft_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_notes:{user_id}",
                per_minute=NOTES_RATE_LIMIT_PER_MINUTE,
                burst=NOTES_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode notes", request_id=rid)
        
        try:
            note = waitmode_service.create_note(
                draft_id=draft_id,
                author_user_id=user_id,
                content=body.content,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"data": note.model_dump(), "request_id": rid}


@router.get("/drafts/{draft_id}/notes")
async def list_notes(
    draft_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List private notes for a draft (author-only).
    
    Rate limit: 120/min with burst of 30
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.list_notes", {"draft_id": draft_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_notes:{user_id}",
                per_minute=NOTES_RATE_LIMIT_PER_MINUTE,
                burst=NOTES_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode notes", request_id=rid)
        
        try:
            notes = waitmode_service.list_notes(
                draft_id=draft_id,
                user_id=user_id,
            )
        except AppError:
            raise
        
        return {"data": [n.model_dump() for n in notes], "request_id": rid}


@router.patch("/notes/{note_id}")
async def update_note(
    note_id: str,
    body: UpdateNoteRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Update a note (author only).
    
    Rate limit: 120/min with burst of 30
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.update_note", {"note_id": note_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_notes:{user_id}",
                per_minute=NOTES_RATE_LIMIT_PER_MINUTE,
                burst=NOTES_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode notes", request_id=rid)
        
        try:
            note = waitmode_service.update_note(
                note_id=note_id,
                user_id=user_id,
                content=body.content,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"data": note.model_dump(), "request_id": rid}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a note (author only).
    
    Rate limit: 120/min with burst of 30
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.delete_note", {"note_id": note_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_notes:{user_id}",
                per_minute=NOTES_RATE_LIMIT_PER_MINUTE,
                burst=NOTES_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode notes", request_id=rid)
        
        try:
            waitmode_service.delete_note(
                note_id=note_id,
                user_id=user_id,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"success": True, "request_id": rid}


# ===== SUGGESTIONS ENDPOINTS =====

@router.post("/drafts/{draft_id}/suggestions")
async def create_suggestion(
    draft_id: str,
    body: CreateSuggestionRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Create a queued suggestion.
    
    Rate limit: 60/min with burst of 15
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.create_suggestion", {"draft_id": draft_id, "user_id": user_id, "kind": body.kind}):
        if limiter:
            allowed = limiter.allow(
                f"wait_suggestions:{user_id}",
                per_minute=SUGGESTIONS_RATE_LIMIT_PER_MINUTE,
                burst=SUGGESTIONS_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode suggestions", request_id=rid)
        
        try:
            suggestion = waitmode_service.create_suggestion(
                draft_id=draft_id,
                author_user_id=user_id,
                kind=body.kind,
                content=body.content,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"data": suggestion.model_dump(), "request_id": rid}


@router.get("/drafts/{draft_id}/suggestions")
async def list_suggestions(
    draft_id: str,
    status: Optional[Literal["queued", "consumed", "dismissed"]] = None,
    request: Request = None,
    user_id: str = Depends(get_current_user_id),
):
    """List suggestions for a draft (author-only by default).
    
    Rate limit: 60/min with burst of 15
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.list_suggestions", {"draft_id": draft_id, "user_id": user_id, "status": status}):
        if limiter:
            allowed = limiter.allow(
                f"wait_suggestions:{user_id}",
                per_minute=SUGGESTIONS_RATE_LIMIT_PER_MINUTE,
                burst=SUGGESTIONS_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode suggestions", request_id=rid)
        
        try:
            suggestions = waitmode_service.list_suggestions(
                draft_id=draft_id,
                user_id=user_id,
                status=status,
            )
        except AppError:
            raise
        
        return {"data": [s.model_dump() for s in suggestions], "request_id": rid}


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Dismiss a suggestion (author only).
    
    Rate limit: 60/min with burst of 15
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.dismiss_suggestion", {"suggestion_id": suggestion_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_suggestions:{user_id}",
                per_minute=SUGGESTIONS_RATE_LIMIT_PER_MINUTE,
                burst=SUGGESTIONS_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode suggestions", request_id=rid)
        
        try:
            suggestion = waitmode_service.dismiss_suggestion(
                suggestion_id=suggestion_id,
                user_id=user_id,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"data": suggestion.model_dump(), "request_id": rid}


@router.post("/suggestions/{suggestion_id}/consume")
async def consume_suggestion(
    suggestion_id: str,
    segment_id: Optional[str] = None,
    request: Request = None,
    user_id: str = Depends(get_current_user_id),
):
    """Consume a suggestion (ring holder only).
    
    Marks suggestion as consumed. Does NOT automatically append segment.
    Ring holder should manually append segment with suggestion content.
    
    Rate limit: 60/min with burst of 15
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.consume_suggestion", {"suggestion_id": suggestion_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_suggestions:{user_id}",
                per_minute=SUGGESTIONS_RATE_LIMIT_PER_MINUTE,
                burst=SUGGESTIONS_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode suggestions", request_id=rid)
        
        try:
            suggestion = waitmode_service.consume_suggestion(
                suggestion_id=suggestion_id,
                user_id=user_id,
                segment_id=segment_id,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"data": suggestion.model_dump(), "request_id": rid}


# ===== VOTES ENDPOINTS =====

@router.post("/drafts/{draft_id}/segments/{segment_id}/vote")
async def vote_segment(
    draft_id: str,
    segment_id: str,
    body: VoteRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Vote on a segment (upsert behavior).
    
    Rate limit: 240/min with burst of 60
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.vote_segment", {"draft_id": draft_id, "segment_id": segment_id, "user_id": user_id, "value": body.value}):
        if limiter:
            allowed = limiter.allow(
                f"wait_votes:{user_id}",
                per_minute=VOTES_RATE_LIMIT_PER_MINUTE,
                burst=VOTES_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode votes", request_id=rid)
        
        try:
            vote = waitmode_service.vote_segment(
                draft_id=draft_id,
                segment_id=segment_id,
                voter_user_id=user_id,
                value=body.value,
                request_id=rid,
            )
        except AppError:
            raise
        
        return {"data": vote.model_dump(), "request_id": rid}


@router.get("/drafts/{draft_id}/votes")
async def list_votes(
    draft_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List votes for all segments in a draft.
    
    Returns per-segment totals + user's vote.
    
    Rate limit: 240/min with burst of 60
    """
    rid = getattr(request.state, "request_id", None) or get_request_id()
    limiter = getattr(request.app.state, "rate_limiter", None)
    
    with start_span("api.waitmode.list_votes", {"draft_id": draft_id, "user_id": user_id}):
        if limiter:
            allowed = limiter.allow(
                f"wait_votes:{user_id}",
                per_minute=VOTES_RATE_LIMIT_PER_MINUTE,
                burst=VOTES_RATE_LIMIT_BURST,
            )
            if not allowed:
                ratelimit_block_total.inc(labels={"scope": normalize_path(str(request.url.path))})
                raise RateLimitError("Rate limit exceeded for wait mode votes", request_id=rid)
        
        try:
            votes = waitmode_service.list_votes(
                draft_id=draft_id,
                user_id=user_id,
            )
        except AppError:
            raise
        
        return {"data": votes.model_dump(), "request_id": rid}
