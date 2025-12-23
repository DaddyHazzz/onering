import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import update, select

from backend.core.database import check_connection, get_db_session, plans
from backend.core.errors import QuotaExceededError
from backend.features.entitlements.service import (
    EnforcementStatus,
    enforce_entitlement,
    set_override,
    clear_override,
)
from backend.features.plans.service import seed_plans, assign_plan, get_grace_remaining
from backend.features.usage.service import emit_usage_event, get_usage_count
from backend.features.users.service import get_or_create_user
from backend.models.collab import CollabDraftRequest
from backend.features.collaboration.service import create_draft


# Skip all tests if no database connection
pytestmark = pytest.mark.skipif(
    not check_connection(),
    reason="Database not available",
)


def _enable_enforcement(plan_id: str, grace_count: int) -> None:
    with get_db_session() as session:
        session.execute(
            update(plans)
            .where(plans.c.plan_id == plan_id)
            .values(enforcement_enabled=True, enforcement_grace_count=grace_count)
        )


def _restore_plan(plan_id: str, enabled: bool, grace: int) -> None:
    with get_db_session() as session:
        session.execute(
            update(plans)
            .where(plans.c.plan_id == plan_id)
            .values(enforcement_enabled=enabled, enforcement_grace_count=grace)
        )


@pytest.fixture
def reset_free_plan():
    seed_plans()
    with get_db_session() as session:
        row = session.execute(
            select(plans.c.enforcement_enabled, plans.c.enforcement_grace_count)
            .where(plans.c.plan_id == "free")
        ).first()
    yield
    if row:
        _restore_plan("free", row.enforcement_enabled, row.enforcement_grace_count)


def test_grace_allows_then_blocks(reset_free_plan):
    seed_plans()
    _enable_enforcement("free", grace_count=2)

    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    now = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Emit usage up to limit (free.drafts.max = 10)
    for i in range(10):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))

    decision1 = enforce_entitlement(
        user_id,
        "drafts.max",
        requested=1,
        usage_key="drafts.created",
        now=now + timedelta(seconds=11),
    )
    assert decision1.status == EnforcementStatus.ALLOW_WITH_GRACE
    assert decision1.grace_remaining == 1

    decision2 = enforce_entitlement(
        user_id,
        "drafts.max",
        requested=1,
        usage_key="drafts.created",
        now=now + timedelta(seconds=12),
    )
    assert decision2.status == EnforcementStatus.ALLOW_WITH_GRACE
    assert decision2.grace_remaining == 0

    with pytest.raises(QuotaExceededError):
        enforce_entitlement(
            user_id,
            "drafts.max",
            requested=1,
            usage_key="drafts.created",
            now=now + timedelta(seconds=13),
        )


def test_override_unlimited_allows_over_limit(reset_free_plan):
    seed_plans()
    _enable_enforcement("free", grace_count=0)

    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    set_override(user_id, "drafts.max", -1, created_by="test")

    now = datetime.now(timezone.utc) - timedelta(minutes=1)
    for i in range(25):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))

    decision = enforce_entitlement(
        user_id,
        "drafts.max",
        requested=1,
        usage_key="drafts.created",
        now=now + timedelta(seconds=26),
    )
    clear_override(user_id, "drafts.max")
    assert decision.status == EnforcementStatus.ALLOW
    assert decision.override_applied is True
    assert decision.remaining == "unlimited" or decision.entitlement_value == -1


def test_create_draft_blocks_and_emits_no_usage(reset_free_plan):
    seed_plans()
    _enable_enforcement("free", grace_count=0)

    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    assign_plan(user_id, "free")
    now = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Reach limit
    for i in range(10):
        emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=i))

    draft_request = CollabDraftRequest(title="Blocked draft", platform="X")

    with pytest.raises(QuotaExceededError):
        create_draft(user_id, draft_request)

    # Usage should remain unchanged because enforcement blocked before emitting usage
    usage_after = get_usage_count(user_id, "drafts.created", now=now + timedelta(seconds=20))
    assert usage_after == 10
    # Grace remains zero since plan had none
    assert get_grace_remaining(user_id, "drafts.max") == 0
