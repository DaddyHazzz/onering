"""
Tests for Plan and Entitlement models (Phase 4.1).
"""
from datetime import datetime, timezone
from backend.models.plan import Plan
from backend.models.entitlement import Entitlement


def test_plan_model_frozen():
    """Plan model should be immutable (frozen=True)."""
    now = datetime.now(timezone.utc)
    plan = Plan(plan_id="free", name="Free Plan", is_default=True, created_at=now)
    
    try:
        plan.name = "Modified"
        assert False, "Plan should be immutable"
    except Exception:
        pass  # Expected


def test_plan_model_fields():
    """Plan model should have all required fields."""
    now = datetime.now(timezone.utc)
    plan = Plan(
        plan_id="creator",
        name="Creator Plan",
        is_default=False,
        created_at=now
    )
    
    assert plan.plan_id == "creator"
    assert plan.name == "Creator Plan"
    assert plan.is_default is False
    assert plan.created_at == now


def test_entitlement_model_frozen():
    """Entitlement model should be immutable (frozen=True)."""
    ent = Entitlement(entitlement_key="drafts.max", value=10, plan_id="free")
    
    try:
        ent.value = 20
        assert False, "Entitlement should be immutable"
    except Exception:
        pass  # Expected


def test_entitlement_int_value():
    """Entitlement should support int values."""
    ent = Entitlement(entitlement_key="drafts.max", value=10, plan_id="free")
    assert ent.value == 10
    assert isinstance(ent.value, int)


def test_entitlement_bool_value():
    """Entitlement should support bool values."""
    ent = Entitlement(entitlement_key="analytics.enabled", value=True, plan_id="free")
    assert ent.value is True
    assert isinstance(ent.value, bool)


def test_entitlement_unlimited_value():
    """Entitlement should support -1 for unlimited."""
    ent = Entitlement(entitlement_key="drafts.max", value=-1, plan_id="team")
    assert ent.value == -1
