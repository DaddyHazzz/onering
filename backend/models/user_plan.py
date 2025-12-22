"""
backend/models/user_plan.py

UserPlan model for monetization hooks (Phase 4.1).

Links users to their active plan.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserPlan(BaseModel):
    """
    UserPlan represents a user's active plan assignment.
    
    Constraint: Each user has exactly one active plan.
    """
    model_config = ConfigDict(frozen=True)
    
    user_id: str
    plan_id: str
    assigned_at: datetime
