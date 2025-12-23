"""
backend/features/plans/service.py

Plan and entitlement service (Phase 4.1).

Handles:
- Plan seeding (free, creator, team)
- User plan assignment
- Entitlement resolution
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Union
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import IntegrityError

from backend.core.database import (
    get_db_session,
    plans,
    plan_entitlements,
    user_plans,
    entitlement_grace_usage,
    create_all_tables,
    apply_schema_upgrades,
)
from backend.models.plan import Plan
from backend.models.entitlement import Entitlement
from backend.models.user_plan import UserPlan
from backend.features.usage.service import get_usage_count


# Default plan configurations
DEFAULT_PLANS = {
    "free": {
        "name": "Free Plan",
        "is_default": True,
        "enforcement_enabled": False,
        "enforcement_grace_count": 0,
        "entitlements": {
            "drafts.max": 10,
            "collaborators.max": 3,
            "segments.max": 20,
            "analytics.enabled": True,
        }
    },
    "creator": {
        "name": "Creator Plan",
        "is_default": False,
        "enforcement_enabled": False,
        "enforcement_grace_count": 0,
        "entitlements": {
            "drafts.max": 50,
            "collaborators.max": 10,
            "segments.max": 100,
            "analytics.enabled": True,
        }
    },
    "team": {
        "name": "Team Plan",
        "is_default": False,
        "enforcement_enabled": False,
        "enforcement_grace_count": 0,
        "entitlements": {
            "drafts.max": -1,  # unlimited
            "collaborators.max": -1,  # unlimited
            "segments.max": -1,  # unlimited
            "analytics.enabled": True,
        }
    }
}


_plan_schema_ready = False


def _ensure_plan_schema() -> None:
    """Ensure plan-related tables and columns exist (idempotent)."""
    global _plan_schema_ready
    if _plan_schema_ready:
        return
    try:
        create_all_tables()
    except Exception:
        # Swallow to preserve backward compatibility in test setups
        pass
    try:
        apply_schema_upgrades()
        _plan_schema_ready = True
    except Exception:
        # If migration fails, we still attempt queries to surface errors
        pass


def seed_plans() -> None:
    """
    Seed default plans into database (idempotent).
    
    Creates free, creator, and team plans with default entitlements.
    Safe to call multiple times.
    """
    _ensure_plan_schema()
    
    now = datetime.now(timezone.utc)
    
    with get_db_session() as session:
        for plan_id, config in DEFAULT_PLANS.items():
            # Check if plan exists (after ensuring schema)
            existing = session.execute(
                select(plans).where(plans.c.plan_id == plan_id)
            ).first()
            
            if not existing:
                # Insert plan
                session.execute(
                    insert(plans).values(
                        plan_id=plan_id,
                        name=config["name"],
                        is_default=config["is_default"],
                        enforcement_enabled=config.get("enforcement_enabled", False),
                        enforcement_grace_count=config.get("enforcement_grace_count", 0),
                        created_at=now
                    )
                )
                
                # Insert entitlements
                for key, value in config["entitlements"].items():
                    session.execute(
                        insert(plan_entitlements).values(
                            plan_id=plan_id,
                            entitlement_key=key,
                            value=value,
                            created_at=now
                        )
                    )


def get_default_plan() -> Optional[Plan]:
    """Get the default plan (typically 'free')."""
    _ensure_plan_schema()
    with get_db_session() as session:
        row = session.execute(
            select(plans).where(plans.c.is_default == True)
        ).first()
        
        if not row:
            return None
        
        return Plan(
            plan_id=row.plan_id,
            name=row.name,
            is_default=row.is_default,
            enforcement_enabled=getattr(row, "enforcement_enabled", False),
            enforcement_grace_count=getattr(row, "enforcement_grace_count", 0),
            created_at=row.created_at
        )


def get_plan(plan_id: str) -> Optional[Plan]:
    """Get plan by ID."""
    _ensure_plan_schema()
    with get_db_session() as session:
        row = session.execute(
            select(plans).where(plans.c.plan_id == plan_id)
        ).first()
        
        if not row:
            return None
        
        return Plan(
            plan_id=row.plan_id,
            name=row.name,
            is_default=row.is_default,
            enforcement_enabled=getattr(row, "enforcement_enabled", False),
            enforcement_grace_count=getattr(row, "enforcement_grace_count", 0),
            created_at=row.created_at
        )


def assign_plan(user_id: str, plan_id: str) -> UserPlan:
    """
    Assign plan to user (creates or updates).
    
    Args:
        user_id: User to assign plan to
        plan_id: Plan to assign
    
    Returns:
        UserPlan instance
    
    Raises:
        ValueError: If plan_id doesn't exist
    """
    # Verify plan exists
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")
    
    now = datetime.now(timezone.utc)
    
    with get_db_session() as session:
        # Check if user already has a plan
        existing = session.execute(
            select(user_plans).where(user_plans.c.user_id == user_id)
        ).first()
        
        if existing:
            if existing.plan_id != plan_id:
                # Reset grace usage when plan changes to avoid carrying prior overages
                session.execute(
                    delete(entitlement_grace_usage).where(
                        entitlement_grace_usage.c.user_id == user_id
                    )
                )
            # Update existing plan assignment
            session.execute(
                update(user_plans)
                .where(user_plans.c.user_id == user_id)
                .values(plan_id=plan_id, assigned_at=now)
            )
        else:
            # Insert new plan assignment
            session.execute(
                insert(user_plans).values(
                    user_id=user_id,
                    plan_id=plan_id,
                    assigned_at=now
                )
            )
        
        return UserPlan(user_id=user_id, plan_id=plan_id, assigned_at=now)


def assign_default_plan(user_id: str) -> UserPlan:
    """
    Assign default plan to user (idempotent).
    
    Args:
        user_id: User to assign default plan to
    
    Returns:
        UserPlan instance
    """
    default_plan = get_default_plan()
    if not default_plan:
        raise RuntimeError("No default plan configured. Run seed_plans() first.")
    
    return assign_plan(user_id, default_plan.plan_id)


def get_user_plan(user_id: str) -> Optional[UserPlan]:
    """Get user's active plan."""
    with get_db_session() as session:
        row = session.execute(
            select(user_plans).where(user_plans.c.user_id == user_id)
        ).first()
        
        if not row:
            return None
        
        return UserPlan(
            user_id=row.user_id,
            plan_id=row.plan_id,
            assigned_at=row.assigned_at
        )


def get_user_entitlements(user_id: str) -> Dict[str, Union[int, bool, str]]:
    """
    Get all entitlements for a user.
    
    Args:
        user_id: User to get entitlements for
    
    Returns:
        Dict mapping entitlement_key to value
        Empty dict if user has no plan or plan has no entitlements
    """
    user_plan = get_user_plan(user_id)
    if not user_plan:
        return {}
    
    with get_db_session() as session:
        rows = session.execute(
            select(plan_entitlements)
            .where(plan_entitlements.c.plan_id == user_plan.plan_id)
        ).all()
        
        return {row.entitlement_key: row.value for row in rows}


def get_user_entitlement(user_id: str, entitlement_key: str) -> Optional[Union[int, bool, str]]:
    """
    Get specific entitlement value for a user.
    
    Args:
        user_id: User to get entitlement for
        entitlement_key: Entitlement to retrieve (e.g., "drafts.max")
    
    Returns:
        Entitlement value or None if not found
    """
    entitlements = get_user_entitlements(user_id)
    return entitlements.get(entitlement_key)


# Enforcement helpers (Phase 4.2)

def is_enforcement_enabled(plan_id: str) -> bool:
    plan = get_plan(plan_id)
    return bool(plan and plan.enforcement_enabled)


def get_grace_remaining(user_id: str, entitlement_key: str) -> int:
    """Return remaining grace for a user/entitlement scoped to their active plan."""
    user_plan = get_user_plan(user_id)
    if not user_plan:
        return 0
    plan = get_plan(user_plan.plan_id)
    if not plan:
        return 0
    with get_db_session() as session:
        row = session.execute(
            select(entitlement_grace_usage)
            .where(entitlement_grace_usage.c.user_id == user_id)
            .where(entitlement_grace_usage.c.plan_id == user_plan.plan_id)
            .where(entitlement_grace_usage.c.entitlement_key == entitlement_key)
        ).first()
        used = int(row.used) if row else 0
        return max(0, int(plan.enforcement_grace_count) - used)


def consume_grace(user_id: str, entitlement_key: str) -> int:
    """Consume one grace unit if available.

    Returns remaining grace after consumption (can be 0). Returns 0 if plan
    has no grace or user has no plan. Safe and idempotent for a single call.
    """
    user_plan = get_user_plan(user_id)
    if not user_plan:
        return 0
    plan = get_plan(user_plan.plan_id)
    if not plan:
        return 0
    with get_db_session() as session:
        row = session.execute(
            select(entitlement_grace_usage)
            .where(entitlement_grace_usage.c.user_id == user_id)
            .where(entitlement_grace_usage.c.plan_id == user_plan.plan_id)
            .where(entitlement_grace_usage.c.entitlement_key == entitlement_key)
        ).first()
        used = int(row.used) if row else 0
        if used >= int(plan.enforcement_grace_count):
            return 0
        if row:
            session.execute(
                update(entitlement_grace_usage)
                .where(entitlement_grace_usage.c.id == row.id)
                .values(used=used + 1)
            )
        else:
            session.execute(
                insert(entitlement_grace_usage).values(
                    user_id=user_id,
                    plan_id=user_plan.plan_id,
                    entitlement_key=entitlement_key,
                    used=1,
                )
            )
        return max(0, int(plan.enforcement_grace_count) - (used + 1))
