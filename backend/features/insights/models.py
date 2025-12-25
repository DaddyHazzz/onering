"""
Phase 8.7: Insight Engine - Data Models

Pydantic models for draft insights, recommendations, and alerts.
All models frozen (immutable).
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class InsightType(str, Enum):
    """Types of insights derived from analytics."""
    STALLED = "stalled"
    DOMINANT_USER = "dominant_user"
    LOW_ENGAGEMENT = "low_engagement"
    HEALTHY = "healthy"


class InsightSeverity(str, Enum):
    """Severity level for insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DraftInsight(BaseModel):
    """
    A derived insight about a draft's collaboration health.
    
    Always includes `reason` for explainability.
    """
    type: InsightType
    severity: InsightSeverity
    title: str = Field(..., description="Short human-readable title")
    message: str = Field(..., description="Longer explanation")
    reason: str = Field(..., description="Deterministic explanation referencing metrics")
    metrics_snapshot: Dict[str, Union[int, float, str]] = Field(
        default_factory=dict,
        description="Snapshot of metrics that triggered this insight"
    )
    
    class Config:
        frozen = True


class RecommendationAction(str, Enum):
    """Types of recommended actions."""
    PASS_RING = "pass_ring"
    INVITE_USER = "invite_user"
    ADD_SEGMENT = "add_segment"
    REVIEW_SUGGESTIONS = "review_suggestions"


class DraftRecommendation(BaseModel):
    """
    An actionable recommendation for improving collaboration.
    
    Always includes `reason` for transparency.
    """
    action: RecommendationAction
    target_user_id: Optional[str] = Field(None, description="User to pass ring to or invite")
    reason: str = Field(..., description="Why this recommendation is being made")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    
    class Config:
        frozen = True


class AlertType(str, Enum):
    """Types of alerts that can be triggered."""
    NO_ACTIVITY = "no_activity"
    LONG_RING_HOLD = "long_ring_hold"
    SINGLE_CONTRIBUTOR = "single_contributor"


class DraftAlert(BaseModel):
    """
    A threshold-based alert computed from current draft state.
    
    Not stored; computed on demand.
    """
    alert_type: AlertType
    triggered_at: datetime
    threshold: str = Field(..., description="Human-readable threshold description")
    current_value: Union[int, float] = Field(..., description="Current metric value")
    reason: str = Field(..., description="Explanation of why alert triggered")
    
    class Config:
        frozen = True


class DraftInsightsResponse(BaseModel):
    """
    Complete insights response for a draft.
    """
    draft_id: str
    insights: list[DraftInsight]
    recommendations: list[DraftRecommendation]
    alerts: list[DraftAlert]
    computed_at: datetime
    
    class Config:
        frozen = True
