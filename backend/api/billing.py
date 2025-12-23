"""
Billing API routes (Phase 4.3).

Minimal surface:
- POST /api/billing/checkout: Create checkout session
- POST /api/billing/portal: Create portal session
- POST /api/billing/webhook: Handle Stripe webhooks
- GET  /api/billing/status: Get user billing status
"""
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel

from backend.features.billing.service import (
    billing_enabled,
    start_checkout,
    start_portal,
    process_webhook_event,
    get_billing_status,
)
from backend.features.billing.provider import BillingProviderError, BillingWebhookError


router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    """Request to create checkout session."""
    plan_id: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    url: str


class PortalRequest(BaseModel):
    """Request to create portal session."""
    return_url: str


class PortalResponse(BaseModel):
    """Response with portal URL."""
    url: str


class BillingStatusResponse(BaseModel):
    """User billing status."""
    enabled: bool
    plan_id: str | None
    status: str | None
    period_end: str | None  # ISO8601
    cancel_at_period_end: bool


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, req: Request):
    """
    Create Stripe checkout session.
    
    Requires:
    - STRIPE_SECRET_KEY configured
    - Valid plan_id (creator, team)
    - User authenticated (user_id from context)
    
    Returns:
        {"url": "https://checkout.stripe.com/..."}
    
    Errors:
        503: Billing disabled (STRIPE_SECRET_KEY not set)
        400: Invalid plan_id
        500: Stripe API error
    """
    if not billing_enabled():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Billing disabled",
                "code": "billing_disabled",
                "message": "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.",
            },
        )
    
    # Extract user_id from request state (set by auth middleware)
    user_id = getattr(req.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        url = start_checkout(
            user_id=user_id,
            plan_id=request.plan_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        if not url:
            raise HTTPException(
                status_code=503,
                detail={"error": "Billing disabled", "code": "billing_disabled"},
            )
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BillingProviderError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portal", response_model=PortalResponse)
async def create_portal(request: PortalRequest, req: Request):
    """
    Create Stripe billing portal session.
    
    Requires:
    - STRIPE_SECRET_KEY configured
    - User authenticated
    - User has a Stripe customer record
    
    Returns:
        {"url": "https://billing.stripe.com/..."}
    
    Errors:
        503: Billing disabled
        404: Customer not found (user never checked out)
        500: Stripe API error
    """
    if not billing_enabled():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Billing disabled",
                "code": "billing_disabled",
                "message": "Stripe is not configured.",
            },
        )
    
    user_id = getattr(req.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        url = start_portal(user_id=user_id, return_url=request.return_url)
        if not url:
            raise HTTPException(
                status_code=404,
                detail="Customer not found. Complete checkout first.",
            )
        return {"url": url}
    except BillingProviderError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def handle_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Handle Stripe webhook events.
    
    Verifies signature, processes event idempotently, and updates subscription state.
    
    Signature verification uses STRIPE_WEBHOOK_SECRET.
    Event deduplication uses stripe_event_id (stored in billing_events table).
    
    Returns:
        {"received": true}
    
    Errors:
        400: Invalid signature or payload
        503: Billing disabled
    """
    if not billing_enabled():
        raise HTTPException(
            status_code=503,
            detail={"error": "Billing disabled", "code": "billing_disabled"},
        )
    
    # Read raw body (required for signature verification)
    body = await request.body()
    headers = dict(request.headers)
    
    try:
        result = process_webhook_event(headers, body)
        return {"received": True, "event_id": result.event_id}
    except BillingWebhookError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=BillingStatusResponse)
async def get_status(req: Request):
    """
    Get user's billing status.
    
    Returns:
        {
            "enabled": bool (true if Stripe configured),
            "plan_id": str | null (current plan),
            "status": str | null (active, canceled, etc.),
            "period_end": str | null (ISO8601),
            "cancel_at_period_end": bool
        }
    
    If billing disabled, returns:
        {"enabled": false, "plan_id": null, "status": null, ...}
    """
    user_id = getattr(req.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    status = get_billing_status(user_id)
    
    # Convert period_end datetime to ISO8601 string
    period_end_str = None
    if status["period_end"]:
        period_end_str = status["period_end"].isoformat()
    
    return {
        "enabled": status["enabled"],
        "plan_id": status["plan_id"],
        "status": status["status"],
        "period_end": period_end_str,
        "cancel_at_period_end": status["cancel_at_period_end"],
    }
