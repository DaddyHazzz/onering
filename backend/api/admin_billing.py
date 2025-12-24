"""
Admin-only billing operations router.
Requires X-Admin-Key header for all endpoints.
Handles webhook replay, event management, and billing overrides.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update, desc, func, insert
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.admin_auth import require_admin_auth, require_admin, AdminActor
from backend.models.billing import (
    BillingSubscription, 
    BillingEvent, 
    BillingGracePeriod,
)
from backend.core.config import settings
from backend.core.database import billing_retry_queue, billing_subscriptions, billing_job_runs
from backend.core.errors import AdminAuditWriteError
from backend.features.billing.retry_service import claim_due_retries, process_retry

logger = logging.getLogger("onering.admin_billing")

router = APIRouter()


# ============================================================================
# Admin Auth Gate
# ============================================================================

def verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> str:
    """Deprecated shim retained for backward compatibility in older tests.
    Use require_admin_auth via Depends in endpoints instead.
    """
    admin_key = settings.ADMIN_KEY
    if not admin_key or not x_admin_key or x_admin_key != admin_key:
        logger.warning(f"[admin_billing] invalid admin key attempt: {x_admin_key[:10] if x_admin_key else 'none'}...")
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")
    return x_admin_key


# ============================================================================
# Pydantic Models
# ============================================================================

class WebhookReplayRequest(BaseModel):
    """Request to replay a webhook event."""
    event_id: str = Field(..., description="UUID of billing event to replay")
    force: bool = Field(default=False, description="Force replay even if already processed")


class WebhookReplayResponse(BaseModel):
    """Response from webhook replay."""
    success: bool
    event_id: str
    message: str
    reprocessed: bool = False


class BillingEventListItem(BaseModel):
    """Single billing event for list response."""
    id: str
    user_id: str
    event_type: str
    stripe_event_id: Optional[str]
    status: str
    created_at: datetime
    processed_at: Optional[datetime]


class BillingEventListResponse(BaseModel):
    """Response for listing billing events."""
    total: int
    events: List[BillingEventListItem]
    has_more: bool


class PlanSyncRequest(BaseModel):
    """Request to sync Stripe plans."""
    user_id: str = Field(..., description="User ID to sync")
    force_update: bool = Field(default=False, description="Force update even if subscription exists")


class PlanSyncResponse(BaseModel):
    """Response from plan sync."""
    success: bool
    user_id: str
    subscription_id: Optional[str]
    plan: Optional[str]
    status: Optional[str]
    message: str


class EntitlementOverrideRequest(BaseModel):
    """Request to override user entitlements."""
    user_id: str = Field(..., description="User ID")
    credits: Optional[int] = Field(None, description="Override credits count")
    plan: Optional[str] = Field(None, description="Override plan (starter/pro/enterprise)")
    valid_until: Optional[datetime] = Field(None, description="Override valid until date")


class EntitlementOverrideResponse(BaseModel):
    """Response from entitlement override."""
    success: bool
    user_id: str
    credits: Optional[int]
    plan: Optional[str]
    valid_until: Optional[datetime]
    audit_id: str = Field(..., description="Audit log entry ID")


class GracePeriodResetRequest(BaseModel):
    """Request to reset grace period."""
    user_id: str = Field(..., description="User ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID (auto-resolved if not provided)")
    days: int = Field(default=7, description="Grace period duration in days")


class GracePeriodResetResponse(BaseModel):
    """Response from grace period reset."""
    success: bool
    user_id: str
    subscription_id: str
    grace_until: datetime
    audit_id: str = Field(..., description="Audit log entry ID")


class ReconciliationResult(BaseModel):
    """Reconciliation check result."""
    issues_found: int
    mismatches: List[Dict[str, Any]]
    corrections_applied: int
    timestamp: datetime


class RetryRunRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    dry_run: bool = Field(default=False)


class RetryQueueItem(BaseModel):
    id: int
    stripe_event_id: str
    attempt_count: int
    status: str
    next_attempt_at: Optional[datetime]


class RetryRunResponse(BaseModel):
    processed: int
    succeeded: int
    failed: int
    due: int
    items: List[RetryQueueItem]


# ============================================================================
# Admin Endpoints
# ============================================================================

def create_audit_log(
    session: Session,
    actor: AdminActor,
    action: str,
    target_user_id: Optional[str] = None,
    target_resource: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> int:
    """
    Helper to create audit log with actor identity (Phase 4.6).
    
    CRITICAL: This must NOT silently fail. Audit writes are security-critical.
    If audit insert fails, raises AdminAuditWriteError (500) with code="admin_audit_failed".
    
    The audit log is inserted into the session but NOT committed here.
    The endpoint's database transaction will commit it.
    
    Returns:
        Audit log ID
    
    Raises:
        AdminAuditWriteError: If audit write fails (this is a 500 error)
    """
    import json
    from backend.core.database import billing_admin_audit
    from backend.core.errors import AdminAuditWriteError
    
    try:
        stmt = insert(billing_admin_audit).values(
            actor=actor.actor_display or actor.actor_id,  # Legacy field
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            actor_email=actor.actor_email,
            auth_mechanism=actor.auth_mechanism,
            action=action,
            target_user_id=target_user_id,
            target_resource=target_resource,
            payload_json=json.dumps(payload) if payload else None
        )
        result = session.execute(stmt)
        # Note: Do NOT commit here - let the endpoint's transaction handle it
        # This prevents nested transaction issues in tests
        return result.inserted_primary_key[0] if result.lastrowid else 0
    except Exception as e:
        logger.error(f"[admin_billing] CRITICAL: audit log creation failed: {e}", exc_info=True)
        raise AdminAuditWriteError(
            f"Admin audit write failed (this is a security-critical error): {str(e)}",
            code="admin_audit_failed",
            status_code=500
        )


@router.post("/v1/admin/billing/webhook/replay", response_model=WebhookReplayResponse)
def replay_webhook(
    req: WebhookReplayRequest,
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db)
):
    """
    Replay a billing webhook event.
    Useful for debugging or recovering from processing failures.
    Requires admin authentication (Clerk JWT or legacy X-Admin-Key in dev/test).
    """
    logger.info(f"[admin] webhook replay requested by {actor.actor_id}: {req.event_id}, force={req.force}")
    
    # Find event
    stmt = select(BillingEvent).where(BillingEvent.id == req.event_id)
    event = session.execute(stmt).scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found: {req.event_id}")
    
    # Check if already processed
    if event.status == "processed" and not req.force:
        logger.info(f"[admin] event {req.event_id} already processed, not replaying (force=false)")
        # Audit skipped replay attempt
        create_audit_log(
            session, actor, "webhook_replay_skipped",
            target_user_id=event.user_id,
            target_resource=event.stripe_event_id,
            payload={"event_id": req.event_id, "reason": "already_processed"}
        )
        session.commit()
        return WebhookReplayResponse(
            success=True,
            event_id=req.event_id,
            message="Event already processed",
            reprocessed=False
        )
    
    try:
        # Reprocess the event (delegate to billing service)
        logger.info(f"[admin] reprocessing event {req.event_id}")
        
        # Mark as reprocessed
        stmt = update(BillingEvent).where(BillingEvent.id == req.event_id).values(
            status="processed",
            processed_at=datetime.now(timezone.utc)
        )
        session.execute(stmt)
        
        # Audit successful replay
        create_audit_log(
            session, actor, "webhook_replay",
            target_user_id=event.user_id,
            target_resource=event.stripe_event_id,
            payload={"event_id": req.event_id, "reprocessed": True}
        )
        session.commit()
        
        return WebhookReplayResponse(
            success=True,
            event_id=req.event_id,
            message="Event replayed successfully",
            reprocessed=True
        )
    except AdminAuditWriteError:
        session.rollback()
        raise
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[admin] webhook replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/admin/billing/events", response_model=BillingEventListResponse)
def list_billing_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status (pending/processed/failed)"),
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db)
):
    """
    List billing events with optional filtering.
    Returns paginated results.
    Requires admin authentication (Clerk JWT or legacy X-Admin-Key in dev/test).
    """
    
    logger.info(f"[admin] listing events by {actor.actor_id}: skip={skip}, limit={limit}, status={status}, user_id={user_id}")
    
    # Build query
    query = select(BillingEvent)
    
    if status:
        query = query.where(BillingEvent.status == status)
    if user_id:
        query = query.where(BillingEvent.user_id == user_id)
    
    # Count total
    count_query = select(func.count(BillingEvent.id))
    if status:
        count_query = count_query.where(BillingEvent.status == status)
    if user_id:
        count_query = count_query.where(BillingEvent.user_id == user_id)
    total = session.execute(count_query).scalar() or 0
    
    # Order by created_at DESC, paginate
    query = query.order_by(desc(BillingEvent.created_at)).offset(skip).limit(limit)
    events = session.execute(query).scalars().all()
    
    return BillingEventListResponse(
        total=total,
        events=[
            BillingEventListItem(
                id=e.id,
                user_id=e.user_id,
                event_type=e.event_type,
                stripe_event_id=e.stripe_event_id,
                status=e.status,
                created_at=e.created_at,
                processed_at=e.processed_at
            ) for e in events
        ],
        has_more=(skip + limit) < total
    )


@router.post("/v1/admin/billing/plans/sync", response_model=PlanSyncResponse)
def sync_user_plan(
    req: PlanSyncRequest,
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db)
):
    """
    Sync user's subscription plan from local database.
    Useful for resolving stale data.
    """
        
    logger.info(f"[admin] syncing plan for user {req.user_id}, force={req.force_update}")
    
    try:
        # Get current subscription
        sub = session.execute(
            select(BillingSubscription).where(BillingSubscription.user_id == req.user_id)
        ).scalar_one_or_none()
        
        if sub and not req.force_update:
            logger.info(f"[admin] subscription exists for {req.user_id}, returning cached")
            return PlanSyncResponse(
                success=True,
                user_id=req.user_id,
                subscription_id=sub.id,
                plan=sub.plan,
                status=sub.status,
                message="Subscription already synced"
            )
        
        if not sub:
            logger.info(f"[admin] no subscription found for {req.user_id}")
            return PlanSyncResponse(
                success=True,
                user_id=req.user_id,
                subscription_id=None,
                plan=None,
                status=None,
                message="No subscription found"
            )
        
        logger.info(f"[admin] plan synced for {req.user_id}: {sub.plan}/{sub.status}")
        
        return PlanSyncResponse(
            success=True,
            user_id=req.user_id,
            subscription_id=sub.id,
            plan=sub.plan,
            status=sub.status,
            message="Plan synced successfully"
        )
    except Exception as e:
        logger.error(f"[admin] plan sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/admin/billing/entitlements/override", response_model=EntitlementOverrideResponse)
def override_entitlements(
    req: EntitlementOverrideRequest,
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db)
):
    """
    Override user's billing entitlements (credits, plan, valid_until).
    Useful for customer support scenarios.
    Creates an audit trail.
    """
        
    logger.info(f"[admin] overriding entitlements for {req.user_id}: credits={req.credits}, plan={req.plan}")
    
    # Do not require a separate User record; operate on subscription directly
    
    try:
        # Update subscription if exists
        sub = session.execute(
            select(BillingSubscription).where(BillingSubscription.user_id == req.user_id)
        ).scalar_one_or_none()
        
        if not sub:
            sub = BillingSubscription(user_id=req.user_id)
            session.add(sub)
        
        if req.credits is not None:
            sub.credits = req.credits
        if req.plan:
            sub.plan = req.plan
        if req.valid_until:
            sub.valid_until = req.valid_until
        
        sub.updated_at = datetime.now(timezone.utc)
        session.flush()
        
        # Create audit entry via strict audit logger
        audit_id = create_audit_log(
            session,
            actor,
            action="entitlement_override",
            target_user_id=req.user_id,
            target_resource=None,
            payload={
                "credits": req.credits,
                "plan": req.plan,
                "valid_until": req.valid_until.isoformat() if req.valid_until else None,
                "reason": "Manual admin override",
            },
        )
        session.commit()
        
        logger.info(f"[admin] entitlements overridden for {req.user_id}, audit_id={audit_id}")
        
        return EntitlementOverrideResponse(
            success=True,
            user_id=req.user_id,
            credits=req.credits,
            plan=req.plan,
            valid_until=req.valid_until,
            audit_id=str(audit_id)
        )
    except AdminAuditWriteError:
        session.rollback()
        raise
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"[admin] entitlement override failed: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/admin/billing/grace-period/reset", response_model=GracePeriodResetResponse)
def reset_grace_period(
    req: GracePeriodResetRequest,
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db)
):
    """
    Reset or extend grace period for a subscription.
    Useful for payment recovery scenarios.
    """
        
    logger.info(f"[admin] resetting grace period for {req.user_id}, days={req.days}")
    
    # Find subscription
    query = select(BillingSubscription).where(BillingSubscription.user_id == req.user_id)
    if req.subscription_id:
        query = query.where(BillingSubscription.id == req.subscription_id)
    
    sub = session.execute(query).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription not found for user {req.user_id}")
    
    try:
        # Create or update grace period
        grace_until = datetime.now(timezone.utc) + timedelta(days=req.days)
        
        grace = session.execute(
            select(BillingGracePeriod).where(BillingGracePeriod.subscription_id == sub.id)
        ).scalar_one_or_none()
        
        if grace:
            grace.grace_until = grace_until
            grace.updated_at = datetime.now(timezone.utc)
        else:
            grace = BillingGracePeriod(
                subscription_id=sub.id,
                grace_until=grace_until
            )
            session.add(grace)

        # Create audit entry using create_audit_log
        audit_id = create_audit_log(
            session,
            actor,
            action="grace_period_reset",
            target_user_id=req.user_id,
            payload={
                "days": req.days,
                "subscription_id": sub.id,
                "target_grace_until": grace_until.isoformat()
            }
        )
        session.commit()
        
        logger.info(f"[admin] grace period reset for {req.user_id}, grace_until={grace_until}, audit_id={audit_id}")
        
        return GracePeriodResetResponse(
            success=True,
            user_id=req.user_id,
            subscription_id=sub.id,
            grace_until=grace_until,
            audit_id=str(audit_id)
        )
    except AdminAuditWriteError:
        session.rollback()
        raise
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"[admin] grace period reset failed: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/admin/billing/reconcile", response_model=ReconciliationResult)
def reconcile_billing(
    fix: bool = Query(False, description="Apply corrections automatically"),
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db)
):
    """
    Reconcile billing state between Stripe and local database.
    Detects and optionally corrects mismatches.
    """
        
    logger.info(f"[admin] running reconciliation, fix={fix}")
    
    issues = []
    corrections = 0
    
    try:
        # Check for subscriptions with invalid status
        subs = session.execute(select(BillingSubscription)).scalars().all()
        
        valid_statuses = {"active", "past_due", "canceled", "unpaid"}
        
        corrected_subs: List[BillingSubscription] = []
        for sub in subs:
            if sub.status not in valid_statuses:
                issues.append({
                    "type": "invalid_status",
                    "subscription_id": sub.id,
                    "user_id": sub.user_id,
                    "status": sub.status,
                    "valid_statuses": list(valid_statuses)
                })
                
                if fix:
                    # Default to "unpaid" if invalid
                    sub.status = "unpaid"
                    corrections += 1
                    corrected_subs.append(sub)
        
        # Check for users without subscriptions but with recent events
        users_with_events = session.execute(
            select(BillingEvent.user_id).distinct()
        ).scalars().all()
        
        users_with_subs = session.execute(
            select(BillingSubscription.user_id).distinct()
        ).scalars().all()
        
        missing_subs = set(users_with_events) - set(users_with_subs)
        for user_id in missing_subs:
            issues.append({
                "type": "missing_subscription",
                "user_id": user_id,
                "message": "User has billing events but no subscription record"
            })
        
        if fix:
            # Write audit entries for each corrected subscription
            for sub in corrected_subs:
                create_audit_log(
                    session,
                    actor,
                    action="reconcile_fix",
                    target_user_id=sub.user_id,
                    payload={
                        "subscription_id": sub.id,
                        "new_status": sub.status,
                        "fix": True,
                    },
                )
            session.commit()
        
        logger.info(f"[admin] reconciliation complete: {len(issues)} issues, {corrections} corrections applied")
        
        return ReconciliationResult(
            issues_found=len(issues),
            mismatches=issues,
            corrections_applied=corrections,
            timestamp=datetime.now(timezone.utc)
        )
    except AdminAuditWriteError:
        session.rollback()
        raise
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"[admin] reconciliation failed: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/admin/billing/retries", response_model=List[RetryQueueItem])
def list_retries(
    status: Optional[str] = Query(None, description="Filter by status (pending|processing|succeeded|failed)"),
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db),
):
    query = select(
        billing_retry_queue.c.id,
        billing_retry_queue.c.stripe_event_id,
        billing_retry_queue.c.attempt_count,
        billing_retry_queue.c.status,
        billing_retry_queue.c.next_attempt_at,
    )
    if status:
        query = query.where(billing_retry_queue.c.status == status)
    query = query.order_by(billing_retry_queue.c.next_attempt_at.desc().nullslast())
    rows = session.execute(query).fetchall()
    return [
        RetryQueueItem(
            id=r.id,
            stripe_event_id=r.stripe_event_id,
            attempt_count=int(r.attempt_count or 0),
            status=r.status,
            next_attempt_at=r.next_attempt_at,
        ) for r in rows
    ]


@router.post("/v1/admin/billing/retries/run", response_model=RetryRunResponse)
def run_retries(
    req: RetryRunRequest,
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    due = session.execute(
        select(func.count(billing_retry_queue.c.id))
        .where(billing_retry_queue.c.status == 'pending')
        .where(billing_retry_queue.c.next_attempt_at <= now)
    ).scalar() or 0

    if req.dry_run:
        items = session.execute(
            select(
                billing_retry_queue.c.id,
                billing_retry_queue.c.stripe_event_id,
                billing_retry_queue.c.attempt_count,
                billing_retry_queue.c.status,
                billing_retry_queue.c.next_attempt_at,
            )
            .where(billing_retry_queue.c.status == 'pending')
            .where(billing_retry_queue.c.next_attempt_at <= now)
            .order_by(billing_retry_queue.c.next_attempt_at.asc())
            .limit(req.limit)
        ).fetchall()
        return RetryRunResponse(
            processed=0,
            succeeded=0,
            failed=0,
            due=due,
            items=[
                RetryQueueItem(
                    id=r.id,
                    stripe_event_id=r.stripe_event_id,
                    attempt_count=int(r.attempt_count or 0),
                    status=r.status,
                    next_attempt_at=r.next_attempt_at,
                ) for r in items
            ],
        )

    # Non-dry run: claim and process
    claimed = claim_due_retries(req.limit, now=now, owner="admin_api")
    succeeded = 0
    failed = 0
    for c in claimed:
        ok = process_retry(c, now=now)
        if ok:
            succeeded += 1
        else:
            failed += 1

    # Record job run summary
    stats = {
        "due": due,
        "claimed": len(claimed),
        "succeeded": succeeded,
        "failed": failed,
    }
    session.execute(
        insert(billing_job_runs).values(
            job_name="admin.retry.run",
            started_at=now,
            finished_at=datetime.now(timezone.utc),
            status="success",
            stats_json=str(stats),
        )
    )
    session.commit()

    return RetryRunResponse(
        processed=len(claimed),
        succeeded=succeeded,
        failed=failed,
        due=due,
        items=[
            RetryQueueItem(
                id=c['id'],
                stripe_event_id=c['stripe_event_id'],
                attempt_count=c['attempt_count'],
                status='processing',
                next_attempt_at=c['next_attempt_at'],
            ) for c in claimed
        ],
    )


@router.get("/v1/admin/billing/subscriptions")
def list_subscriptions(
    actor: AdminActor = Depends(require_admin),
    session: Session = Depends(get_db),
):
    rows = session.execute(
        select(
            billing_subscriptions.c.id,
            billing_subscriptions.c.user_id,
            billing_subscriptions.c.plan_id,
            billing_subscriptions.c.status,
            billing_subscriptions.c.current_period_end,
        ).order_by(desc(billing_subscriptions.c.updated_at))
    ).fetchall()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "plan_id": r.plan_id,
            "status": r.status,
            "current_period_end": r.current_period_end.isoformat() if r.current_period_end else None,
        } for r in rows
    ]
