from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

StreakDecayState = Literal["none", "partial"]
StreakStatus = Literal["active", "grace", "decayed"]


@dataclass
class StreakRecord:
    """
    Domain model for a creator streak. Day-level, UTC only, no direct DB concerns.
    """

    user_id: str
    current_length: int = 0
    longest_length: int = 0
    last_active_date: Optional[date] = None
    grace_used: bool = False
    decay_state: StreakDecayState = "none"
    processed_event_ids: set[str] = field(default_factory=set)
    incremented_days: set[date] = field(default_factory=set)
    history: list[StreakSnapshot] = field(default_factory=list)


@dataclass
class StreakSnapshot:
    day: date
    current_length: int
    longest_length: int
    status: StreakStatus
    reason: str
