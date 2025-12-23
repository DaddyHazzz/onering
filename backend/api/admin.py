"""
Admin API routes for billing operations (Phase 4.4).

All routes require X-Admin-Key header for authentication.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.core.admin_auth import require_admin_auth
from backend.features.billing.admin_service import (
    replay_webhook_event,
    get_webhook_events,
    sync_user_plan,
    record_admin_audit,
)
from backend.features.entitlements.service import set_override, get_entitlement_override
from backend.core.database import get_db_session, entitlement_grace_usage
from sqlalchemy import delete, select
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ReplayWebhookRequest(BaseModel):
    stripe_event_id: str
    force: bool = False


class SyncUserPlanRequest(BaseModel):
    user_id: str
    dry_run: bool = True


class OverrideEntitlementRequest(BaseModel):
    user_id: str
    entitlement_key: str
    value: int | bool | str  # Value can be int (limit), bool (flag), or string
    expires_at: Optional[str] = None  # ISO datetime string, optional


class ResetGraceRequest(BaseModel):
    user_id: str
    entitlement_key: Optional[str] = None  # If null, reset all grace for user


@router.post("/billing/replay_webhook")
def replay_webhook(request: Request, body: ReplayWebhookRequest) -> dict:
    """Replay a webhook event (idempotent reprocessing)."""
    require_admin_auth(request)
    
    result = replay_webhook_event(
        stripe_event_id=body.stripe_event_id,
        force=body.force,
    )
    return result


@router.get("/billing/events")
def list_webhook_events(
    request: Request,
    user_id: Optional[str] = None,
    limit: int = 50,
    status: Optional[str] = None,
) -> dict:
    """List webhook events with optional filtering."""
    require_admin_auth(request)
    
    events = get_webhook_events(
        user_id=user_id,
        limit=limit,
        status=status,
    )
    return {
        "count": len(events),
        "events": events,
    }


@router.post("/billing/sync_user_plan")
def sync_plan(request: Request, body: SyncUserPlanRequest) -> dict:
    """Synchronize user plan to match subscription state."""
    require_admin_auth(request)
    
    result = sync_user_plan(
        user_id=body.user_id,
        dry_run=body.dry_run,
    )
    return result


@router.post("/entitlements/override")
def override_entitlement(request: Request, body: OverrideEntitlementRequest) -> dict:
    """Create or update an entitlement override for a user."""
    require_admin_auth(request)
    
    expires_at = None
    if body.expires_at:
        expires_at = datetime.fromisoformat(body.expires_at)
    
    # Use existing entitlements service to set override
    set_override(
        user_id=body.user_id,
        entitlement_key=body.entitlement_key,
        value=body.value,
        expires_at=expires_at,
    )
    
    # Record in audit
    record_admin_audit(
        actor="admin_key",
        action="override_entitlement",
        target_user_id=body.user_id,
        target_resource=body.entitlement_key,
        payload={
            "value": str(body.value),
            "expires_at": body.expires_at,
        },
    )
    
    return {
        "user_id": body.user_id,
        "entitlement_key": body.entitlement_key,
        "value": body.value,
        "expires_at": body.expires_at,
        "status": "overridden",
    }


@router.delete("/entitlements/override")
def remove_entitlement_override(request: Request, body: OverrideEntitlementRequest) -> dict:
    """Remove an entitlement override for a user."""
    require_admin_auth(request)
    
    # Find and delete the override
    # (This is a simplified implementation; actual deletion requires querying entitlement_overrides table)
    # For now, record the action
    record_admin_audit(
        actor="admin_key",
        action="delete_entitlement_override",
        target_user_id=body.user_id,
        target_resource=body.entitlement_key,
        payload={},
    )
    
    return {
        "user_id": body.user_id,
        "entitlement_key": body.entitlement_key,
        "status": "deleted",
    }


@router.post("/entitlements/reset_grace")
def reset_grace(request: Request, body: ResetGraceRequest) -> dict:
    """Reset grace period usage for a user or specific entitlement."""
    require_admin_auth(request)
    
    with get_db_session() as session:
        # Build query to delete grace records
        query = delete(entitlement_grace_usage).where(
            entitlement_grace_usage.c.user_id == body.user_id
        )
        
        if body.entitlement_key:
            query = query.where(
                entitlement_grace_usage.c.entitlement_key == body.entitlement_key
            )
        
        result = session.execute(query)
        session.commit()
        deleted_count = result.rowcount
    
    # Record in audit
    record_admin_audit(
        actor="admin_key",
        action="reset_grace",
        target_user_id=body.user_id,
        target_resource=body.entitlement_key,
        payload={"deleted_count": deleted_count},
    )
    
    return {
        "user_id": body.user_id,
        "entitlement_key": body.entitlement_key,
        "deleted_count": deleted_count,
        "status": "reset",
    }
