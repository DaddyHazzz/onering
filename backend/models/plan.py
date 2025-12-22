"""
backend/models/plan.py

Plan model for monetization hooks (Phase 4.1).

Plans represent capability tiers (free, creator, team) without pricing.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class Plan(BaseModel):
    """
    Plan represents a capability tier.
    
    Examples:
    - free (default)
    - creator
    - team
    
    Plans do NOT include:
    - Pricing (no currency, no amounts)
    - Billing cycles (no monthly/annual)
    - Payment methods
    """
    model_config = ConfigDict(frozen=True)
    
    plan_id: str
    name: str
    is_default: bool = False
    created_at: datetime
