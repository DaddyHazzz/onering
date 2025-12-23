"""
backend/features/entitlements/service.py

Entitlement check + enforcement service (Phase 4.2).

Handles:
- Entitlement verification (Phase 4.1 compatibility)
- Hard enforcement with per-entitlement grace and overrides
- Structured logs only (no metrics backend yet)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, Tuple
import logging
from sqlalchemy import select, insert, delete

from backend.core.database import get_db_session, entitlement_overrides
from backend.core.errors import QuotaExceededError
from backend.features.plans.service import (
    get_user_entitlement,
    get_user_plan,
    get_plan,
    get_grace_remaining,
    consume_grace,
)
from backend.features.usage.service import get_usage_count


logger = logging.getLogger(__name__)

# Explicit mapping from entitlement_key to usage_key for hard enforcement
# This ensures consistency across all entitlement checks.
ENTITLEMENT_USAGE_KEY_MAP = {
    "drafts.max": "drafts.created",
    "collaborators.max": "collaborators.added",
    "segments.max": "segments.appended",
}


def _get_usage_key(entitlement_key: str, explicit_usage_key: Optional[str] = None) -> str:
    """Resolve usage_key for an entitlement_key.
    
    Args:
        entitlement_key: The entitlement key (e.g., 'drafts.max')
        explicit_usage_key: If provided, override the mapping
        
    Returns:
        The usage_key to query against usage_events table
        
    Raises:
        ValueError: If entitlement_key is not in the mapping and explicit_usage_key not provided
    """
    if explicit_usage_key:
        return explicit_usage_key
    
    if entitlement_key in ENTITLEMENT_USAGE_KEY_MAP:
        return ENTITLEMENT_USAGE_KEY_MAP[entitlement_key]
    
    # Fallback: simple transformation (but log a warning for unmapped keys)
    fallback = entitlement_key.replace(".max", ".created")
    logger.warning(
        "[entitlements] unmapped entitlement_key, using fallback",
        extra={
            "entitlement_key": entitlement_key,
            "fallback_usage_key": fallback,
        },
    )
    return fallback


class EntitlementResult(str, Enum):
    """Result of legacy entitlement check (Phase 4.1 compatibility)."""
    ALLOWED = "ALLOWED"
    WOULD_EXCEED = "WOULD_EXCEED"
    DISALLOWED = "DISALLOWED"


class EnforcementStatus(str, Enum):
    """Outcome of enforcement decision."""
    ALLOW = "ALLOW"
    ALLOW_WITH_GRACE = "ALLOW_WITH_GRACE"
    WARN_ONLY = "WARN_ONLY"
    BLOCK = "BLOCK"
    DISALLOWED = "DISALLOWED"


@dataclass(frozen=True)
class EnforcementDecision:
    status: EnforcementStatus
    entitlement_value: Any
    current_usage: Optional[int]
    remaining: Optional[Any]
    grace_remaining: int
    plan_id: Optional[str]
    override_applied: bool


def _normalize_now(now: Optional[Any]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if getattr(now, "tzinfo", None) is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _resolve_effective_entitlement(
    user_id: str, entitlement_key: str, now: Optional[Any] = None
) -> Tuple[Optional[Any], bool]:
    """Return (entitlement_value, override_applied)."""
    normalized_now = _normalize_now(now)
    with get_db_session() as session:
        row = session.execute(
            select(entitlement_overrides)
            .where(entitlement_overrides.c.user_id == user_id)
            .where(entitlement_overrides.c.entitlement_key == entitlement_key)
        ).first()
        if row and (row.expires_at is None or row.expires_at > normalized_now):
            return row.override_value, True
    return get_user_entitlement(user_id, entitlement_key), False


def set_override(
    user_id: str,
    entitlement_key: str,
    override_value: Any,
    *,
    expires_at: Optional[datetime] = None,
    created_by: Optional[str] = None,
) -> None:
    """Upsert an entitlement override (support escape hatch)."""
    with get_db_session() as session:
        session.execute(
            delete(entitlement_overrides)
            .where(entitlement_overrides.c.user_id == user_id)
            .where(entitlement_overrides.c.entitlement_key == entitlement_key)
        )
        session.execute(
            insert(entitlement_overrides).values(
                user_id=user_id,
                entitlement_key=entitlement_key,
                override_value=override_value,
                expires_at=expires_at,
                created_by=created_by,
            )
        )


def clear_override(user_id: str, entitlement_key: str) -> None:
    with get_db_session() as session:
        session.execute(
            delete(entitlement_overrides)
            .where(entitlement_overrides.c.user_id == user_id)
            .where(entitlement_overrides.c.entitlement_key == entitlement_key)
        )


def check_entitlement(
    user_id: str,
    entitlement_key: str,
    requested: int = 1,
    usage_key: Optional[str] = None,
    now: Optional[Any] = None,
    window_days: Optional[int] = None
) -> EntitlementResult:
    """Phase 4.1-compatible check (no blocking, no grace consumption)."""
    entitlement_value, _ = _resolve_effective_entitlement(user_id, entitlement_key, now)

    if entitlement_value is None:
        logger.warning(
            "[entitlement] DISALLOWED",
            extra={
                "user_id": user_id,
                "entitlement_key": entitlement_key,
                "reason": "entitlement not found",
            },
        )
        return EntitlementResult.DISALLOWED

    if isinstance(entitlement_value, bool):
        if entitlement_value:
            return EntitlementResult.ALLOWED
        logger.warning(
            "[entitlement] DISALLOWED",
            extra={"user_id": user_id, "entitlement_key": entitlement_key, "entitlement_value": False},
        )
        return EntitlementResult.DISALLOWED

    if isinstance(entitlement_value, int):
        if entitlement_value == -1:
            return EntitlementResult.ALLOWED

        use_key = _get_usage_key(entitlement_key, usage_key)
        current_usage = get_usage_count(user_id, use_key, now=now, window_days=window_days)
        if current_usage + requested > entitlement_value:
            logger.warning(
                "[entitlement] WOULD_EXCEED",
                extra={
                    "user_id": user_id,
                    "entitlement_key": entitlement_key,
                    "entitlement_value": entitlement_value,
                    "current_usage": current_usage,
                    "requested": requested,
                    "would_exceed_by": (current_usage + requested) - entitlement_value,
                },
            )
            return EntitlementResult.WOULD_EXCEED

        logger.info(
            "[entitlement] ALLOWED",
            extra={
                "user_id": user_id,
                "entitlement_key": entitlement_key,
                "entitlement_value": entitlement_value,
                "current_usage": current_usage,
                "requested": requested,
                "remaining": entitlement_value - (current_usage + requested),
            },
        )
        return EntitlementResult.ALLOWED

    logger.warning(
        "[entitlement] DISALLOWED",
        extra={
            "user_id": user_id,
            "entitlement_key": entitlement_key,
            "reason": f"unsupported entitlement type: {type(entitlement_value)}",
        },
    )
    return EntitlementResult.DISALLOWED


def get_entitlement_metadata(
    user_id: str,
    entitlement_key: str,
    usage_key: Optional[str] = None,
    now: Optional[Any] = None,
    window_days: Optional[int] = None
) -> Dict[str, Any]:
    entitlement_value, override_applied = _resolve_effective_entitlement(user_id, entitlement_key, now)

    if entitlement_value is None:
        return {"status": "disabled", "entitlement_value": None}

    if isinstance(entitlement_value, bool):
        return {
            "status": "ok" if entitlement_value else "disabled",
            "entitlement_value": entitlement_value,
            "override_applied": override_applied,
        }

    if isinstance(entitlement_value, int):
        if entitlement_value == -1:
            return {
                "status": "ok",
                "entitlement_value": "unlimited",
                "current_usage": 0,
                "remaining": "unlimited",
                "override_applied": override_applied,
            }

        use_key = _get_usage_key(entitlement_key, usage_key)
        current_usage = get_usage_count(user_id, use_key, now=now, window_days=window_days)
        remaining = max(0, entitlement_value - current_usage)

        if current_usage >= entitlement_value:
            status = "at_limit"
        elif current_usage >= entitlement_value * 0.8:
            status = "approaching_limit"
        else:
            status = "ok"

        return {
            "status": status,
            "entitlement_value": entitlement_value,
            "current_usage": current_usage,
            "remaining": remaining,
            "override_applied": override_applied,
        }

    return {"status": "disabled", "entitlement_value": None, "override_applied": override_applied}


def enforce_entitlement(
    user_id: str,
    entitlement_key: str,
    *,
    requested: int = 1,
    usage_key: Optional[str] = None,
    now: Optional[Any] = None,
    window_days: Optional[int] = None,
) -> EnforcementDecision:
    """Hard enforcement with per-entitlement grace and overrides.

    Raises QuotaExceededError when enforcement is enabled and grace is exhausted.
    """
    normalized_now = _normalize_now(now)
    user_plan = get_user_plan(user_id)
    plan = get_plan(user_plan.plan_id) if user_plan else None
    entitlement_value, override_applied = _resolve_effective_entitlement(user_id, entitlement_key, normalized_now)

    if entitlement_value is None:
        logger.warning(
            "[enforcement] DISALLOWED",
            extra={"user_id": user_id, "entitlement_key": entitlement_key, "plan_id": getattr(plan, "plan_id", None)},
        )
        return EnforcementDecision(
            status=EnforcementStatus.DISALLOWED,
            entitlement_value=None,
            current_usage=None,
            remaining=None,
            grace_remaining=0,
            plan_id=getattr(plan, "plan_id", None),
            override_applied=override_applied,
        )

    if isinstance(entitlement_value, bool):
        if entitlement_value:
            return EnforcementDecision(
                status=EnforcementStatus.ALLOW,
                entitlement_value=True,
                current_usage=None,
                remaining=None,
                grace_remaining=get_grace_remaining(user_id, entitlement_key),
                plan_id=getattr(plan, "plan_id", None),
                override_applied=override_applied,
            )
        logger.warning(
            "[enforcement] DISALLOWED",
            extra={"user_id": user_id, "entitlement_key": entitlement_key, "plan_id": getattr(plan, "plan_id", None)},
        )
        return EnforcementDecision(
            status=EnforcementStatus.DISALLOWED,
            entitlement_value=False,
            current_usage=None,
            remaining=None,
            grace_remaining=0,
            plan_id=getattr(plan, "plan_id", None),
            override_applied=override_applied,
        )

    if not isinstance(entitlement_value, int):
        logger.warning(
            "[enforcement] DISALLOWED",
            extra={
                "user_id": user_id,
                "entitlement_key": entitlement_key,
                "plan_id": getattr(plan, "plan_id", None),
                "reason": f"unsupported type: {type(entitlement_value)}",
            },
        )
        return EnforcementDecision(
            status=EnforcementStatus.DISALLOWED,
            entitlement_value=entitlement_value,
            current_usage=None,
            remaining=None,
            grace_remaining=0,
            plan_id=getattr(plan, "plan_id", None),
            override_applied=override_applied,
        )

    # Numeric entitlement
    if entitlement_value == -1:
        return EnforcementDecision(
            status=EnforcementStatus.ALLOW,
            entitlement_value=entitlement_value,
            current_usage=0,
            remaining="unlimited",
            grace_remaining=get_grace_remaining(user_id, entitlement_key),
            plan_id=getattr(plan, "plan_id", None),
            override_applied=override_applied,
        )

    use_key = _get_usage_key(entitlement_key, usage_key)
    current_usage = get_usage_count(user_id, use_key, now=normalized_now, window_days=window_days)
    would_exceed = current_usage + requested > entitlement_value
    remaining = max(0, entitlement_value - (current_usage + requested))
    grace_remaining = get_grace_remaining(user_id, entitlement_key)

    if not plan or not plan.enforcement_enabled:
        status = EnforcementStatus.WARN_ONLY if would_exceed else EnforcementStatus.ALLOW
        logger.warning(
            "[enforcement] WARN_ONLY" if would_exceed else "[enforcement] ALLOW",
            extra={
                "user_id": user_id,
                "plan_id": getattr(plan, "plan_id", None),
                "entitlement_key": entitlement_key,
                "entitlement_value": entitlement_value,
                "current_usage": current_usage,
                "requested": requested,
                "remaining": remaining,
                "grace_remaining": grace_remaining,
                "metric": "enforcement.warned.count" if would_exceed else None,
            },
        )
        return EnforcementDecision(
            status=status,
            entitlement_value=entitlement_value,
            current_usage=current_usage,
            remaining=remaining,
            grace_remaining=grace_remaining,
            plan_id=getattr(plan, "plan_id", None),
            override_applied=override_applied,
        )

    if would_exceed:
        if grace_remaining > 0:
            remaining_after = consume_grace(user_id, entitlement_key)
            logger.warning(
                "[enforcement] ALLOW_WITH_GRACE",
                extra={
                    "user_id": user_id,
                    "plan_id": plan.plan_id,
                    "entitlement_key": entitlement_key,
                    "entitlement_value": entitlement_value,
                    "current_usage": current_usage,
                    "requested": requested,
                    "grace_remaining_after": remaining_after,
                    "metric": "enforcement.warned.count",
                },
            )
            return EnforcementDecision(
                status=EnforcementStatus.ALLOW_WITH_GRACE,
                entitlement_value=entitlement_value,
                current_usage=current_usage,
                remaining=remaining,
                grace_remaining=remaining_after,
                plan_id=plan.plan_id,
                override_applied=override_applied,
            )

        logger.error(
            "[enforcement] BLOCK",
            extra={
                "user_id": user_id,
                "plan_id": plan.plan_id,
                "entitlement_key": entitlement_key,
                "entitlement_value": entitlement_value,
                "current_usage": current_usage,
                "requested": requested,
                "metric": "enforcement.blocked.count",
            },
        )
        raise QuotaExceededError(
            f"Entitlement {entitlement_key} exceeded for user {user_id}",
            code="quota_exceeded",
        )

    return EnforcementDecision(
        status=EnforcementStatus.ALLOW,
        entitlement_value=entitlement_value,
        current_usage=current_usage,
        remaining=remaining,
        grace_remaining=grace_remaining,
        plan_id=plan.plan_id if plan else None,
        override_applied=override_applied,
    )
