"""
backend/models/analytics.py
Analytics models: DraftAnalytics, UserAnalytics, LeaderboardEntry.
All deterministic, no engagement chasing, no dark patterns.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Literal


class DraftAnalytics(BaseModel):
    """Analytics for a single collaborative draft."""

    model_config = ConfigDict(frozen=True)

    draft_id: str = Field(description="UUID")
    views: int = Field(ge=0, description="Number of views (clicks from share)")
    shares: int = Field(ge=0, description="Number of times shared")
    segments_count: int = Field(ge=0, description="Total segments in draft (0 allowed)")
    contributors_count: int = Field(ge=1, description="Unique contributors (including creator)")
    ring_passes_count: int = Field(ge=0, description="Total ring passes in lifetime of draft")
    last_activity_at: Optional[datetime] = Field(default=None, description="Most recent activity (segment add, ring pass)")
    computed_at: datetime = Field(description="When analytics were computed")


class UserAnalytics(BaseModel):
    """Analytics for a user across all their contributions."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(description="Clerk user ID")
    drafts_created: int = Field(ge=0, description="Drafts authored")
    drafts_contributed: int = Field(ge=0, description="Drafts with segments added (excluding created)")
    segments_written: int = Field(ge=0, description="Total segments contributed")
    rings_held_count: int = Field(ge=0, description="Times held ring in drafts")
    avg_time_holding_ring_minutes: float = Field(ge=0, description="Average minutes before passing ring")
    last_active_at: Optional[datetime] = Field(default=None, description="Most recent activity")
    computed_at: datetime = Field(description="When analytics were computed")


class LeaderboardEntry(BaseModel):
    """Single entry in leaderboard."""

    model_config = ConfigDict(frozen=True)

    position: int = Field(ge=1, le=10, description="Position (1-10)")
    user_id: str = Field(description="Clerk user ID")
    display_name: str = Field(description="User display name")
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL")
    metric_value: float = Field(description="Metric value for this leaderboard type")
    metric_label: str = Field(description="Human-readable label (e.g., '12 segments')")
    insight: str = Field(description="Supportive insight, never comparative")


class LeaderboardResponse(BaseModel):
    """Response for leaderboard endpoint."""

    model_config = ConfigDict(frozen=True)

    metric_type: Literal["collaboration", "momentum", "consistency"] = Field(description="Leaderboard type")
    entries: List[LeaderboardEntry] = Field(description="Top 10 entries")
    computed_at: datetime = Field(description="When leaderboard was computed")
    message: str = Field(description="Supportive header message (never comparative)")


class LeaderboardRequest(BaseModel):
    """Request for leaderboard."""

    metric: Literal["collaboration", "momentum", "consistency"] = Field(default="collaboration")
    now: Optional[str] = Field(default=None, description="ISO timestamp for deterministic results")
