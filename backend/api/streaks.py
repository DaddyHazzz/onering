from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.features.streaks.service import streak_service

router = APIRouter()


class PostedEvent(BaseModel):
    user_id: str = Field(..., min_length=1)
    post_id: str = Field(..., min_length=1)
    posted_at: Optional[datetime] = None
    platform: Optional[str] = None


class ScheduledEvent(BaseModel):
    user_id: str = Field(..., min_length=1)
    content_ref: str = Field(..., min_length=1)
    scheduled_for: Optional[datetime] = None


@router.get("/v1/streaks/current")
def get_current_streak(user_id: str = Query(..., min_length=1)):
    """Return the current streak state for a user."""
    return streak_service.get_state(user_id)


@router.get("/v1/streaks/history")
def get_streak_history(user_id: str = Query(..., min_length=1)):
    return {"history": streak_service.history(user_id)}


@router.post("/v1/streaks/events/post")
def handle_post_posted(event: PostedEvent):
    record, emitted = streak_service.record_posted(
        user_id=event.user_id,
        post_id=event.post_id,
        posted_at=_normalize(event.posted_at),
        platform=event.platform,
    )
    return {"state": streak_service.get_state(event.user_id), "emitted": emitted}


@router.post("/v1/streaks/events/scheduled")
def handle_post_scheduled(event: ScheduledEvent):
    streak_service.record_scheduled(
        user_id=event.user_id,
        content_ref=event.content_ref,
        scheduled_for=_normalize(event.scheduled_for),
    )
    return {"ack": True}


def _normalize(moment: Optional[datetime]) -> datetime:
    if moment is None:
        return datetime.now(timezone.utc)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)
