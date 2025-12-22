"""
backend/features/entitlements/service.py

Entitlement check service (Phase 4.1).

Handles:
- Entitlement verification
- Soft enforcement (log warnings, don't block)
- Structured logging for future billing
"""

from enum import Enum
from typing import Optional, Dict, Any
import logging

from backend.features.plans.service import get_user_entitlement
from backend.features.usage.service import get_usage_count


logger = logging.getLogger(__name__)


class EntitlementResult(str, Enum):
    """Result of entitlement check."""
    ALLOWED = "ALLOWED"
    WOULD_EXCEED = "WOULD_EXCEED"
    DISALLOWED = "DISALLOWED"


def check_entitlement(
    user_id: str,
    entitlement_key: str,
    requested: int = 1,
    usage_key: Optional[str] = None,
    now: Optional[Any] = None,
    window_days: Optional[int] = None
) -> EntitlementResult:
    """
    Check if user is allowed to perform action under their plan.
    
    Phase 4.1: Logs warnings but NEVER blocks actions.
    Phase 4.2: Will optionally raise ValidationError when WOULD_EXCEED.
    
    Args:
        user_id: User to check
        entitlement_key: Entitlement to check (e.g., "drafts.max")
        requested: How many units user wants to use (default 1)
        usage_key: Usage key to count (defaults to entitlement_key without .max suffix)
        now: Fixed timestamp for deterministic usage queries
        window_days: Rolling window for usage (None = all-time)
    
    Returns:
        EntitlementResult:
        - ALLOWED: User can proceed
        - WOULD_EXCEED: User would exceed limit (Phase 4.1: warning only)
        - DISALLOWED: Plan doesn't have this entitlement
    """
    # Get entitlement value
    entitlement_value = get_user_entitlement(user_id, entitlement_key)
    
    if entitlement_value is None:
        # Plan doesn't have this entitlement
        logger.warning(
            "[entitlement] DISALLOWED",
            extra={
                "user_id": user_id,
                "entitlement_key": entitlement_key,
                "reason": "entitlement not found in plan"
            }
        )
        return EntitlementResult.DISALLOWED
    
    # Boolean entitlements: check if enabled
    if isinstance(entitlement_value, bool):
        if entitlement_value:
            return EntitlementResult.ALLOWED
        else:
            logger.warning(
                "[entitlement] DISALLOWED",
                extra={
                    "user_id": user_id,
                    "entitlement_key": entitlement_key,
                    "entitlement_value": False
                }
            )
            return EntitlementResult.DISALLOWED
    
    # Numeric entitlements: check against usage
    if isinstance(entitlement_value, int):
        # -1 means unlimited
        if entitlement_value == -1:
            return EntitlementResult.ALLOWED
        
        # Get current usage
        if usage_key is None:
            # Default: remove .max suffix from entitlement_key
            usage_key = entitlement_key.replace(".max", ".created")
            if usage_key == entitlement_key:  # No .max suffix found
                usage_key = entitlement_key
        
        current_usage = get_usage_count(user_id, usage_key, now=now, window_days=window_days)
        
        # Check if requested would exceed limit
        if current_usage + requested > entitlement_value:
            logger.warning(
                "[entitlement] WOULD_EXCEED",
                extra={
                    "user_id": user_id,
                    "entitlement_key": entitlement_key,
                    "entitlement_value": entitlement_value,
                    "current_usage": current_usage,
                    "requested": requested,
                    "would_exceed_by": (current_usage + requested) - entitlement_value
                }
            )
            return EntitlementResult.WOULD_EXCEED
        
        # Allowed
        logger.info(
            "[entitlement] ALLOWED",
            extra={
                "user_id": user_id,
                "entitlement_key": entitlement_key,
                "entitlement_value": entitlement_value,
                "current_usage": current_usage,
                "requested": requested,
                "remaining": entitlement_value - (current_usage + requested)
            }
        )
        return EntitlementResult.ALLOWED
    
    # Unknown entitlement value type
    logger.warning(
        "[entitlement] DISALLOWED",
        extra={
            "user_id": user_id,
            "entitlement_key": entitlement_key,
            "reason": f"unsupported entitlement type: {type(entitlement_value)}"
        }
    )
    return EntitlementResult.DISALLOWED


def get_entitlement_metadata(
    user_id: str,
    entitlement_key: str,
    usage_key: Optional[str] = None,
    now: Optional[Any] = None,
    window_days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get entitlement metadata for API responses.
    
    Returns:
        Dict with:
        - entitlement_value: Limit or feature flag
        - current_usage: Current usage count (if numeric)
        - remaining: Units remaining (if numeric)
        - status: "ok" | "approaching_limit" | "at_limit" | "disabled"
    """
    entitlement_value = get_user_entitlement(user_id, entitlement_key)
    
    if entitlement_value is None:
        return {"status": "disabled", "entitlement_value": None}
    
    if isinstance(entitlement_value, bool):
        return {
            "status": "ok" if entitlement_value else "disabled",
            "entitlement_value": entitlement_value
        }
    
    if isinstance(entitlement_value, int):
        if entitlement_value == -1:
            return {
                "status": "ok",
                "entitlement_value": "unlimited",
                "current_usage": 0,
                "remaining": "unlimited"
            }
        
        # Get usage
        if usage_key is None:
            usage_key = entitlement_key.replace(".max", ".created")
        
        current_usage = get_usage_count(user_id, usage_key, now=now, window_days=window_days)
        remaining = max(0, entitlement_value - current_usage)
        
        # Determine status
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
            "remaining": remaining
        }
    
    return {"status": "disabled", "entitlement_value": None}
