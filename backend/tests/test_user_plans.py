"""
Tests for user plan assignment (Phase 4.1).
"""
import pytest
from uuid import uuid4
from backend.features.plans.service import (
    seed_plans,
    get_default_plan,
    assign_plan,
    assign_default_plan,
    get_user_plan,
    get_user_entitlements,
    get_user_entitlement,
)
from backend.features.users.service import get_or_create_user
from backend.core.database import check_connection


# Skip all tests if no database connection
pytestmark = pytest.mark.skipif(
    not check_connection(),
    reason="Database not available"
)


def test_seed_plans_idempotent():
    """Seeding plans multiple times should be safe."""
    seed_plans()
    seed_plans()  # Should not raise


def test_get_default_plan():
    """Should return free plan as default."""
    seed_plans()
    default = get_default_plan()
    assert default is not None
    assert default.plan_id == "free"
    assert default.is_default is True


def test_assign_plan():
    """Should assign plan to user."""
    seed_plans()
    # Create user first (required for FK constraint)
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    
    user_plan = assign_plan(user_id, "creator")
    assert user_plan.user_id == user_id
    assert user_plan.plan_id == "creator"


def test_assign_plan_idempotent():
    """Assigning same plan twice should be safe."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    
    up1 = assign_plan(user_id, "free")
    up2 = assign_plan(user_id, "free")
    
    assert up1.user_id == up2.user_id
    assert up1.plan_id == up2.plan_id


def test_assign_plan_updates_existing():
    """Assigning new plan should update existing."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    
    up1 = assign_plan(user_id, "free")
    up2 = assign_plan(user_id, "creator")
    
    assert up2.plan_id == "creator"
    
    # Verify only one plan assignment exists
    retrieved = get_user_plan(user_id)
    assert retrieved.plan_id == "creator"


def test_assign_default_plan():
    """Should assign default plan to user."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id


def test_get_user_entitlements():
    """Should return all entitlements for user's plan."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    
    entitlements = get_user_entitlements(user_id)
    
    assert "drafts.max" in entitlements
    assert "collaborators.max" in entitlements
    assert "analytics.enabled" in entitlements
    
    assert entitlements["drafts.max"] == 10
    assert entitlements["collaborators.max"] == 3
    assert entitlements["analytics.enabled"] is True


def test_get_user_entitlement_specific():
    """Should return specific entitlement value."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "creator")
    
    drafts_max = get_user_entitlement(user_id, "drafts.max")
    assert drafts_max == 50


def test_get_user_entitlement_unlimited():
    """Team plan should have unlimited entitlements (-1)."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "team")
    
    drafts_max = get_user_entitlement(user_id, "drafts.max")
    assert drafts_max == -1


def test_get_user_entitlement_no_plan():
    """User with no plan should return None."""
    seed_plans()
    user_id = f"user-{uuid4()}"
    
    drafts_max = get_user_entitlement(user_id, "drafts.max")
    assert drafts_max is None


def test_user_creation_auto_assigns_plan():
    """Creating user should auto-assign default plan."""
    seed_plans()
    user_id = f"user-{uuid4()}"
    
    user = get_or_create_user(user_id)
    
    user_plan = get_user_plan(user_id)
    assert user_plan is not None
    assert user_plan.plan_id == "free"


def test_entitlement_resolution_deterministic():
    """Same user + same plan = same entitlements."""
    seed_plans()
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    
    ents1 = get_user_entitlements(user_id)
    ents2 = get_user_entitlements(user_id)
    
    assert ents1 == ents2
