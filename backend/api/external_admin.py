"""
Admin endpoints for external platform management (Phase 10.3).

Requires admin authentication (X-Admin-Key or Clerk JWT with admin role).
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.admin_auth import require_admin, AdminActor
from backend.features.external.api_keys import (
    create_api_key,
    revoke_api_key,
    list_api_keys,
    rotate_api_key,
    VALID_SCOPES,
    RATE_LIMIT_TIERS,
)
from backend.features.external.webhooks import (
    create_webhook_subscription,
    list_webhook_subscriptions,
    delete_webhook_subscription,
)


router = APIRouter(prefix="/v1/admin/external", tags=["admin-external"])


# --- API Key Management ---


class CreateApiKeyRequest(BaseModel):
    owner_user_id: str
    scopes: List[str]
    tier: str = "free"
    expires_in_days: Optional[int] = None
    ip_allowlist: Optional[List[str]] = None


class CreateApiKeyResponse(BaseModel):
    id: str
    key_id: str
    full_key: str  # Only shown once!
    scopes: List[str]
    tier: str
    expires_at: Optional[str]
    ip_allowlist: List[str]


@router.post("/keys", response_model=CreateApiKeyResponse)
async def create_external_api_key(
    request: CreateApiKeyRequest,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create new external API key for user."""
    # Validate scopes
    invalid_scopes = [s for s in request.scopes if s not in VALID_SCOPES]
    if invalid_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scopes: {invalid_scopes}. Valid scopes: {VALID_SCOPES}"
        )
    
    # Validate tier
    if request.tier not in RATE_LIMIT_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier: {request.tier}. Valid tiers: {list(RATE_LIMIT_TIERS.keys())}"
        )
    
    key_info = create_api_key(
        db,
        owner_user_id=request.owner_user_id,
        scopes=request.scopes,
        tier=request.tier,
        expires_in_days=request.expires_in_days,
        ip_allowlist=request.ip_allowlist,
    )
    
    return CreateApiKeyResponse(**key_info)


class RevokeApiKeyResponse(BaseModel):
    success: bool
    message: str


class RotateApiKeyRequest(BaseModel):
    preserve_key_id: bool = True
    ip_allowlist: Optional[List[str]] = None
    expires_in_days: Optional[int] = None


class RotateApiKeyResponse(BaseModel):
    key_id: str
    full_key: str  # Only shown once!
    owner_user_id: str
    scopes: List[str]
    tier: str
    expires_at: Optional[str]
    ip_allowlist: List[str]


@router.post("/keys/{key_id}/revoke", response_model=RevokeApiKeyResponse)
async def revoke_external_api_key(
    key_id: str,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Revoke external API key."""
    success = revoke_api_key(db, key_id, owner_user_id=None)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return RevokeApiKeyResponse(
        success=True,
        message=f"API key {key_id} revoked successfully"
    )


@router.post("/keys/{key_id}/rotate", response_model=RotateApiKeyResponse)
async def rotate_external_api_key(
    key_id: str,
    request: RotateApiKeyRequest,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Rotate external API key (optionally preserving key_id)."""
    rotated = rotate_api_key(
        db,
        key_id,
        preserve_key_id=request.preserve_key_id,
        ip_allowlist=request.ip_allowlist,
        expires_in_days=request.expires_in_days,
    )

    if not rotated:
        raise HTTPException(status_code=404, detail="API key not found")

    return RotateApiKeyResponse(
        key_id=rotated["key_id"],
        full_key=rotated["full_key"],
        owner_user_id=rotated["owner_user_id"],
        scopes=rotated["scopes"],
        tier=rotated["tier"],
        expires_at=rotated["expires_at"].isoformat() if rotated.get("expires_at") else None,
        ip_allowlist=rotated.get("ip_allowlist", []),
    )


class ApiKeyListItem(BaseModel):
    id: str
    key_id: str
    scopes: List[str]
    tier: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    ip_allowlist: List[str]


class ListApiKeysResponse(BaseModel):
    keys: List[ApiKeyListItem]


class RotateApiKeyRequest(BaseModel):
    preserve_key_id: bool = True
    ip_allowlist: Optional[List[str]] = None
    expires_in_days: Optional[int] = None


class RotateApiKeyResponse(BaseModel):
    key_id: str
    full_key: str
    owner_user_id: str
    scopes: List[str]
    tier: str
    expires_at: Optional[str]
    ip_allowlist: List[str]


@router.get("/keys/{owner_user_id}", response_model=ListApiKeysResponse)
async def list_user_api_keys(
    owner_user_id: str,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all API keys for a user."""
    keys = list_api_keys(db, owner_user_id)
    return ListApiKeysResponse(keys=[ApiKeyListItem(**k) for k in keys])


# --- Webhook Management ---


class CreateWebhookRequest(BaseModel):
    owner_user_id: str
    url: HttpUrl
    events: List[str]


class CreateWebhookResponse(BaseModel):
    id: str
    url: str
    secret: str  # Only shown once!
    events: List[str]


@router.post("/webhooks", response_model=CreateWebhookResponse)
async def create_webhook(
    request: CreateWebhookRequest,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create webhook subscription for user."""
    valid_events = ["draft.published", "ring.passed", "ring.earned", "enforcement.failed"]
    invalid_events = [e for e in request.events if e not in valid_events]
    
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}. Valid events: {valid_events}"
        )
    
    webhook_info = create_webhook_subscription(
        db,
        owner_user_id=request.owner_user_id,
        url=str(request.url),
        events=request.events,
    )
    
    return CreateWebhookResponse(**webhook_info)


class WebhookListItem(BaseModel):
    id: str
    url: str
    events: List[str]
    is_active: bool
    created_at: str
    last_delivered_at: Optional[str]


class ListWebhooksResponse(BaseModel):
    webhooks: List[WebhookListItem]


@router.get("/webhooks/{owner_user_id}", response_model=ListWebhooksResponse)
async def list_user_webhooks(
    owner_user_id: str,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List webhook subscriptions for a user."""
    webhooks = list_webhook_subscriptions(db, owner_user_id)
    return ListWebhooksResponse(webhooks=[WebhookListItem(**w) for w in webhooks])


class DeleteWebhookResponse(BaseModel):
    success: bool
    message: str


@router.delete("/webhooks/{webhook_id}", response_model=DeleteWebhookResponse)
async def delete_user_webhook(
    webhook_id: str,
    owner_user_id: str,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete webhook subscription."""
    success = delete_webhook_subscription(db, webhook_id, owner_user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return DeleteWebhookResponse(
        success=True,
        message=f"Webhook {webhook_id} deleted successfully"
    )
