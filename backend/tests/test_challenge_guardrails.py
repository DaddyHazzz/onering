from datetime import date, datetime, timedelta, timezone

from backend.features.challenges.service import ChallengeService


def test_challenge_assignment_deterministic():
    """Same user + same date = same challenge."""
    service = ChallengeService()
    day = date(2024, 1, 1)

    result1 = service.get_today_challenge(user_id="alice", today=day)
    result2 = service.get_today_challenge(user_id="alice", today=day)

    assert result1.challenge_id == result2.challenge_id
    assert result1.prompt == result2.prompt
    assert result1.type == result2.type


def test_different_users_get_different_challenges():
    """Different users get different deterministic challenges."""
    service = ChallengeService()
    day = date(2024, 1, 1)

    alice = service.get_today_challenge(user_id="alice", today=day)
    bob = service.get_today_challenge(user_id="bob", today=day)

    # Different users should get different challenges (high probability)
    assert alice.challenge_id != bob.challenge_id


def test_lifecycle_assigned_accepted_completed():
    """Challenge progresses through lifecycle states."""
    service = ChallengeService()
    day = date(2024, 1, 1)

    # Assigned
    result = service.get_today_challenge(user_id="charlie", today=day)
    assert result.status == "assigned"

    # Accept
    accepted, _ = service.accept_challenge(
        user_id="charlie",
        challenge_id=result.challenge_id,
        accepted_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    assert accepted.status == "accepted"

    # Complete
    completed, _ = service.complete_challenge(
        user_id="charlie",
        challenge_id=result.challenge_id,
        completed_at=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
    )
    assert completed.status == "completed"


def test_idempotent_accept():
    """Accepting same challenge twice is idempotent."""
    service = ChallengeService()
    day = date(2024, 1, 1)

    result = service.get_today_challenge(user_id="diana", today=day)

    # First accept
    _, events1 = service.accept_challenge(user_id="diana", challenge_id=result.challenge_id)
    # Second accept
    _, events2 = service.accept_challenge(user_id="diana", challenge_id=result.challenge_id)

    assert len(events1) == 1  # First accept emits event
    assert len(events2) == 0  # Second accept is no-op


def test_idempotent_complete():
    """Completing same challenge twice is idempotent."""
    service = ChallengeService()
    day = date(2024, 1, 1)

    result = service.get_today_challenge(user_id="ethan", today=day)

    # First complete
    _, events1 = service.complete_challenge(user_id="ethan", challenge_id=result.challenge_id)
    # Second complete
    _, events2 = service.complete_challenge(user_id="ethan", challenge_id=result.challenge_id)

    assert len(events1) == 1  # First complete emits event
    assert len(events2) == 0  # Second complete is no-op


def test_expiration_marks_old_challenges():
    """Old challenges are expired when cutoff date passes."""
    service = ChallengeService()
    day1 = date(2024, 1, 1)
    day3 = date(2024, 1, 3)

    # Assign day 1 challenge
    service.get_today_challenge(user_id="frank", today=day1)

    # Expire all challenges before day 3
    expired_count = service.expire_old_challenges(cutoff_date=day3)
    assert expired_count == 1

    # Re-fetch and check status
    result = service.get_today_challenge(user_id="frank", today=day1)
    assert result.status == "expired"


def test_challenge_completion_does_not_double_increment_streak():
    """Challenge completion increments streak only if not already incremented today."""
    from backend.features.streaks.service import StreakService

    streak_service = StreakService()
    challenge_service = ChallengeService()
    day = date(2024, 1, 1)
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    # User posts first
    streak_service.record_posted(user_id="grace", post_id="p1", posted_at=now, platform="x")
    streak_state = streak_service.get_state("grace")
    assert streak_state["current_length"] == 1

    # User completes challenge (should not double-increment)
    challenge = challenge_service.get_today_challenge(user_id="grace", today=day)
    challenge_service.complete_challenge(user_id="grace", challenge_id=challenge.challenge_id)

    # Manually check: if we try to record_posted with challenge_id, it should be deduplicated
    _, events = streak_service.record_posted(
        user_id="grace", post_id=challenge.challenge_id, posted_at=now, platform="challenge"
    )
    assert len(events) == 0  # No new streak event because already incremented today
    
    streak_state = streak_service.get_state("grace")
    assert streak_state["current_length"] == 1  # Still 1, no double increment
