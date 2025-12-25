"""
backend/features/analytics/models.py
Analytics response models for Phase 8.6 — Segment-level metrics + Activity dashboards
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class InactivityRisk(str, Enum):
    """Inactivity risk assessment based on last activity and ring passes"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DraftAnalyticsSummary(BaseModel):
    """Top-level analytics for a collaborative draft"""
    
    model_config = ConfigDict(frozen=True)
    
    draft_id: str = Field(description="Draft UUID")
    total_segments: int = Field(ge=0, description="Total segments added")
    total_words: int = Field(ge=0, description="Sum of all segment word counts")
    unique_contributors: int = Field(ge=0, description="Count of distinct contributors")
    last_activity_ts: Optional[datetime] = Field(default=None, description="ISO timestamp of last segment/ring event")
    ring_pass_count: int = Field(ge=0, description="Total ring passes")
    avg_time_holding_ring_seconds: Optional[float] = Field(default=None, ge=0, description="Mean hold duration across all rings")
    inactivity_risk: InactivityRisk = Field(description="low|medium|high based on time since last activity")


class ContributorMetrics(BaseModel):
    """Metrics for a single contributor in a draft"""
    
    model_config = ConfigDict(frozen=True)
    
    user_id: str = Field(description="Contributor user ID")
    segments_added_count: int = Field(ge=0)
    words_added: int = Field(ge=0)
    first_contribution_ts: Optional[datetime] = Field(default=None)
    last_contribution_ts: Optional[datetime] = Field(default=None)
    ring_holds_count: int = Field(ge=0, description="Times held the ring")
    total_hold_seconds: int = Field(ge=0, description="Total seconds holding ring")
    suggestions_queued_count: int = Field(ge=0, description="Wait mode suggestions queued (if present)")
    votes_cast_count: int = Field(ge=0, description="Wait mode votes cast (if present)")


class DraftAnalyticsContributors(BaseModel):
    """Contributor breakdown for a draft"""
    
    model_config = ConfigDict(frozen=True)
    
    draft_id: str
    contributors: List[ContributorMetrics] = Field(description="Sorted by last_contribution_ts DESC")
    total_contributors: int = Field(ge=0)


class RingHold(BaseModel):
    """Record of a ring hold period"""
    
    model_config = ConfigDict(frozen=True)
    
    user_id: str = Field(description="User who held the ring")
    start_ts: datetime = Field(description="When ring holder started")
    end_ts: Optional[datetime] = Field(default=None, description="When ring was passed (None if current holder)")
    seconds: int = Field(ge=0, description="Duration in seconds")


class RingPass(BaseModel):
    """Record of a ring pass event"""
    
    model_config = ConfigDict(frozen=True)
    
    from_user_id: str
    to_user_id: str
    ts: datetime = Field(description="When pass occurred")
    strategy: Optional[str] = Field(default=None, description="Strategy if smart pass (most_inactive, round_robin, etc)")


class RingRecommendation(BaseModel):
    """Recommendation for next ring holder"""
    
    model_config = ConfigDict(frozen=True)
    
    recommended_to_user_id: str = Field(description="User ID recommended to receive ring")
    reason: str = Field(description="Human-readable explanation")


class DraftAnalyticsRing(BaseModel):
    """Ring dynamics for a draft"""
    
    model_config = ConfigDict(frozen=True)
    
    draft_id: str
    current_holder_id: str = Field(description="Current ring holder")
    holds: List[RingHold] = Field(description="Last N holds (most recent first)")
    passes: List[RingPass] = Field(description="Last N passes (most recent first)")
    recommendation: Optional[RingRecommendation] = Field(default=None, description="Next holder suggestion")


class DailyActivityMetrics(BaseModel):
    """Activity metrics for a single day"""
    
    model_config = ConfigDict(frozen=True)
    
    date: str = Field(description="YYYY-MM-DD in UTC")
    segments_added: int = Field(ge=0)
    ring_passes: int = Field(ge=0)


class DraftAnalyticsDaily(BaseModel):
    """Daily activity sparkline for a draft"""
    
    model_config = ConfigDict(frozen=True)
    
    draft_id: str
    days: List[DailyActivityMetrics] = Field(description="Last N days in chronological order")
    window_days: int = Field(description="Number of days requested (e.g., 14)")
