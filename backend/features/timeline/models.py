"""Timeline event models for Phase 8.3.

Normalized timeline events from audit logs.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    """Normalized timeline event from audit log."""
    
    event_id: str = Field(..., description="Stable event ID (audit ID or synthetic)")
    ts: datetime = Field(..., description="Event timestamp (ISO datetime)")
    type: Literal[
        "draft_created",
        "segment_added",
        "ring_passed",
        "collaborator_added",
        "ai_suggested",
        "format_generated",
        "other"
    ] = Field(..., description="Event type")
    actor_user_id: Optional[str] = Field(None, description="User who performed action")
    draft_id: str = Field(..., description="Draft ID")
    summary: str = Field(..., description="Human-readable summary")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Event-specific metadata")

    class Config:
        frozen = True


class TimelineResponse(BaseModel):
    """Timeline API response."""
    
    draft_id: str
    events: list[TimelineEvent]
    next_cursor: Optional[str] = None

    class Config:
        frozen = True


class ContributorStats(BaseModel):
    """Contributor attribution stats."""
    
    user_id: str
    segment_count: int
    segment_ids: list[str]
    first_ts: datetime
    last_ts: datetime

    class Config:
        frozen = True


class AttributionResponse(BaseModel):
    """Attribution API response."""
    
    draft_id: str
    contributors: list[ContributorStats]

    class Config:
        frozen = True
