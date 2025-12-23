"""
Test Phase 4.2 QuotaExceededError contract.

Ensures QuotaExceededError is raised with proper payload when enforcement
blocks, and that the error contract is stable for API clients.
"""
import pytest
from datetime import datetime, timezone
from backend.core.errors import QuotaExceededError
from backend.core.database import create_all_tables, reset_database, get_db_session, users
from sqlalchemy import insert
from backend.features.plans.service import seed_plans, assign_plan
from backend.features.entitlements.service import enforce_entitlement, set_override
from backend.features.usage.service import emit_usage_event


def create_test_user(user_id: str):
    """Helper to create a test user."""
    with get_db_session() as session:
        session.execute(
            insert(users).values(
                user_id=user_id,
                display_name=f"Test User {user_id}",
                status="active",
            )
        )


@pytest.fixture(scope="function", autouse=True)
def reset_db_and_seed():
    """Reset DB and seed plans before each test."""
    reset_database()
    seed_plans()
    yield


class TestQuotaExceededErrorContract:
    """Verify QuotaExceededError has stable, useful contract."""

    def test_quota_exceeded_error_has_status_403(self):
        """Verify QuotaExceededError returns HTTP 403."""
        error = QuotaExceededError(
            message="Test error",
            code="quota_exceeded",
        )
        assert error.status_code == 403

    def test_quota_exceeded_error_code_is_quota_exceeded(self):
        """Verify error code is 'quota_exceeded'."""
        error = QuotaExceededError(
            message="Test error",
            code="quota_exceeded",
        )
        assert error.code == "quota_exceeded"

    def test_enforce_entitlement_raises_quota_exceeded_when_blocked(self):
        """Verify enforce_entitlement raises QuotaExceededError on BLOCK."""
        user_id = "test_user_block"
        now = datetime.now(timezone.utc)
        
        # Create user first
        create_test_user(user_id)

        # Assign free plan with enforcement enabled
        assign_plan(user_id, "free")
        from backend.features.plans.service import get_plan
        free_plan = get_plan("free")
        
        # Enable enforcement with grace_count=0 (no grace)
        from backend.core.database import get_db_session, plans
        from sqlalchemy import update
        with get_db_session() as session:
            session.execute(
                update(plans)
                .where(plans.c.plan_id == "free")
                .values(enforcement_enabled=True, enforcement_grace_count=0)
            )
        
        # Emit usage events to exceed limit (drafts.max=10 on free plan)
        for i in range(10):
            emit_usage_event(
                user_id=user_id,
                usage_key="drafts.created",
                occurred_at=now,
            )
        
        # Next request should raise QuotaExceededError
        with pytest.raises(QuotaExceededError) as exc_info:
            enforce_entitlement(
                user_id,
                "drafts.max",
                requested=1,
                now=now,
            )
        
        error = exc_info.value
        assert error.status_code == 403
        assert error.code == "quota_exceeded"

    def test_quota_exceeded_error_message_includes_entitlement_key(self):
        """Verify error message includes which entitlement was exceeded."""
        user_id = "test_user_msg"
        now = datetime.now(timezone.utc)
        
        # Create user first
        create_test_user(user_id)

        assign_plan(user_id, "free")
        from backend.core.database import get_db_session, plans
        from sqlalchemy import update
        with get_db_session() as session:
            session.execute(
                update(plans)
                .where(plans.c.plan_id == "free")
                .values(enforcement_enabled=True, enforcement_grace_count=0)
            )
        
        for i in range(10):
            emit_usage_event(
                user_id=user_id,
                usage_key="drafts.created",
                occurred_at=now,
            )
        
        with pytest.raises(QuotaExceededError) as exc_info:
            enforce_entitlement(
                user_id,
                "drafts.max",
                requested=1,
                now=now,
            )
        
        assert "drafts.max" in str(exc_info.value)

    def test_override_prevents_quota_exceeded_error(self):
        """Verify set_override allows bypass of enforcement block."""
        user_id = "test_user_override"
        now = datetime.now(timezone.utc)
        
        # Create user first
        create_test_user(user_id)

        assign_plan(user_id, "free")
        from backend.core.database import get_db_session, plans
        from sqlalchemy import update
        with get_db_session() as session:
            session.execute(
                update(plans)
                .where(plans.c.plan_id == "free")
                .values(enforcement_enabled=True, enforcement_grace_count=0)
            )
        
        for i in range(10):
            emit_usage_event(
                user_id=user_id,
                usage_key="drafts.created",
                occurred_at=now,
            )
        
        # Set unlimited override
        set_override(user_id, "drafts.max", -1)
        
        # Should NOT raise
        decision = enforce_entitlement(
            user_id,
            "drafts.max",
            requested=1,
            now=now,
        )
        assert decision.override_applied is True
        assert decision.status.value == "ALLOW"
