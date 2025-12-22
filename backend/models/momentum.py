"""
Momentum domain model.

Momentum Score answers: "Am I gaining or losing momentum this week?"
It is deterministic, stable, and interpretable—not a raw metric, but a mirror.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal, Optional


MomentumTrend = Literal["up", "flat", "down"]


@dataclass
class MomentumComponents:
    """Individual contributors to overall momentum score."""

    streak_component: float = 0.0  # 0..25 points from streak health
    consistency_component: float = 0.0  # 0..10 points from consistency
    challenge_component: float = 0.0  # 0..15 points from daily challenges
    coach_component: float = 0.0  # 0..10 points from coach improvement signals

    def validate(self) -> None:
        """Ensure all components are in valid ranges."""
        assert 0.0 <= self.streak_component <= 25.0, f"streak_component out of range: {self.streak_component}"
        assert 0.0 <= self.consistency_component <= 10.0, f"consistency_component out of range: {self.consistency_component}"
        assert 0.0 <= self.challenge_component <= 15.0, f"challenge_component out of range: {self.challenge_component}"
        assert 0.0 <= self.coach_component <= 10.0, f"coach_component out of range: {self.coach_component}"

    def total(self) -> float:
        """Sum of all components (before clamping to 0..100)."""
        return (
            self.streak_component
            + self.consistency_component
            + self.challenge_component
            + self.coach_component
        )

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return asdict(self)


@dataclass
class MomentumSnapshot:
    """
    Daily momentum snapshot for a user.
    
    Represents the user's momentum at a point in time, computed deterministically
    from streak, challenge, consistency, and coach signals.
    
    Attributes:
        user_id: User identifier (Clerk user ID)
        date: UTC date (YYYY-MM-DD) this snapshot represents
        score: Overall momentum score, 0..100 (clamped)
        trend: Direction of momentum (up / flat / down) vs 7-day rolling average
        components: Breakdown of score by source
        next_action_hint: Supportive guidance for today (never shaming)
        computed_at: UTC timestamp when this was calculated
    """

    user_id: str
    date: str  # ISO date YYYY-MM-DD in UTC
    score: float  # 0..100, clamped
    trend: MomentumTrend
    components: MomentumComponents
    next_action_hint: str
    computed_at: datetime

    def validate(self) -> None:
        """Ensure snapshot is valid."""
        assert self.user_id, "user_id required"
        assert self.date, "date required in YYYY-MM-DD format"
        assert 0.0 <= self.score <= 100.0, f"score out of range: {self.score}"
        assert self.trend in ["up", "flat", "down"], f"invalid trend: {self.trend}"
        assert self.next_action_hint, "next_action_hint required"
        self.components.validate()

    def to_dict(self) -> dict:
        """Serialize to dict for JSON response."""
        return {
            "userId": self.user_id,
            "date": self.date,
            "score": round(self.score, 1),  # Round to 1 decimal
            "trend": self.trend,
            "components": {
                "streakComponent": round(self.components.streak_component, 1),
                "consistencyComponent": round(self.components.consistency_component, 1),
                "challengeComponent": round(self.components.challenge_component, 1),
                "coachComponent": round(self.components.coach_component, 1),
            },
            "nextActionHint": self.next_action_hint,
            "computedAt": self.computed_at.isoformat(),
        }
