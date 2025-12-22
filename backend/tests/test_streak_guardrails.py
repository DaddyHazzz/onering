from datetime import datetime, timedelta, timezone

from backend.features.streaks.service import StreakService


def test_streak_not_increment_twice_same_day():
    service = StreakService()
    now = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

    service.record_posted(user_id="u1", post_id="p1", posted_at=now, platform="x")
    service.record_posted(user_id="u1", post_id="p2", posted_at=now, platform="x")

    state = service.get_state("u1")
    assert state["current_length"] == 1
    assert state["status"] == "active"


def test_failed_post_does_not_break_streak():
    service = StreakService()
    day_one = datetime(2024, 1, 1, tzinfo=timezone.utc)

    service.record_posted(user_id="u2", post_id="p1", posted_at=day_one, platform="x")
    service.record_failed_post(user_id="u2")

    state = service.get_state("u2")
    assert state["current_length"] == 1
    assert state["status"] == "active"


def test_grace_day_behavior():
    service = StreakService()
    day_one = datetime(2024, 1, 1, tzinfo=timezone.utc)
    day_three = day_one + timedelta(days=2)

    service.record_posted(user_id="u3", post_id="p1", posted_at=day_one, platform="x")
    service.record_posted(user_id="u3", post_id="p2", posted_at=day_three, platform="x")

    state = service.get_state("u3")
    assert state["current_length"] == 2  # Missed one day but grace preserved momentum
    assert state["status"] == "grace"


def test_partial_decay_behavior():
    service = StreakService()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    service.record_posted(user_id="u4", post_id="p1", posted_at=start, platform="x")
    service.record_posted(user_id="u4", post_id="p2", posted_at=start + timedelta(days=1), platform="x")

    # Miss several days; only first miss is protected, remaining trigger partial decay
    late_return = start + timedelta(days=5)
    service.record_posted(user_id="u4", post_id="p3", posted_at=late_return, platform="x")

    state = service.get_state("u4")
    assert state["status"] == "decayed"
    assert state["current_length"] >= 1
    assert state["current_length"] < 3  # Partial decay trimmed the prior momentum


def test_idempotent_retries_do_not_double_count():
    service = StreakService()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    service.record_posted(user_id="u5", post_id="dup", posted_at=now, platform="x")
    service.record_posted(user_id="u5", post_id="dup", posted_at=now + timedelta(seconds=30), platform="x")

    state = service.get_state("u5")
    assert state["current_length"] == 1
    assert state["longest_length"] == 1
