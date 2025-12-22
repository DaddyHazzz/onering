"""
backend/features/collaboration/service.py
Collaboration service: create drafts, append segments, pass ring (idempotent).
All operations emit events following .ai/events.md pattern.
"""

import uuid
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import hashlib
from backend.models.collab import (
    CollabDraft,
    CollabDraftRequest,
    DraftSegment,
    RingState,
    DraftStatus,
    SegmentAppendRequest,
    RingPassRequest,
)
from backend.features.collaboration.persistence import DraftPersistence
from backend.core.errors import NotFoundError, PermissionError, ValidationError

# In-memory stub store (fallback when DB not available)
_drafts_store: Dict[str, CollabDraft] = {}
_idempotency_keys: set = set()  # Track seen idempotency keys

# Persistence layer selector
def _use_persistence() -> bool:
    """Check if we should use DB persistence."""
    return os.getenv('DATABASE_URL') is not None

def _get_persistence():
    """Get persistence layer if enabled."""
    return DraftPersistence() if _use_persistence() else None


def emit_event(event_type: str, payload: dict) -> None:
    """Emit event (stub; real impl would publish to event bus)"""
    print(f"[COLLAB EVENT] {event_type}: {payload}")


def display_for_user(user_id: str) -> str:
    """Generate deterministic display name for user (Phase 3.3a)"""
    hash_obj = hashlib.sha1(user_id.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    return f"@u_{hash_hex[-6:]}"


def compute_metrics(
    draft: CollabDraft, 
    now: Optional[datetime] = None
) -> Dict[str, any]:
    """Compute ring velocity metrics (Phase 3.3a)
    
    Args:
        draft: CollabDraft to compute metrics for
        now: Optional fixed timestamp for deterministic testing
    
    Returns:
        {
            "contributorsCount": int,
            "ringPassesLast24h": int,
            "avgMinutesBetweenPasses": float | None,
            "lastActivityAt": str (ISO)
        }
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Contributors: unique author_user_id from segments + creator
    author_ids = set([draft.creator_id])
    for seg in draft.segments:
        if seg.author_user_id:
            author_ids.add(seg.author_user_id)
        else:
            author_ids.add(seg.user_id)  # Fallback for old segments
    contributors_count = len(author_ids)
    
    # Ring passes last 24h: Count passes within 24h window
    # Note: holders_history includes initial holder, so passes = len(history) - 1
    # But we need timestamps to filter by 24h
    # Since we don't store individual pass timestamps in history (only last passed_at),
    # we'll approximate: if draft was updated within 24h and has multiple holders, count as active
    # For accurate count, we'd need full ring pass history with timestamps
    # For now: simple heuristic
    twenty_four_hours_ago = now - timedelta(hours=24)
    ring_passes_last_24h = 0
    
    # Check if draft has recent activity
    if draft.ring_state.last_passed_at:
        if draft.ring_state.last_passed_at >= twenty_four_hours_ago:
            # At least one pass in last 24h
            ring_passes_last_24h = max(1, len(draft.ring_state.holders_history) - 1)
    
    # Avg minutes between passes: Use last N passes (up to 10)
    # Since we don't have full timestamp history, use approximation:
    # If we have segments with created_at, compute intervals
    avg_minutes_between_passes = None
    if len(draft.ring_state.holders_history) >= 2:
        # Simple approximation: time from draft creation to last pass / number of passes
        total_passes = len(draft.ring_state.holders_history) - 1
        if total_passes > 0 and draft.ring_state.last_passed_at:
            time_span = draft.ring_state.last_passed_at - draft.created_at
            avg_minutes_between_passes = round(time_span.total_seconds() / 60 / total_passes, 1)
    
    # Last activity: max of last segment created_at, last_passed_at, draft created_at
    last_activity = draft.created_at
    if draft.segments:
        last_segment_time = max(seg.created_at for seg in draft.segments)
        if last_segment_time > last_activity:
            last_activity = last_segment_time
    if draft.ring_state.last_passed_at and draft.ring_state.last_passed_at > last_activity:
        last_activity = draft.ring_state.last_passed_at
    
    return {
        "contributorsCount": contributors_count,
        "ringPassesLast24h": ring_passes_last_24h,
        "avgMinutesBetweenPasses": avg_minutes_between_passes,
        "lastActivityAt": last_activity.isoformat(),
    }


def create_draft(user_id: str, request: CollabDraftRequest) -> CollabDraft:
    """Create new collaboration draft"""
    # Ensure user exists in User domain
    try:
        from backend.features.users.service import get_or_create_user
        get_or_create_user(user_id)
    except Exception:
        pass
    draft_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Initialize ring state
    ring_state = RingState(
        draft_id=draft_id,
        current_holder_id=user_id,
        holders_history=[user_id],
        passed_at=now,
        last_passed_at=now,  # Phase 3.3a: Track initial pass time
    )

    # Initialize segments
    segments: List[DraftSegment] = []
    if request.initial_segment:
        segment = DraftSegment(
            segment_id=str(uuid.uuid4()),
            draft_id=draft_id,
            user_id=user_id,
            content=request.initial_segment,
            created_at=now,
            segment_order=0,
            # Phase 3.3a: Attribution for initial segment
            author_user_id=user_id,
            author_display=display_for_user(user_id),
            ring_holder_user_id_at_write=user_id,
            ring_holder_display_at_write=display_for_user(user_id),
        )
        segments.append(segment)

    draft = CollabDraft(
        draft_id=draft_id,
        creator_id=user_id,
        title=request.title,
        platform=request.platform,
        status=DraftStatus.ACTIVE,
        segments=segments,
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )

    # Store (use persistence if available)
    persistence = _get_persistence()
    if persistence:
        persistence.create_draft(draft)
    else:
        _drafts_store[draft_id] = draft

    # Emit event
    emit_event(
        "collab.draft_created",
        {
            "draft_id": draft_id,
            "creator_id": user_id,
            "title": request.title,
            "platform": request.platform,
            "created_at": now.isoformat(),
        },
    )

    return draft


def get_draft(draft_id: str, compute_metrics_flag: bool = True, now: Optional[datetime] = None) -> Optional[CollabDraft]:
    """Fetch draft by ID, optionally with computed metrics (Phase 3.3a)
    
    Args:
        draft_id: Draft UUID
        compute_metrics_flag: If True, compute and attach metrics
        now: Optional fixed timestamp for deterministic testing
    """
    # Get draft from persistence or in-memory
    persistence = _get_persistence()
    if persistence:
        draft = persistence.get_draft(draft_id)
    else:
        draft = _drafts_store.get(draft_id)
    if not draft:
        return None
    
    if compute_metrics_flag:
        metrics = compute_metrics(draft, now=now)
        # Create new draft with metrics (frozen=True requires new instance)
        draft = CollabDraft(
            draft_id=draft.draft_id,
            creator_id=draft.creator_id,
            title=draft.title,
            platform=draft.platform,
            status=draft.status,
            segments=draft.segments,
            ring_state=draft.ring_state,
            collaborators=draft.collaborators,
            pending_invites=draft.pending_invites,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            target_publish_at=draft.target_publish_at,
            metrics=metrics,
        )
    
    return draft


def list_drafts(user_id: str) -> List[CollabDraft]:
    """List all drafts involving user (as creator or contributor)"""
    persistence = _get_persistence()
    if persistence:
        return persistence.list_drafts_by_user(user_id)
    else:
        result = []
        for draft in _drafts_store.values():
            if draft.creator_id == user_id:
                result.append(draft)
            elif any(seg.user_id == user_id for seg in draft.segments):
                result.append(draft)
        return result


def append_segment(
    draft_id: str, user_id: str, request: SegmentAppendRequest
) -> CollabDraft:
    """
    Append segment to draft (idempotent).
    Only ring holder can append.
    """
    draft = get_draft(draft_id)
    if not draft:
        raise NotFoundError(f"Draft {draft_id} not found")

    # Check role: must be owner or collaborator
    is_collaborator = (user_id == draft.creator_id) or (user_id in draft.collaborators)
    if not is_collaborator:
        raise PermissionError(
            f"User {user_id} is not owner/collaborator for draft {draft_id}"
        )
    # Ring holder rule remains: only current holder can append
    if draft.ring_state.current_holder_id != user_id:
        raise PermissionError(
            f"User {user_id} is not ring holder for draft {draft_id}"
        )

    # Check idempotency
    persistence = _get_persistence()
    if persistence:
        if persistence.check_idempotency(request.idempotency_key):
            # Idempotent: already appended, return current state
            return draft
    else:
        if request.idempotency_key in _idempotency_keys:
            # Idempotent: already appended, return current state
            return draft

    # Append segment
    now = datetime.now(timezone.utc)
    # Ensure user exists in User domain
    try:
        from backend.features.users.service import get_or_create_user
        get_or_create_user(user_id)
    except Exception:
        pass
    ring_holder_id = draft.ring_state.current_holder_id
    segment = DraftSegment(
        segment_id=str(uuid.uuid4()),
        draft_id=draft_id,
        user_id=user_id,
        content=request.content,
        created_at=now,
        segment_order=len(draft.segments),
        idempotency_key=request.idempotency_key,
        # Phase 3.3a: Attribution
        author_user_id=user_id,
        author_display=display_for_user(user_id),
        ring_holder_user_id_at_write=ring_holder_id,
        ring_holder_display_at_write=display_for_user(ring_holder_id),
    )

    # Update draft (must create new instance since frozen=True)
    updated_draft = CollabDraft(
        draft_id=draft.draft_id,
        creator_id=draft.creator_id,
        title=draft.title,
        platform=draft.platform,
        status=draft.status,
        segments=draft.segments + [segment],
        ring_state=draft.ring_state,
        created_at=draft.created_at,
        updated_at=now,
        target_publish_at=draft.target_publish_at,
    )

    # Store updated draft
    if persistence:
        persistence.append_segment(draft_id, segment)
        persistence.record_idempotency(request.idempotency_key, scope="collab")
        # Reload draft to get updated state
        updated_draft = persistence.get_draft(draft_id)
    else:
        _drafts_store[draft_id] = updated_draft
        _idempotency_keys.add(request.idempotency_key)

    # Emit event
    emit_event(
        "collab.segment_added",
        {
            "draft_id": draft_id,
            "segment_id": segment.segment_id,
            "user_id": user_id,
            "segment_order": segment.segment_order,
            "created_at": now.isoformat(),
        },
    )

    return updated_draft


def pass_ring(draft_id: str, from_user_id: str, request: RingPassRequest) -> CollabDraft:
    """
    Pass ring to another user (idempotent).
    Only current ring holder can pass.
    Can only pass to: owner OR accepted collaborators.
    """
    draft = get_draft(draft_id)
    if not draft:
        raise NotFoundError(f"Draft {draft_id} not found")

    # Check ownership
    if draft.ring_state.current_holder_id != from_user_id:
        raise PermissionError(
            f"User {from_user_id} is not ring holder for draft {draft_id}"
        )

    # Verify to_user_id is owner or collaborator
    is_valid_recipient = (
        request.to_user_id == draft.creator_id
        or request.to_user_id in draft.collaborators
    )
    if not is_valid_recipient:
        raise PermissionError(
            f"Cannot pass ring to {request.to_user_id} (not owner or collaborator)"
        )

    # Ensure both users exist in User domain
    try:
        from backend.features.users.service import get_or_create_user
        get_or_create_user(from_user_id)
        get_or_create_user(request.to_user_id)
    except Exception:
        pass

    # Check idempotency
    persistence = _get_persistence()
    if persistence:
        if persistence.check_idempotency(request.idempotency_key):
            # Idempotent: ring already passed, return current state
            return draft
    else:
        if request.idempotency_key in _idempotency_keys:
            # Idempotent: ring already passed, return current state
            return draft

    # Pass ring
    now = datetime.now(timezone.utc)
    updated_ring_state = RingState(
        draft_id=draft.ring_state.draft_id,
        current_holder_id=request.to_user_id,
        holders_history=draft.ring_state.holders_history + [request.to_user_id],
        passed_at=now,
        last_passed_at=now,  # Phase 3.3a: Track last pass time
        idempotency_key=request.idempotency_key,
    )

    updated_draft = CollabDraft(
        draft_id=draft.draft_id,
        creator_id=draft.creator_id,
        title=draft.title,
        platform=draft.platform,
        status=draft.status,
        segments=draft.segments,
        ring_state=updated_ring_state,
        created_at=draft.created_at,
        updated_at=now,
        target_publish_at=draft.target_publish_at,
    )

    # Store updated draft and ring pass
    if persistence:
        persistence.pass_ring(draft_id, from_user_id, request.to_user_id, now)
        persistence.record_idempotency(request.idempotency_key, scope="collab")
        # Update draft in DB
        persistence.update_draft(updated_draft)
        # Reload draft to get updated state
        updated_draft = persistence.get_draft(draft_id)
    else:
        _drafts_store[draft_id] = updated_draft
        _idempotency_keys.add(request.idempotency_key)

    # Emit event
    emit_event(
        "collab.ring_passed",
        {
            "draft_id": draft_id,
            "from_user_id": from_user_id,
            "to_user_id": request.to_user_id,
            "passed_at": now.isoformat(),
        },
    )

    return updated_draft


def generate_share_card(draft_id: str, now: Optional[datetime] = None) -> dict:
    """
    Generate deterministic share card for collaborative draft (Phase 3.3c)
    
    Args:
        draft_id: Draft ID
        now: Optional fixed timestamp for deterministic testing
    
    Returns:
        CollabShareCard as dict (safe: no token_hash, emails, or secrets)
    
    Raises:
        ValueError: If draft not found or not a collaboration draft
    """
    from backend.models.sharecard_collab import CollabShareCard, ShareCardMetrics, ShareCardCTA, ShareCardTheme
    
    # Get draft from persistence or in-memory
    persistence = _get_persistence()
    if persistence:
        draft = persistence.get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
    else:
        if draft_id not in _drafts_store:
            raise NotFoundError(f"Draft {draft_id} not found")
        draft = _drafts_store[draft_id]
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Compute metrics (deterministic if now provided)
    metrics_dict = compute_metrics(draft, now)
    
    # Get ring holder display name
    ring_holder_display = display_for_user(draft.ring_state.current_holder_id)
    
    # Build contributors list (max 5, deterministic order)
    # First: creator, then unique authors from segments sorted lexicographically
    contributor_set = {display_for_user(draft.creator_id)}
    for segment in draft.segments:
        if segment.author_user_id:
            contributor_set.add(display_for_user(segment.author_user_id))
    
    # Deterministic ordering: creator first, then others sorted
    creator_display = display_for_user(draft.creator_id)
    others = sorted([c for c in contributor_set if c != creator_display])
    contributors_list = [creator_display] + others
    contributors_list = contributors_list[:5]  # Max 5
    
    # Build subtitle
    subtitle = f"Ring with {ring_holder_display} • {metrics_dict['contributorsCount']} contributors • {metrics_dict['ringPassesLast24h']} passes/24h"
    
    # Build supportive topLine (no shame words)
    top_line = "A collaborative thread in progress."
    
    # Build CTA
    cta = ShareCardCTA(
        label="Join the thread",
        url=f"/dashboard/collab?draftId={draft_id}"
    )
    
    # Build share card
    share_card = CollabShareCard(
        draft_id=draft_id,
        title=f"Collab Thread: {draft.title}",
        subtitle=subtitle,
        metrics=ShareCardMetrics(
            contributors_count=metrics_dict['contributorsCount'],
            ring_passes_last_24h=metrics_dict['ringPassesLast24h'],
            avg_minutes_between_passes=metrics_dict.get('avgMinutesBetweenPasses'),
            segments_count=len(draft.segments),
        ),
        contributors=contributors_list,
        top_line=top_line,
        cta=cta,
        theme=ShareCardTheme(),
        generated_at=now.isoformat(),
    )
    
    return share_card.model_dump()


def clear_store() -> None:
    """Clear all data (testing only)"""
    global _drafts_store, _idempotency_keys
    persistence = _get_persistence()
    if persistence:
        persistence.clear_all()
    _drafts_store.clear()
    _idempotency_keys.clear()
