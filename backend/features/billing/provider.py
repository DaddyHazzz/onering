"""
Billing provider protocol (Phase 4.3).

Defines the interface for billing providers (Stripe, etc.).
This allows swapping providers without changing business logic.
"""
from typing import Protocol, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BillingWebhookResult:
    """Result of processing a billing webhook."""
    event_id: str
    event_type: str
    user_id: Optional[str]
    subscription_id: Optional[str]
    plan_id: Optional[str]
    status: Optional[str]  # active, canceled, past_due, etc.
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    metadata: Dict[str, Any]


class BillingProvider(Protocol):
    """
    Protocol for billing providers.
    
    Implementations must handle:
    - Customer creation
    - Checkout session creation
    - Portal session creation
    - Webhook signature verification and parsing
    """
    
    def ensure_customer(self, user_id: str, email: Optional[str] = None, name: Optional[str] = None) -> str:
        """
        Ensure a billing customer exists for the user.
        
        Args:
            user_id: Internal user ID
            email: User email (optional)
            name: User name (optional)
        
        Returns:
            Provider customer ID (e.g., Stripe customer ID)
        
        Raises:
            BillingProviderError: If customer creation fails
        """
        ...
    
    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a checkout session for a subscription.
        
        Args:
            customer_id: Provider customer ID
            price_id: Provider price ID (e.g., Stripe price ID)
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancellation
            metadata: Optional metadata to attach
        
        Returns:
            Checkout session URL
        
        Raises:
            BillingProviderError: If session creation fails
        """
        ...
    
    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """
        Create a billing portal session for customer self-service.
        
        Args:
            customer_id: Provider customer ID
            return_url: URL to return to after portal actions
        
        Returns:
            Portal session URL
        
        Raises:
            BillingProviderError: If portal session creation fails
        """
        ...
    
    def handle_webhook(self, headers: Dict[str, str], body: bytes) -> BillingWebhookResult:
        """
        Verify webhook signature and parse event.
        
        Args:
            headers: HTTP headers (must include signature header)
            body: Raw webhook body (for signature verification)
        
        Returns:
            Parsed webhook result
        
        Raises:
            BillingWebhookError: If signature invalid or parsing fails
        """
        ...


class BillingProviderError(Exception):
    """Base exception for billing provider errors."""
    pass


class BillingWebhookError(BillingProviderError):
    """Exception for webhook processing errors."""
    pass
