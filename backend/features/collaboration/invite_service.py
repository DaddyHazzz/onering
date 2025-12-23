"""
backend/features/collaboration/invite_service.py
Invite creation, acceptance, revocation with idempotency and token security.
"""

import hashlib
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from backend.models.invite import (
    CollaborationInvite,
    InviteStatus,
    InviteSummary,
    CreateInviteRequest,
    AcceptInviteRequest,
    RevokeInviteRequest,
)
from backend.features.collaboration.identity import (
    resolve_handle_to_user_id,
    is_valid_user_id,
    is_valid_handle,
)

# STUB: In-memory store for Phase 3.2. Replace with PostgreSQL in Phase 3.5.
_invites_store: dict[str, CollaborationInvite] = {}
_invite_idempotency_keys: set[str] = set()

# STUB: Fixed internal salt for token generation in tests.
# In production with real persistence, use an env var: INVITE_TOKEN_SALT
_INTERNAL_TOKEN_SALT = "onering_invite_salt_test_only_change_in_prod"


def _generate_token_and_hash(invite_id: str) -> Tuple[str, str]:
    """
    Generate a deterministic token and its hash.

    For MVP: Token derived from invite_id + salt (deterministic).
    In production: Use secure random token + env var salt.

    Args:
        invite_id: UUID of invite

    Returns:
        (token, token_hash): Raw token (returned once to user) and hash (stored)
    """
    # Deterministic token generation from invite_id + salt
    # Same invite_id always produces same token
    token_input = f"{invite_id}:{_INTERNAL_TOKEN_SALT}"
    token_hash_obj = hashlib.sha256(token_input.encode())
    token = token_hash_obj.hexdigest()[:32]  # 32 chars (16 bytes hex)

    # Hash for storage
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return token, token_hash


def _verify_token(token: str, token_hash: str) -> bool:
    """Verify raw token matches hash"""
    computed_hash = hashlib.sha256(token.encode()).hexdigest()
    return computed_hash == token_hash


def _compute_status(invite: CollaborationInvite, now: Optional[datetime] = None) -> InviteStatus:
    """
    Compute current status of invite (account for expiration).

    Args:
        invite: The invite
        now: Current time (defaults to utcnow)

    Returns:
        Current status (pending, accepted, revoked, or expired)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # If explicitly revoked, stay revoked
    if invite.status == InviteStatus.REVOKED:
        return InviteStatus.REVOKED

    # If accepted, stay accepted
    if invite.status == InviteStatus.ACCEPTED:
        return InviteStatus.ACCEPTED

    # Check expiration
    if invite.status == InviteStatus.PENDING and now > invite.expires_at:
        return InviteStatus.EXPIRED

    return invite.status


def create_invite(
    draft_id: str,
    created_by_user_id: str,
    request: CreateInviteRequest,
) -> Tuple[CollaborationInvite, str]:
    """
    Create an invite to join draft.

    Idempotent: Same idempotency_key returns same invite (no duplicate).

    Args:
        draft_id: Target draft UUID
        created_by_user_id: User creating the invite
        request: CreateInviteRequest with target + expires_in_hours + idempotency_key

    Returns:
        (invite, token): The invite object and raw token (only returned once)

    Raises:
        ValueError: Invalid target, invalid request
    """
    # Idempotency check
    if request.idempotency_key in _invite_idempotency_keys:
        # Already created; find and return it
        for invite in _invites_store.values():
            if (
                invite.draft_id == draft_id
                and invite.idempotency_key == request.idempotency_key
            ):
                # Regenerate token (for idempotent response)
                token, _ = _generate_token_and_hash(invite.invite_id)
                return invite, token
        raise ValueError("Idempotency key mismatch")

    # Resolve target
    if request.target_handle and request.target_user_id:
        raise ValueError("Specify either target_handle OR target_user_id, not both")

    target_user_id: str
    target_handle: Optional[str] = None

    if request.target_handle:
        if not is_valid_handle(request.target_handle):
            raise ValueError(f"Invalid handle: {request.target_handle}")
        target_user_id = resolve_handle_to_user_id(request.target_handle)
        target_handle = request.target_handle
    elif request.target_user_id:
        if not is_valid_user_id(request.target_user_id):
            raise ValueError(f"Invalid user_id: {request.target_user_id}")
        target_user_id = request.target_user_id
    else:
        raise ValueError("Must specify target_handle or target_user_id")

    # Cannot invite yourself
    if target_user_id == created_by_user_id:
        raise ValueError("Cannot invite yourself")

    # Generate invite
    invite_id = str(uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=request.expires_in_hours)

    token, token_hash = _generate_token_and_hash(invite_id)

    invite = CollaborationInvite(
        invite_id=invite_id,
        draft_id=draft_id,
        created_by_user_id=created_by_user_id,
        target_user_id=target_user_id,
        target_handle=target_handle,
        status=InviteStatus.PENDING,
        created_at=now,
        expires_at=expires_at,
        token_hash=token_hash,
        token_hint=token[-6:],  # Last 6 chars of token
        idempotency_key=request.idempotency_key,
    )

    # Store
    _invites_store[invite_id] = invite
    _invite_idempotency_keys.add(request.idempotency_key)

    # Emit event
    emit_event(
        "collab.invite_created",
        {
            "invite_id": invite_id,
            "draft_id": draft_id,
            "created_by_user_id": created_by_user_id,
            "target_user_id": target_user_id,
            "target_handle": target_handle,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        },
    )

    return invite, token


def accept_invite(
    invite_id: str,
    user_id: str,
    request: AcceptInviteRequest,
) -> CollaborationInvite:
    """
    Accept an invite (user becomes collaborator on draft).

    Idempotent: Same idempotency_key returns same result (no duplicate accept).

    Args:
        invite_id: ID of invite to accept
        user_id: User accepting the invite
        request: AcceptInviteRequest with token + idempotency_key

    Returns:
        Updated invite

    Raises:
        ValueError: Invalid token, expired, wrong user, etc.
    """
    # Idempotency check
    if request.idempotency_key in _invite_idempotency_keys:
        invite = _invites_store.get(invite_id)
        if invite and invite.status == InviteStatus.ACCEPTED:
            return invite
        # If not found or not accepted, fall through to normal checks

    invite = _invites_store.get(invite_id)
    if not invite:
        raise ValueError(f"Invite not found: {invite_id}")

    # Verify token
    if not _verify_token(request.token, invite.token_hash or ""):
        raise ValueError("Invalid token")

    # Verify target user
    if user_id != invite.target_user_id:
        raise ValueError(f"This invite is for {invite.target_user_id}, not {user_id}")

    # Check status
    now = datetime.now(timezone.utc)
    current_status = _compute_status(invite, now)

    if current_status == InviteStatus.REVOKED:
        raise ValueError("Invite has been revoked")
    if current_status == InviteStatus.EXPIRED:
        raise ValueError("Invite has expired")
    if current_status == InviteStatus.ACCEPTED:
        # Already accepted; idempotent return
        _invite_idempotency_keys.add(request.idempotency_key)
        return invite

    # Ensure user exists in User domain
    try:
        from backend.features.users.service import get_or_create_user
        get_or_create_user(user_id)
    except Exception:
        pass

    # Enforce collaborator entitlement on inviter (owner)
    from backend.features.entitlements.service import enforce_entitlement
    enforce_entitlement(
        invite.created_by_user_id,
        "collaborators.max",
        requested=1,
        usage_key="collaborators.added",
        now=now,
    )

    # Accept the invite
    accepted_invite = CollaborationInvite(
        invite_id=invite.invite_id,
        draft_id=invite.draft_id,
        created_by_user_id=invite.created_by_user_id,
        target_user_id=invite.target_user_id,
        target_handle=invite.target_handle,
        status=InviteStatus.ACCEPTED,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        accepted_at=now,
        token_hash=invite.token_hash,
        token_hint=invite.token_hint,
        idempotency_key=request.idempotency_key,
    )

    _invites_store[invite_id] = accepted_invite
    _invite_idempotency_keys.add(request.idempotency_key)

    # Add user as collaborator (persist to DB if enabled)
    import os
    if os.getenv('DATABASE_URL'):
        from backend.features.collaboration.persistence import DraftPersistence
        DraftPersistence.add_collaborator(invite.draft_id, user_id)
    else:
        # In-memory mode: add to draft.collaborators
        from backend.features.collaboration.service import _drafts_store
        draft = _drafts_store.get(invite.draft_id)
        if draft and user_id not in draft.collaborators:
            draft.collaborators.append(user_id)

    # Phase 4.1: Emit usage event (for the inviter, not the accepter)
    try:
        from backend.features.usage.service import emit_usage_event
        emit_usage_event(
            user_id=invite.created_by_user_id,
            usage_key="collaborators.added",
            occurred_at=now,
            metadata={"draft_id": invite.draft_id, "collaborator_id": user_id}
        )
    except Exception:
        # Graceful degradation if usage tracking fails
        pass

    # Emit event
    emit_event(
        "collab.invite_accepted",
        {
            "invite_id": invite_id,
            "draft_id": invite.draft_id,
            "user_id": user_id,
            "created_by_user_id": invite.created_by_user_id,
            "accepted_at": now.isoformat(),
        },
    )

    return accepted_invite


def revoke_invite(
    invite_id: str,
    requester_user_id: str,
    request: RevokeInviteRequest,
) -> CollaborationInvite:
    """
    Revoke an invite.

    Only draft owner (creator) can revoke (simplified MVP).
    Idempotent: Same idempotency_key returns same result.

    Args:
        invite_id: ID of invite to revoke
        requester_user_id: User requesting revocation
        request: RevokeInviteRequest with idempotency_key

    Returns:
        Updated invite

    Raises:
        ValueError: Not authorized, not found, etc.
    """
    # Idempotency check
    if request.idempotency_key in _invite_idempotency_keys:
        invite = _invites_store.get(invite_id)
        if invite and invite.status == InviteStatus.REVOKED:
            return invite

    invite = _invites_store.get(invite_id)
    if not invite:
        raise ValueError(f"Invite not found: {invite_id}")

    # Only creator can revoke (in MVP)
    if requester_user_id != invite.created_by_user_id:
        raise PermissionError(f"Only {invite.created_by_user_id} can revoke this invite")

    # Revoke
    revoked_invite = CollaborationInvite(
        invite_id=invite.invite_id,
        draft_id=invite.draft_id,
        created_by_user_id=invite.created_by_user_id,
        target_user_id=invite.target_user_id,
        target_handle=invite.target_handle,
        status=InviteStatus.REVOKED,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        token_hash=invite.token_hash,
        token_hint=invite.token_hint,
        idempotency_key=request.idempotency_key,
    )

    _invites_store[invite_id] = revoked_invite
    _invite_idempotency_keys.add(request.idempotency_key)

    # Emit event
    emit_event(
        "collab.invite_revoked",
        {
            "invite_id": invite_id,
            "draft_id": invite.draft_id,
            "revoked_by_user_id": requester_user_id,
        },
    )

    return revoked_invite


def get_invite(invite_id: str) -> Optional[CollaborationInvite]:
    """Fetch invite by ID (safe version, no token_hash exposed)"""
    invite = _invites_store.get(invite_id)
    if not invite:
        return None
    # Return invite as-is (token_hash is internal; API layer filters it)
    return invite


def get_invites_for_draft(draft_id: str) -> List[InviteSummary]:
    """Get all invites for a draft (safe summaries)"""
    invites = [
        inv
        for inv in _invites_store.values()
        if inv.draft_id == draft_id
    ]
    return [
        InviteSummary(
            invite_id=inv.invite_id,
            draft_id=inv.draft_id,
            target_user_id=inv.target_user_id,
            target_handle=inv.target_handle,
            status=_compute_status(inv),
            created_at=inv.created_at,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            token_hint=inv.token_hint,
            created_by_user_id=inv.created_by_user_id,
        )
        for inv in invites
    ]


def emit_event(event_type: str, payload: dict) -> None:
    """
    Emit invite-related event.

    STUB: Prints to stdout. Real impl (Phase 3.5+) uses event bus.
    """
    print(f"[COLLAB EVENT] {event_type}: {payload}")


def clear_store() -> None:
    """Clear all invites (for testing)"""
    global _invites_store, _invite_idempotency_keys
    _invites_store.clear()
    _invite_idempotency_keys.clear()
