from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional

ChallengeType = Literal["creative", "reflective", "engagement", "growth"]
ChallengeStatus = Literal["assigned", "accepted", "completed", "expired"]
StreakEffect = Literal["none", "would_increment", "incremented"]


@dataclass
class Challenge:
    """Domain model for a daily challenge."""

    challenge_id: str
    user_id: str
    date: date
    type: ChallengeType
    prompt: str
    status: ChallengeStatus = "assigned"
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_source: Optional[str] = None  # post_id if tied to a post
    metadata: dict = field(default_factory=dict)


@dataclass
class ChallengeResult:
    """Response wrapper for challenge queries."""

    challenge_id: str
    date: str
    type: ChallengeType
    prompt: str
    status: ChallengeStatus
    next_action_hint: str
    streak_effect: StreakEffect
    metadata: dict = field(default_factory=dict)
