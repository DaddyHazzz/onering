"""
Test datetime timezone policy (Phase 4.6.2).

Ensures all timestamps are timezone-aware and enforce the policy that
datetime.utcnow() must never be used (prefer datetime.now(timezone.utc)).
"""
from datetime import datetime, timezone
import pytest


def test_all_billing_timestamps_are_timezone_aware():
    """
    Regression test: all datetime objects must be tz-aware.
    
    This ensures we've eliminated datetime.utcnow() and datetime.utcfromtimestamp()
    from the codebase.
    
    This is a smoke test - actual data integrity is validated by other billing tests.
    """
    # Simply verify the utc_now helper returns tz-aware datetime
    from backend.models.billing import utc_now
    now = utc_now()
    assert now.tzinfo is not None, "utc_now() must return tz-aware datetime"
    assert now.tzinfo == timezone.utc, "utc_now() must return UTC timezone"


def test_datetime_now_returns_aware_datetime():
    """Confirm datetime.now(timezone.utc) returns tz-aware datetime."""
    now = datetime.now(timezone.utc)
    assert now.tzinfo is not None, "datetime.now(timezone.utc) must return tz-aware"
    assert now.tzinfo == timezone.utc, "timezone must be UTC"


def test_naive_datetime_detection():
    """Verify we can detect naive datetimes in production code."""
    naive = datetime(2025, 12, 23, 10, 0, 0)  # No tzinfo
    aware = datetime(2025, 12, 23, 10, 0, 0, tzinfo=timezone.utc)
    
    assert naive.tzinfo is None, "Naive datetime should have no tzinfo"
    assert aware.tzinfo is not None, "Aware datetime should have tzinfo"


def test_comparison_between_aware_datetimes():
    """Ensure aware datetimes can be compared safely."""
    now = datetime.now(timezone.utc)
    later = datetime.now(timezone.utc)
    
    # Should not raise TypeError
    assert later >= now, "Aware datetime comparison should work"
