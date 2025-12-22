"""
backend/models/collab.py
Collaboration draft models: minimal, idempotent design.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class DraftStatus(str, Enum):
    """Draft lifecycle: created -> adding_segments -> ready_to_post -> posted"""

    ACTIVE = "active"
    LOCKED = "locked"  # Ring holder passed, awaiting next action
    COMPLETED = "completed"


class DraftSegment(BaseModel):
    """Individual segment contributed to draft"""

    model_config = ConfigDict(frozen=True)

    segment_id: str = Field(description="UUID")
    draft_id: str = Field(description="Parent draft UUID")
    user_id: str = Field(description="Segment author user ID")
    content: str = Field(min_length=1, max_length=500)
    created_at: datetime
    segment_order: int = Field(description="Order in thread (0-indexed)")
    idempotency_key: Optional[str] = None
    # Phase 3.3a: Attribution fields
    author_user_id: Optional[str] = Field(default=None, description="Author user ID (same as user_id for now)")
    author_display: Optional[str] = Field(default=None, description="Deterministic display name")
    ring_holder_user_id_at_write: Optional[str] = Field(default=None, description="Ring holder when segment was written")
    ring_holder_display_at_write: Optional[str] = Field(default=None, description="Ring holder display name at write")


class RingState(BaseModel):
    """Ring holder state within draft"""

    model_config = ConfigDict(frozen=True)

    draft_id: str
    current_holder_id: str = Field(description="User ID who can append")
    holders_history: List[str] = Field(default_factory=list, description="All past holders")
    passed_at: datetime
    last_passed_at: Optional[datetime] = Field(default=None, description="ISO timestamp of last ring pass (Phase 3.3a)")
    idempotency_key: Optional[str] = None


class CollabDraft(BaseModel):
    """Collaboration draft: multiple contributors, pass-the-ring ownership"""

    model_config = ConfigDict(frozen=True)

    draft_id: str = Field(description="UUID")
    creator_id: str
    title: str = Field(max_length=200)
    platform: str = Field(
        description="Target platform: 'x', 'instagram', 'tiktok', 'youtube'"
    )
    status: DraftStatus = Field(default=DraftStatus.ACTIVE)
    segments: List[DraftSegment] = Field(default_factory=list)
    ring_state: RingState
    collaborators: List[str] = Field(
        default_factory=list, description="User IDs of accepted collaborators (excludes creator)"
    )
    pending_invites: List[str] = Field(
        default_factory=list, description="Invite IDs pending acceptance"
    )
    created_at: datetime
    updated_at: datetime
    target_publish_at: Optional[datetime] = None
    # Phase 3.3a: Ring velocity metrics (computed on read)
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Ring velocity metrics: contributorsCount, ringPassesLast24h, avgMinutesBetweenPasses, lastActivityAt"
    )


class CollabDraftRequest(BaseModel):
    """Request to create new draft"""

    title: str = Field(min_length=1, max_length=200)
    platform: str = Field(
        description="'x' | 'instagram' | 'tiktok' | 'youtube'"
    )
    initial_segment: Optional[str] = Field(
        default=None, max_length=500, description="Optional first segment"
    )


class SegmentAppendRequest(BaseModel):
    """Request to append segment (idempotent)"""

    content: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(
        description="UUID, prevents duplicate appends"
    )


class RingPassRequest(BaseModel):
    """Request to pass ring (idempotent)"""

    to_user_id: str
    idempotency_key: str = Field(
        description="UUID, prevents duplicate passes"
    )
