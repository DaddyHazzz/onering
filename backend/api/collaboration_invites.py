"""
backend/api/collaboration_invites.py
FastAPI routes for collaboration invites.
"""

from fastapi import APIRouter, HTTPException, Query
from backend.models.invite import (
    CreateInviteRequest,
    CreateInviteResponse,
    AcceptInviteRequest,
    RevokeInviteRequest,
    InviteSummary,
)
from backend.features.collaboration.invite_service import (
    create_invite as service_create_invite,
    accept_invite as service_accept_invite,
    revoke_invite as service_revoke_invite,
    get_invite,
    get_invites_for_draft,
)
from backend.features.collaboration.service import get_draft

router = APIRouter()


@router.post("/v1/collab/drafts/{draft_id}/invites")
def create_invite(draft_id: str, user_id: str = Query(...), request: CreateInviteRequest = None):
    """
    Create invite to join draft.

    Only draft owner OR current ring holder can create invites.

    Query params:
        user_id: Requester user ID

    Request body:
        target_handle?: string (e.g., "alice")
        target_user_id?: string (direct user ID)
        expires_in_hours?: int (default 72)
        idempotency_key: UUID

    Returns:
        CreateInviteResponse with share_url, token_hint, etc.
    """
    try:
        # Verify draft exists and user is authorized
        draft = get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        # Only creator or ring holder can invite
        is_authorized = (
            user_id == draft.creator_id
            or user_id == draft.ring_state.current_holder_id
        )
        if not is_authorized:
            raise HTTPException(
                status_code=403,
                detail="Only draft owner or ring holder can create invites"
            )

        # Create invite
        invite, token = service_create_invite(draft_id, user_id, request)

        # Build response
        share_url = f"/collab/invite/{invite.invite_id}?token={token}"
        response = CreateInviteResponse(
            invite_id=invite.invite_id,
            target_user_id=invite.target_user_id,
            target_handle=invite.target_handle,
            status=invite.status,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            token_hint=invite.token_hint or "",
            share_url=share_url,
        )
        return {"success": True, "data": response.model_dump()}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/collab/drafts/{draft_id}/invites")
def list_invites(draft_id: str):
    """
    List all invites for a draft.

    Query params:
        draft_id: Draft UUID

    Returns:
        List of InviteSummary (no token_hash exposed)
    """
    try:
        # Verify draft exists
        draft = get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        # Get invites
        invites = get_invites_for_draft(draft_id)
        # Convert to summaries with draft_id
        summaries = [
            InviteSummary(
                invite_id=inv.invite_id,
                draft_id=inv.draft_id,
                target_user_id=inv.target_user_id,
                target_handle=inv.target_handle,
                status=inv.status,
                created_at=inv.created_at,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
                token_hint=inv.token_hint,
                created_by_user_id=inv.created_by_user_id,
            )
            for inv in invites
        ]
        return {
            "success": True,
            "count": len(summaries),
            "data": [s.model_dump() for s in summaries],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/collab/invites/{invite_id}/accept")
def accept_invite(invite_id: str, user_id: str = Query(...), request: AcceptInviteRequest = None):
    """
    Accept an invite to join draft collaboration.

    Query params:
        user_id: Accepting user ID

    Request body:
        token: Token received at invite creation time
        idempotency_key: UUID

    Returns:
        Updated invite summary
    """
    try:
        # Accept invite
        invite = service_accept_invite(invite_id, user_id, request)

        # Build safe summary with supportive message
        from backend.features.collaboration.service import display_for_user
        creator_display = display_for_user(invite.created_by_user_id)
        message = f"You joined {creator_display}'s thread — your turn is coming."
        
        summary = InviteSummary(
            invite_id=invite.invite_id,
            draft_id=invite.draft_id,
            target_user_id=invite.target_user_id,
            target_handle=invite.target_handle,
            status=invite.status,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at,
            token_hint=invite.token_hint,
            created_by_user_id=invite.created_by_user_id,
            message=message,
        )
        return {"success": True, "data": summary.model_dump()}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/collab/invites/{invite_id}/revoke")
def revoke_invite(
    invite_id: str,
    user_id: str = Query(...),
    request: RevokeInviteRequest = None,
):
    """
    Revoke an invite (only creator).

    Query params:
        user_id: Requester user ID

    Request body:
        idempotency_key: UUID

    Returns:
        Updated invite summary
    """
    try:
        # Revoke invite
        invite = service_revoke_invite(invite_id, user_id, request)

        # Build safe summary
        summary = InviteSummary(
            invite_id=invite.invite_id,
            target_user_id=invite.target_user_id,
            target_handle=invite.target_handle,
            status=invite.status,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at,
            token_hint=invite.token_hint,
            created_by_user_id=invite.created_by_user_id,
        )
        return {"success": True, "data": summary.model_dump()}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
