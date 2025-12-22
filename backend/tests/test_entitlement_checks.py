"""
Tests for entitlement checks (Phase 4.1).
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from backend.features.entitlements.service import (
    check_entitlement,
    EntitlementResult,
    get_entitlement_metadata,
)
from backend.features.plans.service import seed_plans, assign_plan
from backend.features.usage.service import emit_usage_event
from backend.core.database import check_connection


# Skip all tests if no database connection
pytestmark = pytest.mark.skipif(
    not check_connection(),
    reason="Database not available"
)


def test_check_entitlement_allowed():
    """Should return ALLOWED when under limit."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")  # free plan has drafts.max = 10
    
    # User has 0 drafts, can create 1
    result = check_entitlement(user_id, "drafts.max", requested=1)
    assert result == EntitlementResult.ALLOWED


def test_check_entitlement_would_exceed():
    """Should return WOULD_EXCEED when at limit."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")  # free plan has drafts.max = 10
    now = datetime.now(timezone.utc)
    
    # Emit 10 drafts.created events (at limit)
    for i in range(10):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))
    
    # Try to create one more
    result = check_entitlement(user_id, "drafts.max", requested=1, now=now + timedelta(seconds=11))
    assert result == EntitlementResult.WOULD_EXCEED


def test_check_entitlement_unlimited():
    """Team plan with unlimited (-1) should always return ALLOWED."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "team")  # team plan has drafts.max = -1 (unlimited)
    now = datetime.now(timezone.utc)
    
    # Emit 1000 drafts
    for i in range(1000):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))
    
    # Still allowed
    result = check_entitlement(user_id, "drafts.max", requested=1, now=now + timedelta(seconds=1001))
    assert result == EntitlementResult.ALLOWED


def test_check_entitlement_bool_enabled():
    """Boolean entitlement (true) should return ALLOWED."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")  # free plan has analytics.enabled = true
    
    result = check_entitlement(user_id, "analytics.enabled")
    assert result == EntitlementResult.ALLOWED


def test_check_entitlement_no_plan():
    """User with no plan should return DISALLOWED."""
    seed_plans()
    user_id = f"user-{uuid4()}"
    # No plan assigned
    
    result = check_entitlement(user_id, "drafts.max", requested=1)
    assert result == EntitlementResult.DISALLOWED


def test_check_entitlement_deterministic():
    """Same user + same usage + same now = same result."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    now = datetime.now(timezone.utc)
    
    emit_usage_event(user_id, "drafts.created", now)
    
    result1 = check_entitlement(user_id, "drafts.max", requested=1, now=now + timedelta(seconds=1))
    result2 = check_entitlement(user_id, "drafts.max", requested=1, now=now + timedelta(seconds=1))
    
    assert result1 == result2


def test_get_entitlement_metadata_ok():
    """Should return metadata with status=ok when under limit."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    
    metadata = get_entitlement_metadata(user_id, "drafts.max")
    
    assert metadata["status"] == "ok"
    assert metadata["entitlement_value"] == 10
    assert metadata["current_usage"] == 0
    assert metadata["remaining"] == 10


def test_get_entitlement_metadata_approaching_limit():
    """Should return approaching_limit when usage >= 80%."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")  # drafts.max = 10
    now = datetime.now(timezone.utc)
    
    # Emit 8 drafts (80% of limit)
    for i in range(8):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))
    
    metadata = get_entitlement_metadata(user_id, "drafts.max", now=now + timedelta(seconds=10))
    
    assert metadata["status"] == "approaching_limit"
    assert metadata["current_usage"] == 8
    assert metadata["remaining"] == 2


def test_get_entitlement_metadata_at_limit():
    """Should return at_limit when usage = entitlement_value."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")  # drafts.max = 10
    now = datetime.now(timezone.utc)
    
    # Emit 10 drafts (at limit)
    for i in range(10):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))
    
    metadata = get_entitlement_metadata(user_id, "drafts.max", now=now + timedelta(seconds=11))
    
    assert metadata["status"] == "at_limit"
    assert metadata["current_usage"] == 10
    assert metadata["remaining"] == 0


def test_get_entitlement_metadata_unlimited():
    """Team plan should show unlimited."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "team")
    
    metadata = get_entitlement_metadata(user_id, "drafts.max")
    
    assert metadata["status"] == "ok"
    assert metadata["entitlement_value"] == "unlimited"
    assert metadata["remaining"] == "unlimited"


def test_phase_4_1_does_not_block_actions():
    """Phase 4.1: Entitlement checks should never block actions."""
    from backend.features.users.service import get_or_create_user
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    now = datetime.now(timezone.utc)
    
    # Emit 20 drafts (way over limit of 10)
    for i in range(20):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))
    
    # Check should return WOULD_EXCEED but not raise exception
    result = check_entitlement(user_id, "drafts.max", requested=1, now=now + timedelta(seconds=21))
    assert result == EntitlementResult.WOULD_EXCEED
    # No exception raised = test passes
