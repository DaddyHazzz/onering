"""
Analytics snapshot writer (Phase 4.0).
- Optional snapshot persistence for draft analytics and leaderboard.
- Reducers remain the source of truth; snapshots are read-only and reproducible.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from backend.features.analytics.event_store import get_store
from backend.features.analytics.reducers import reduce_draft_analytics, reduce_leaderboard

# In-memory snapshot store (fallback when DB not used)
_draft_snapshots: Dict[str, Dict[str, Any]] = {}
_leaderboard_snapshots: Dict[str, Dict[str, Any]] = {}


def _now_or_utc(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def write_draft_analytics_snapshots(now: Optional[datetime] = None) -> int:
    """Compute and store draft analytics snapshots for all known drafts.
    Returns number of snapshots written.
    """
    now_dt = _now_or_utc(now)
    store = get_store()
    events = store.get_events()
    draft_ids = sorted({e.data.get("draft_id") for e in events if e.data.get("draft_id")})

    count = 0
    for draft_id in draft_ids:
        analytics = reduce_draft_analytics(draft_id, events, now=now_dt)
        _draft_snapshots[draft_id] = analytics.model_dump(mode="json")
        count += 1
    return count


def write_leaderboard_snapshot(metric: str = "collaboration", now: Optional[datetime] = None) -> None:
    now_dt = _now_or_utc(now)
    store = get_store()
    events = store.get_events()
    leaderboard = reduce_leaderboard(metric, events, now=now_dt)
    _leaderboard_snapshots[metric] = leaderboard.model_dump(mode="json")


def get_draft_snapshot(draft_id: str) -> Optional[Dict[str, Any]]:
    return _draft_snapshots.get(draft_id)


def get_leaderboard_snapshot(metric: str = "collaboration") -> Optional[Dict[str, Any]]:
    return _leaderboard_snapshots.get(metric)
