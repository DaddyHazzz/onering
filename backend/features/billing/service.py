"""
Billing service orchestrator (Phase 4.3).

Pure-ish business logic that coordinates:
- Customer management
- Subscription lifecycle
- Webhook processing
- Plan synchronization

All Stripe-specific code is in stripe_provider.py.
"""
import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, insert, update, and_
from sqlalchemy.exc import IntegrityError

from backend.core.database import (
    get_db_session,
    billing_customers,
    billing_subscriptions,
    billing_events,
    user_plans,
)
from backend.features.billing.provider import (
    BillingProvider,
    BillingProviderError,
    BillingWebhookError,
    BillingWebhookResult,
)
from backend.features.billing.stripe_provider import StripeProvider


def billing_enabled() -> bool:
    """Check if billing is enabled (Stripe configured)."""
    return bool(os.getenv("STRIPE_SECRET_KEY"))


def get_provider() -> Optional[BillingProvider]:
    """Get billing provider if billing is enabled."""
    if not billing_enabled():
        return None
    try:
        return StripeProvider()
    except BillingProviderError:
        return None


def ensure_customer_for_user(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None
) -> Optional[str]:
    """
    Ensure a billing customer exists for the user.
    
    Returns:
        Stripe customer ID, or None if billing disabled
    
    Raises:
        BillingProviderError: If customer creation fails
    """
    provider = get_provider()
    if not provider:
        return None
    
    with get_db_session() as session:
        # Check if customer already exists
        result = session.execute(
            select(billing_customers.c.stripe_customer_id).where(
                billing_customers.c.user_id == user_id
            )
        ).fetchone()
        
        if result:
            return result[0]
        
        # Create customer in Stripe
        stripe_customer_id = provider.ensure_customer(user_id, email, name)
        
        # Store in database
        session.execute(
            insert(billing_customers).values(
                user_id=user_id,
                stripe_customer_id=stripe_customer_id,
            )
        )
        session.commit()
        
        return stripe_customer_id


def start_checkout(
    user_id: str,
    plan_id: str,
    success_url: str,
    cancel_url: str
) -> Optional[str]:
    """
    Start checkout session for a subscription.
    
    Args:
        user_id: User ID
        plan_id: Internal plan ID (free, creator, team)
        success_url: Redirect URL on success
        cancel_url: Redirect URL on cancel
    
    Returns:
        Checkout URL, or None if billing disabled
    
    Raises:
        BillingProviderError: If checkout creation fails
        ValueError: If plan_id is invalid or not mapped to Stripe price
    """
    provider = get_provider()
    if not provider:
        return None
    
    # Map plan_id to Stripe price ID
    price_id = get_stripe_price_for_plan(plan_id)
    if not price_id:
        raise ValueError(f"No Stripe price configured for plan: {plan_id}")
    
    # Ensure customer exists
    stripe_customer_id = ensure_customer_for_user(user_id)
    if not stripe_customer_id:
        raise BillingProviderError("Failed to ensure customer")
    
    # Create checkout session
    checkout_url = provider.create_checkout_session(
        customer_id=stripe_customer_id,
        price_id=price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"plan_id": plan_id, "user_id": user_id},
    )
    
    return checkout_url


def start_portal(user_id: str, return_url: str) -> Optional[str]:
    """
    Start billing portal session for customer self-service.
    
    Args:
        user_id: User ID
        return_url: URL to return to after portal actions
    
    Returns:
        Portal URL, or None if billing disabled or customer doesn't exist
    
    Raises:
        BillingProviderError: If portal creation fails
    """
    provider = get_provider()
    if not provider:
        return None
    
    with get_db_session() as session:
        # Get customer ID
        result = session.execute(
            select(billing_customers.c.stripe_customer_id).where(
                billing_customers.c.user_id == user_id
            )
        ).fetchone()
        
        if not result:
            return None
        
        stripe_customer_id = result[0]
    
    # Create portal session
    portal_url = provider.create_portal_session(
        customer_id=stripe_customer_id,
        return_url=return_url,
    )
    
    return portal_url


def apply_subscription_state(
    user_id: str,
    stripe_subscription_id: str,
    plan_id: str,
    status: str,
    current_period_end: Optional[datetime] = None,
    cancel_at_period_end: bool = False
) -> None:
    """
    Apply subscription state to database (idempotent).
    
    Updates or creates subscription record and syncs user_plans.
    """
    with get_db_session() as session:
        # Upsert subscription
        existing = session.execute(
            select(billing_subscriptions.c.id).where(
                billing_subscriptions.c.stripe_subscription_id == stripe_subscription_id
            )
        ).fetchone()
        
        if existing:
            # Update existing
            session.execute(
                update(billing_subscriptions)
                .where(billing_subscriptions.c.stripe_subscription_id == stripe_subscription_id)
                .values(
                    plan_id=plan_id,
                    status=status,
                    current_period_end=current_period_end,
                    cancel_at_period_end=cancel_at_period_end,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            # Insert new
            session.execute(
                insert(billing_subscriptions).values(
                    user_id=user_id,
                    stripe_subscription_id=stripe_subscription_id,
                    plan_id=plan_id,
                    status=status,
                    current_period_end=current_period_end,
                    cancel_at_period_end=cancel_at_period_end,
                )
            )
        
        # Sync user_plans if subscription is active
        if status == "active":
            # Update or insert user_plans
            user_plan_exists = session.execute(
                select(user_plans.c.user_id).where(
                    user_plans.c.user_id == user_id
                )
            ).fetchone()
            
            if user_plan_exists:
                session.execute(
                    update(user_plans)
                    .where(user_plans.c.user_id == user_id)
                    .values(plan_id=plan_id, assigned_at=datetime.utcnow())
                )
            else:
                session.execute(
                    insert(user_plans).values(
                        user_id=user_id,
                        plan_id=plan_id,
                    )
                )
        elif status in ("canceled", "unpaid", "past_due"):
            # Downgrade to free plan (if exists)
            free_plan_exists = session.execute(
                select(user_plans.c.user_id).where(
                    user_plans.c.user_id == user_id
                )
            ).fetchone()
            
            if free_plan_exists:
                session.execute(
                    update(user_plans)
                    .where(user_plans.c.user_id == user_id)
                    .values(plan_id="free", assigned_at=datetime.utcnow())
                )
        
        session.commit()


def process_webhook_event(headers: Dict[str, str], body: bytes) -> BillingWebhookResult:
    """
    Process billing webhook event (idempotent).
    
    1. Verify signature
    2. Check idempotency (skip if already processed)
    3. Parse event
    4. Apply state changes
    5. Mark as processed
    
    Returns:
        BillingWebhookResult
    
    Raises:
        BillingWebhookError: If signature invalid or processing fails
    """
    provider = get_provider()
    if not provider:
        raise BillingWebhookError("Billing not enabled")
    
    # Verify and parse webhook
    result = provider.handle_webhook(headers, body)
    
    # Compute payload hash for deduplication
    payload_hash = hashlib.sha256(body).hexdigest()
    
    with get_db_session() as session:
        # Check idempotency: skip if event already processed
        existing = session.execute(
            select(billing_events.c.id).where(
                billing_events.c.stripe_event_id == result.event_id
            )
        ).fetchone()
        
        if existing:
            # Already processed, skip
            return result
        
        # Record event
        try:
            session.execute(
                insert(billing_events).values(
                    stripe_event_id=result.event_id,
                    event_type=result.event_type,
                    payload_hash=payload_hash,
                    processed=False,
                )
            )
            session.commit()
        except IntegrityError:
            # Race condition: another process already inserted this event
            session.rollback()
            return result
    
    # Apply state changes based on event type
    try:
        if result.user_id and result.subscription_id and result.plan_id:
            apply_subscription_state(
                user_id=result.user_id,
                stripe_subscription_id=result.subscription_id,
                plan_id=result.plan_id,
                status=result.status or "unknown",
                current_period_end=result.current_period_end,
                cancel_at_period_end=result.cancel_at_period_end,
            )
        
        # Mark event as processed
        with get_db_session() as session:
            session.execute(
                update(billing_events)
                .where(billing_events.c.stripe_event_id == result.event_id)
                .values(processed=True, processed_at=datetime.utcnow())
            )
            session.commit()
    except Exception as e:
        # Mark event as failed
        with get_db_session() as session:
            session.execute(
                update(billing_events)
                .where(billing_events.c.stripe_event_id == result.event_id)
                .values(error=str(e))
            )
            session.commit()
        raise
    
    return result


def get_stripe_price_for_plan(plan_id: str) -> Optional[str]:
    """Map internal plan ID to Stripe price ID."""
    price_map = {
        "free": os.getenv("STRIPE_PRICE_FREE"),
        "creator": os.getenv("STRIPE_PRICE_CREATOR"),
        "team": os.getenv("STRIPE_PRICE_TEAM"),
    }
    return price_map.get(plan_id)


def get_billing_status(user_id: str) -> Dict[str, Any]:
    """
    Get user's billing status.
    
    Returns:
        {
            "enabled": bool,
            "plan_id": str | None,
            "status": str | None,
            "period_end": datetime | None,
            "cancel_at_period_end": bool
        }
    """
    if not billing_enabled():
        return {
            "enabled": False,
            "plan_id": None,
            "status": None,
            "period_end": None,
            "cancel_at_period_end": False,
        }
    
    with get_db_session() as session:
        # Get active subscription
        result = session.execute(
            select(
                billing_subscriptions.c.plan_id,
                billing_subscriptions.c.status,
                billing_subscriptions.c.current_period_end,
                billing_subscriptions.c.cancel_at_period_end,
            )
            .where(
                and_(
                    billing_subscriptions.c.user_id == user_id,
                    billing_subscriptions.c.status == "active",
                )
            )
            .order_by(billing_subscriptions.c.created_at.desc())
            .limit(1)
        ).fetchone()
        
        if result:
            return {
                "enabled": True,
                "plan_id": result[0],
                "status": result[1],
                "period_end": result[2],
                "cancel_at_period_end": result[3],
            }
        
        return {
            "enabled": True,
            "plan_id": None,
            "status": None,
            "period_end": None,
            "cancel_at_period_end": False,
        }
