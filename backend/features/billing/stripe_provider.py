"""
Stripe billing provider implementation (Phase 4.3).

Implements BillingProvider protocol using Stripe API.
Handles webhook signature verification and event parsing.
"""
import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import stripe

from backend.features.billing.provider import (
    BillingProvider,
    BillingProviderError,
    BillingWebhookError,
    BillingWebhookResult,
)


class StripeProvider:
    """Stripe implementation of BillingProvider protocol."""
    
    def __init__(self, secret_key: Optional[str] = None, webhook_secret: Optional[str] = None):
        """
        Initialize Stripe provider.
        
        Args:
            secret_key: Stripe secret key (defaults to STRIPE_SECRET_KEY env var)
            webhook_secret: Stripe webhook secret (defaults to STRIPE_WEBHOOK_SECRET env var)
        """
        self.secret_key = secret_key or os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not self.secret_key:
            raise BillingProviderError("STRIPE_SECRET_KEY not configured")
        
        stripe.api_key = self.secret_key
    
    def ensure_customer(self, user_id: str, email: Optional[str] = None, name: Optional[str] = None) -> str:
        """Create or retrieve Stripe customer for user."""
        try:
            # Search for existing customer by metadata
            customers = stripe.Customer.list(limit=1, metadata={"user_id": user_id})
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer_data: Dict[str, Any] = {
                "metadata": {"user_id": user_id}
            }
            if email:
                customer_data["email"] = email
            if name:
                customer_data["name"] = name
            
            customer = stripe.Customer.create(**customer_data)
            return customer.id
        except stripe.error.StripeError as e:
            raise BillingProviderError(f"Stripe customer creation failed: {e}")
    
    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Create Stripe checkout session."""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )
            return session.url
        except stripe.error.StripeError as e:
            raise BillingProviderError(f"Stripe checkout session creation failed: {e}")
    
    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create Stripe billing portal session."""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            raise BillingProviderError(f"Stripe portal session creation failed: {e}")
    
    def handle_webhook(self, headers: Dict[str, str], body: bytes) -> BillingWebhookResult:
        """Verify Stripe webhook signature and parse event."""
        if not self.webhook_secret:
            raise BillingWebhookError("STRIPE_WEBHOOK_SECRET not configured")
        
        try:
            # Verify signature
            sig_header = headers.get("stripe-signature") or headers.get("Stripe-Signature")
            if not sig_header:
                raise BillingWebhookError("Missing stripe-signature header")
            
            event = stripe.Webhook.construct_event(
                body, sig_header, self.webhook_secret
            )
        except ValueError as e:
            raise BillingWebhookError(f"Invalid payload: {e}")
        except stripe.error.SignatureVerificationError as e:
            raise BillingWebhookError(f"Invalid signature: {e}")
        
        # Parse event into BillingWebhookResult
        return self._parse_event(event)
    
    def _parse_event(self, event: Dict[str, Any]) -> BillingWebhookResult:
        """Parse Stripe event into normalized BillingWebhookResult."""
        event_type = event["type"]
        event_id = event["id"]
        data = event.get("data", {}).get("object", {})
        
        # Extract common fields
        user_id = None
        subscription_id = None
        plan_id = None
        status = None
        current_period_end = None
        cancel_at_period_end = False
        
        # Handle subscription events
        if "customer.subscription" in event_type:
            subscription_id = data.get("id")
            status = data.get("status")
            
            # Extract user_id from customer metadata
            customer_id = data.get("customer")
            if customer_id:
                try:
                    customer = stripe.Customer.retrieve(customer_id)
                    user_id = customer.get("metadata", {}).get("user_id")
                except stripe.error.StripeError:
                    pass
            
            # Extract plan_id from subscription metadata or price
            plan_id = data.get("metadata", {}).get("plan_id")
            if not plan_id:
                # Try to infer from price ID
                items = data.get("items", {}).get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id")
                    plan_id = self._map_price_to_plan(price_id)
            
            # Period end
            period_end_ts = data.get("current_period_end")
            if period_end_ts:
                current_period_end = datetime.fromtimestamp(period_end_ts)
            
            cancel_at_period_end = data.get("cancel_at_period_end", False)
        
        # Handle checkout completed events
        elif event_type == "checkout.session.completed":
            subscription_id = data.get("subscription")
            customer_id = data.get("customer")
            
            if customer_id:
                try:
                    customer = stripe.Customer.retrieve(customer_id)
                    user_id = customer.get("metadata", {}).get("user_id")
                except stripe.error.StripeError:
                    pass
            
            # Extract plan_id from session metadata
            plan_id = data.get("metadata", {}).get("plan_id")
        
        return BillingWebhookResult(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
            subscription_id=subscription_id,
            plan_id=plan_id,
            status=status,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            metadata=data.get("metadata", {}),
        )
    
    def _map_price_to_plan(self, price_id: str) -> Optional[str]:
        """Map Stripe price ID to internal plan ID."""
        # Map using environment variables
        price_map = {
            os.getenv("STRIPE_PRICE_FREE"): "free",
            os.getenv("STRIPE_PRICE_CREATOR"): "creator",
            os.getenv("STRIPE_PRICE_TEAM"): "team",
        }
        return price_map.get(price_id)
