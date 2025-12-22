"""
backend/models/usage_event.py

UsageEvent model for monetization hooks (Phase 4.1).

Tracks usage for entitlement enforcement.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class UsageEvent(BaseModel):
    """
    UsageEvent tracks a usage occurrence.
    
    Usage Keys:
    - drafts.created: User created a draft
    - segments.appended: User appended a segment
    - collaborators.added: User added a collaborator
    - ai_credits.used: User used AI generation credits (future)
    
    Metadata can include:
    - draft_id: Related draft
    - segment_id: Related segment
    - collaborator_id: Added collaborator
    """
    model_config = ConfigDict(frozen=True)
    
    user_id: str
    usage_key: str
    occurred_at: datetime
    metadata: Optional[Dict[str, Any]] = None
