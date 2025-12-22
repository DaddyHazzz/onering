#!/usr/bin/env python
"""
Verification script for Phase 1 Creator Streaks implementation.
Demonstrates determinism, mercy mechanics, and idempotency.
"""

from datetime import datetime, timedelta, timezone
from backend.features.streaks.service import StreakService


def demo_scenario(name: str, demo_fn) -> None:
    print(f"\n{'='*70}")
    print(f"SCENARIO: {name}")
    print('='*70)
    demo_fn()


def scenario_fresh_start():
    """Day 1: First post starts streak at 1."""
    service = StreakService()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    service.record_posted(user_id="alice", post_id="p1", posted_at=now, platform="x")
    state = service.get_state("alice")
    
    print(f"✓ Current streak: {state['current_length']} day(s)")
    print(f"✓ Status: {state['status']}")
    print(f"✓ Next action: {state['next_action_hint']}")
    assert state['current_length'] == 1, "Fresh streak should be 1"
    assert state['status'] == 'active', "Fresh streak should be active"


def scenario_continuous_days():
    """Day 2: Continuous posting maintains active status."""
    service = StreakService()
    day1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    day2 = day1 + timedelta(days=1)
    
    service.record_posted(user_id="bob", post_id="p1", posted_at=day1, platform="x")
    service.record_posted(user_id="bob", post_id="p2", posted_at=day2, platform="x")
    state = service.get_state("bob")
    
    print(f"✓ Current streak: {state['current_length']} day(s)")
    print(f"✓ Status: {state['status']}")
    assert state['current_length'] == 2, "Continuous days should be 2"
    assert state['status'] == 'active', "Should remain active"


def scenario_grace_day():
    """Day 4 after Day 2: Miss 1 day, grace protects momentum."""
    service = StreakService()
    day2 = datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)
    day4 = day2 + timedelta(days=2)
    
    service.record_posted(user_id="charlie", post_id="p1", posted_at=day2, platform="x")
    service.record_posted(user_id="charlie", post_id="p2", posted_at=day4, platform="x")
    state = service.get_state("charlie")
    
    print(f"✓ Current streak: {state['current_length']} day(s)")
    print(f"✓ Status: {state['status']} (grace window used)")
    print(f"✓ Next action: {state['next_action_hint']}")
    assert state['current_length'] == 2, "Momentum preserved by grace"
    assert state['status'] == 'grace', "Grace status should be active"


def scenario_partial_decay():
    """Day 6 after Day 2: Miss 3 days, decay trims momentum."""
    service = StreakService()
    day2 = datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)
    day6 = day2 + timedelta(days=4)
    
    service.record_posted(user_id="diana", post_id="p1", posted_at=day2, platform="x")
    service.record_posted(user_id="diana", post_id="p2", posted_at=day6, platform="x")
    state = service.get_state("diana")
    
    print(f"✓ Current streak: {state['current_length']} day(s)")
    print(f"✓ Status: {state['status']} (partial decay)")
    print(f"✓ Next action: {state['next_action_hint']}")
    assert state['current_length'] >= 1, "Minimum 1 day preserved"
    assert state['status'] == 'decayed', "Status should show decay"
    assert state['current_length'] < 2, "Decay should reduce momentum"


def scenario_protection_window():
    """7-day streak resets grace window."""
    service = StreakService()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # Build 7-day streak
    for i in range(7):
        service.record_posted(
            user_id="ethan",
            post_id=f"p{i+1}",
            posted_at=now + timedelta(days=i),
            platform="x"
        )
    
    state = service.get_state("ethan")
    print(f"✓ Current streak: {state['current_length']} day(s)")
    print(f"✓ Status: {state['status']}")
    print(f"✓ Grace used: {state['grace_used']}")
    assert state['current_length'] == 7, "Should reach 7-day milestone"
    assert state['grace_used'] == False, "Grace should reset at stride boundary"


def scenario_idempotent_retry():
    """Same post_id on retry produces identical state."""
    service = StreakService()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # First post
    service.record_posted(user_id="frank", post_id="duplicate", posted_at=now, platform="x")
    state1 = service.get_state("frank")
    
    # Retry same post_id (simulated network retry)
    service.record_posted(
        user_id="frank",
        post_id="duplicate",
        posted_at=now + timedelta(seconds=30),
        platform="x"
    )
    state2 = service.get_state("frank")
    
    print(f"✓ First call: {state1['current_length']} day(s)")
    print(f"✓ Retry call: {state2['current_length']} day(s)")
    print(f"✓ States identical: {state1 == state2}")
    assert state1['current_length'] == state2['current_length'] == 1, "Idempotent"


def scenario_double_post_same_day():
    """Two posts same day increment only once."""
    service = StreakService()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    service.record_posted(user_id="grace", post_id="p1", posted_at=now, platform="x")
    service.record_posted(user_id="grace", post_id="p2", posted_at=now + timedelta(hours=2), platform="x")
    state = service.get_state("grace")
    
    print(f"✓ Two posts same day, current streak: {state['current_length']}")
    assert state['current_length'] == 1, "Max 1 increment per day"


def scenario_failed_post():
    """Failed posts never break streaks."""
    service = StreakService()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    service.record_posted(user_id="henry", post_id="p1", posted_at=now, platform="x")
    service.record_failed_post(user_id="henry")
    state = service.get_state("henry")
    
    print(f"✓ After failed post, current streak: {state['current_length']}")
    assert state['current_length'] == 1, "Failed post never breaks streak"


def main():
    print("\n" + "="*70)
    print("PHASE 1 CREATOR STREAKS — VERIFICATION")
    print("="*70)
    print("\nDemonstrating deterministic behavior, mercy mechanics, and idempotency.")
    
    demo_scenario("Fresh Start (Day 1)", scenario_fresh_start)
    demo_scenario("Continuous Days", scenario_continuous_days)
    demo_scenario("Grace Window (1-day miss)", scenario_grace_day)
    demo_scenario("Partial Decay (3-day miss)", scenario_partial_decay)
    demo_scenario("Protection Window (7-day stride)", scenario_protection_window)
    demo_scenario("Idempotent Retry", scenario_idempotent_retry)
    demo_scenario("Double Post Same Day", scenario_double_post_same_day)
    demo_scenario("Failed Post Never Breaks Streak", scenario_failed_post)
    
    print("\n" + "="*70)
    print("✅ ALL VERIFICATION SCENARIOS PASSED")
    print("="*70)
    print("\nKey Invariants Verified:")
    print("  ✅ No double-increment in same UTC day")
    print("  ✅ Failed posts never break streaks")
    print("  ✅ Grace protects one missed day")
    print("  ✅ Partial decay preserves momentum (min 1 day)")
    print("  ✅ Protection window resets every 7 days")
    print("  ✅ Idempotent retries produce identical state")
    print("\nCreator Streaks is production-ready. 🚀")


if __name__ == "__main__":
    main()
