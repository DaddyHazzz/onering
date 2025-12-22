"""
backend/models/entitlement.py

Entitlement model for monetization hooks (Phase 4.1).

Entitlements define what a plan allows (drafts.max, collaborators.max, etc.).
"""

from typing import Union
from pydantic import BaseModel, ConfigDict


class Entitlement(BaseModel):
    """
    Entitlement represents a capability limit or feature flag.
    
    Entitlement Keys:
    - drafts.max (int): Maximum drafts per user
    - collaborators.max (int): Maximum collaborators per draft
    - segments.max (int): Maximum segments per draft
    - analytics.enabled (bool): Access to analytics features
    - ai_credits.monthly (int): AI generation credits per month (future)
    
    Value Types:
    - int: numeric limits (-1 = unlimited)
    - bool: feature flags (true = enabled, false = disabled)
    - str: not used yet (reserved for future)
    """
    model_config = ConfigDict(frozen=True)
    
    entitlement_key: str
    value: Union[int, bool, str]
    plan_id: str
