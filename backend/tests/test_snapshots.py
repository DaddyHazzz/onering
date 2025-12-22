"""Tests for analytics snapshots (Phase 4.0)."""
from datetime import datetime, timezone, timedelta
from backend.features.analytics.event_store import EventStore, create_event, get_store
from backend.features.analytics.reducers import reduce_draft_analytics, reduce_leaderboard
from backend.features.analytics.snapshots import (
    write_draft_analytics_snapshots,
    write_leaderboard_snapshot,
    get_draft_snapshot,
    get_leaderboard_snapshot,
)


def test_draft_snapshots_match_reducer():
    EventStore.clear()
    now = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
    get_store().append(create_event("DraftCreated", {"draft_id": "d1", "creator_id": "u1"}, now=now - timedelta(hours=1)), "k1")

    # Write snapshots
    written = write_draft_analytics_snapshots(now=now)
    assert written >= 1

    # Compare snapshot to reducer output
    events = get_store().get_events()
    expected = reduce_draft_analytics("d1", events, now=now).model_dump(mode="json")
    snap = get_draft_snapshot("d1")
    assert snap is not None
    assert snap == expected


def test_leaderboard_snapshot_matches_reducer():
    EventStore.clear()
    now = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
    get_store().append(create_event("DraftCreated", {"draft_id": "d2", "creator_id": "u2"}, now=now), "k2")

    write_leaderboard_snapshot(metric="collaboration", now=now)
    events = get_store().get_events()
    expected = reduce_leaderboard("collaboration", events, now=now).model_dump(mode="json")
    snap = get_leaderboard_snapshot("collaboration")
    assert snap is not None
    assert snap == expected
