"""
backend/models/invite.py
Collaboration invite models: idempotent invite creation, acceptance, revocation.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional


class InviteStatus(str, Enum):
    """Invite lifecycle: pending -> accepted OR revoked/expired"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CollaborationInvite(BaseModel):
    """Invite to join a draft collaboration"""

    model_config = ConfigDict(frozen=True)

    invite_id: str = Field(description="UUID")
    draft_id: str = Field(description="Target draft UUID")
    created_by_user_id: str = Field(description="User who created invite")
    target_user_id: str = Field(description="Resolved target user ID (from handle or direct)")
    target_handle: Optional[str] = Field(default=None, description="Original handle if resolved")
    status: InviteStatus = Field(default=InviteStatus.PENDING)
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    token_hash: Optional[str] = Field(
        default=None, description="Hashed token (never returned to client)"
    )
    token_hint: Optional[str] = Field(
        default=None, description="Last 6 chars of token for UI display"
    )
    idempotency_key: Optional[str] = None


class InviteSummary(BaseModel):
    """Safe invite summary (no sensitive fields)"""

    model_config = ConfigDict(frozen=True)

    invite_id: str
    draft_id: str = Field(description="Draft UUID this invite is for")
    target_user_id: str
    target_handle: Optional[str]
    status: InviteStatus
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    token_hint: Optional[str]
    created_by_user_id: str
    message: Optional[str] = Field(default=None, description="Supportive message for accept flow")


class CreateInviteRequest(BaseModel):
    """Request to create invite"""

    target_handle: Optional[str] = Field(default=None, description="Handle to resolve to user_id")
    target_user_id: Optional[str] = Field(default=None, description="Direct user ID (bypasses handle resolution)")
    expires_in_hours: int = Field(default=72, ge=1, le=720, description="Expiration time")
    idempotency_key: str = Field(description="UUID, prevents duplicate invites")


class AcceptInviteRequest(BaseModel):
    """Request to accept invite"""

    token: str = Field(description="Token received at invite creation time")
    idempotency_key: str = Field(description="UUID, prevents duplicate accepts")


class RevokeInviteRequest(BaseModel):
    """Request to revoke invite (only creator/owner)"""

    idempotency_key: str = Field(description="UUID, prevents duplicate revokes")


class CreateInviteResponse(BaseModel):
    """Response from invite creation"""

    model_config = ConfigDict(frozen=True)

    invite_id: str
    target_user_id: str
    target_handle: Optional[str]
    status: InviteStatus
    created_at: datetime
    expires_at: datetime
    token_hint: str
    share_url: str = Field(description="Deterministic URL path for sharing invite")
