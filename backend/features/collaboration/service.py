"""
backend/features/collaboration/service.py
Collaboration service: create drafts, append segments, pass ring (idempotent).
All operations emit events following .ai/events.md pattern.
"""

import uuid
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import hashlib
from backend.models.collab import (
    CollabDraft,
    CollabDraftRequest,
    DraftSegment,
    RingState,
    DraftStatus,
    SegmentAppendRequest,
    RingPassRequest,
    SmartRingPassRequest,
    SmartPassStrategy,
)
from backend.features.collaboration.persistence import DraftPersistence
from backend.core.config import settings
from backend.core.errors import NotFoundError, PermissionError, ValidationError, RingRequiredError, LimitExceededError, ConflictError
from backend.features.audit.service import record_audit_event
from backend.core.logging import get_request_id, log_event
from backend.core.metrics import collab_mutations_total, ws_messages_sent_total
from backend.core.tracing import start_span

# Smart pass idempotency: store (draft_id, user_id, idempotency_key) -> selection decision
_smart_pass_idempotency: Dict[str, Dict[str, Any]] = {}

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


def emit_event(event_type: str, payload: dict, request_id: Optional[str] = None) -> None:
    """
    Emit event to WebSocket hub.
    
    Phase 6.2: Broadcasts to all connected clients watching the draft.
    Runs async broadcast in the background without blocking the REST response.
    """
    import asyncio
    from datetime import datetime, timezone
    from backend.realtime.hub import hub
    from backend.core.logging import get_request_id
    
    # Extract draft_id from payload
    draft_id = payload.get("draft_id")
    if not draft_id:
        print(f"[COLLAB EVENT] Warning: No draft_id in event payload")
        return
    
    # Build WebSocket event message
    event_message = {
        "type": event_type,
        "draft_id": draft_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id or get_request_id(default="n/a"),
        "data": payload,
    }

    # Count broadcast intent (per event_type)
    try:
        ws_messages_sent_total.inc(labels={"event_type": event_type})
    except Exception:
        pass
    
    # Broadcast asynchronously (don't block REST response)
    try:
        # Try to get the current event loop and schedule broadcast
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, schedule as task
            asyncio.create_task(hub.broadcast(draft_id, event_message))
        else:
            # Fallback: run in executor
            loop.run_until_complete(hub.broadcast(draft_id, event_message))
    except RuntimeError:
        # No event loop, create one
        asyncio.run(hub.broadcast(draft_id, event_message))
    
    # Log event
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

    # Phase 4.2: Hard enforcement (no partial state on block)
    from backend.features.entitlements.service import enforce_entitlement
    enforce_entitlement(user_id, "drafts.max", requested=1, usage_key="drafts.created")
    
    with start_span("collab.create_draft", {"user_id": user_id}):
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

        # Phase 4.1: Emit usage event
        try:
            from backend.features.usage.service import emit_usage_event
            emit_usage_event(
                user_id=user_id,
                usage_key="drafts.created",
                occurred_at=now,
                metadata={"draft_id": draft_id}
            )
        except Exception:
            # Graceful degradation if usage tracking fails
            pass

        # Audit event
        record_audit_event(
            action="collab.create_draft",
            user_id=user_id,
            draft_id=draft_id,
            request_id=get_request_id(),
            metadata={"title": request.title, "platform": request.platform},
        )

        collab_mutations_total.inc(labels={"type": "create_draft"})

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
        raise RingRequiredError(
            f"User {user_id} must hold the ring to append segments to draft {draft_id}"
        )

    if settings.MAX_SEGMENTS_PER_DRAFT and settings.MAX_SEGMENTS_PER_DRAFT > 0:
        if len(draft.segments) >= settings.MAX_SEGMENTS_PER_DRAFT:
            log_event(
                "warning",
                "collab.segments_soft_cap",
                request_id=get_request_id(),
                user_id=user_id,
                draft_id=draft_id,
                event_type="collab.segments_soft_cap",
                extra={"cap": settings.MAX_SEGMENTS_PER_DRAFT, "current": len(draft.segments)},
            )

    # Check idempotency - use composite key (draft_id:idempotency_key)
    composite_idempotency_key = f"{draft_id}:{request.idempotency_key}"
    persistence = _get_persistence()
    with start_span("collab.append_segment", {"draft_id": draft_id, "user_id": user_id}):
        if persistence:
            is_dupe = persistence.check_idempotency(composite_idempotency_key)
            if is_dupe:
                # Idempotent: already appended, return current state
                return draft
        else:
            if composite_idempotency_key in _idempotency_keys:
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
        # Phase 4.2: Hard enforcement (segments)
        from backend.features.entitlements.service import enforce_entitlement
        enforce_entitlement(user_id, "segments.max", requested=1, usage_key="segments.appended", now=now)
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
            collaborators=draft.collaborators,
            pending_invites=draft.pending_invites,
            created_at=draft.created_at,
            updated_at=now,
            target_publish_at=draft.target_publish_at,
        )

        # Store updated draft
        if persistence:
            persistence.append_segment(draft_id, segment)
            persistence.record_idempotency(composite_idempotency_key, scope="collab")
            # Reload draft to get updated state
            updated_draft = persistence.get_draft(draft_id)
        else:
            _drafts_store[draft_id] = updated_draft
            _idempotency_keys.add(composite_idempotency_key)

        # Phase 4.1: Emit usage event
        try:
            from backend.features.usage.service import emit_usage_event
            emit_usage_event(
                user_id=user_id,
                usage_key="segments.appended",
                occurred_at=now,
                metadata={"draft_id": draft_id, "segment_id": segment.segment_id}
            )
        except Exception:
            # Graceful degradation if usage tracking fails
            pass

        record_audit_event(
            action="collab.append_segment",
            user_id=user_id,
            draft_id=draft_id,
            request_id=get_request_id(),
            metadata={
                "segment_id": segment.segment_id,
                "content_len": len(request.content or ""),
                "idempotency_key": request.idempotency_key,
            },
        )

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

        collab_mutations_total.inc(labels={"type": "append_segment"})

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

    with start_span("collab.pass_ring", {"draft_id": draft_id, "from_user_id": from_user_id, "to_user_id": request.to_user_id}):
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
            is_dupe = persistence.check_idempotency(request.idempotency_key)
            if is_dupe:
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
            collaborators=draft.collaborators,
            pending_invites=draft.pending_invites,
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

        record_audit_event(
            action="collab.pass_ring",
            user_id=from_user_id,
            draft_id=draft_id,
            request_id=get_request_id(),
            metadata={
                "to_user_id": request.to_user_id,
                "idempotency_key": request.idempotency_key,
            },
        )

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

        collab_mutations_total.inc(labels={"type": "pass_ring"})

        return updated_draft


def _compute_user_last_activity(draft: CollabDraft, user_id: str) -> Optional[datetime]:
    """Compute last activity timestamp for a user within the draft.
    Activity considered: last segment authored or last time they held the ring (approx).
    If no activity, returns None.
    """
    # Last segment time
    seg_times = [seg.created_at for seg in draft.segments if (seg.author_user_id or seg.user_id) == user_id]
    last_seg = max(seg_times) if seg_times else None
    # We don't have per-user hold timestamps; approximate using draft.ring_state.last_passed_at
    # If user is current holder, treat last activity as now-ish: draft.updated_at
    if draft.ring_state.current_holder_id == user_id:
        holder_time = draft.updated_at
    else:
        holder_time = None
    # Choose max of known signals
    candidates = [t for t in [last_seg, holder_time] if t is not None]
    return max(candidates) if candidates else None


def _select_next_holder(draft: CollabDraft, strategy: SmartPassStrategy) -> Tuple[Optional[str], str]:
    """Select next ring holder based on strategy. Returns (user_id, reason).
    Candidates: creator + accepted collaborators, excluding current holder.
    Deterministic tie-breaking by lexicographic user_id.
    """
    current = draft.ring_state.current_holder_id
    candidates = [draft.creator_id] + list(draft.collaborators)
    candidates = [u for u in candidates if u != current]
    # No candidates available
    if not candidates:
        return None, "No eligible recipients (only current holder present)."

    # Deterministic ordering
    candidates_sorted = sorted(candidates)

    if strategy == SmartPassStrategy.BACK_TO_CREATOR:
        # If creator is not current holder, choose creator; else choose first collaborator deterministically
        if draft.creator_id != current:
            return draft.creator_id, "Back to creator: returning the ring to the draft owner."
        # Creator holds ring; pick first collaborator deterministically
        first_collab = next((u for u in candidates_sorted if u != draft.creator_id), None)
        if first_collab:
            return first_collab, "Creator already holds ring; selecting first collaborator."
        return None, "No collaborators to pass to."

    if strategy in (SmartPassStrategy.MOST_INACTIVE, SmartPassStrategy.BEST_NEXT):
        # BEST_NEXT falls back to MOST_INACTIVE deterministically if AI not active at service level
        inactivity_scores = []
        for u in candidates_sorted:
            last_act = _compute_user_last_activity(draft, u)
            # None means never active → highest inactivity (prefer)
            # We sort by (has_activity, last_activity_time) ascending where has_activity False comes first
            has_act = 1 if last_act is not None else 0
            inactivity_scores.append((has_act, last_act or datetime.min.replace(tzinfo=timezone.utc), u))
        # Sort by has_activity (0 first), then by oldest last activity, then by user_id lexicographically
        inactivity_scores.sort(key=lambda x: (x[0], x[1], x[2]))
        chosen = inactivity_scores[0][2]
        reason = (
            "Most inactive: selecting a collaborator with the oldest or no activity."
            if strategy == SmartPassStrategy.MOST_INACTIVE
            else "Best next (deterministic): selecting least-active collaborator as fallback."
        )
        return chosen, reason

    if strategy == SmartPassStrategy.ROUND_ROBIN:
        # Deterministic round-robin over sorted candidates based on current holder position
        # Find current in full ring including current to compute next index
        full_ring = sorted([draft.creator_id] + list(draft.collaborators))
        if current not in full_ring:
            full_ring.append(current)
            full_ring = sorted(full_ring)
        idx = full_ring.index(current)
        # Next in ring; skip current if candidates exclude them
        for offset in range(1, len(full_ring) + 1):
            next_user = full_ring[(idx + offset) % len(full_ring)]
            if next_user in candidates_sorted:
                return next_user, "Round robin: selecting the next collaborator in order."
        # Fallback to first candidate
        return candidates_sorted[0], "Round robin fallback: selecting first eligible collaborator."

    # Unknown strategy (should not happen)
    return candidates_sorted[0], "Default selection: first eligible collaborator."


def pass_ring_smart(draft_id: str, from_user_id: str, request: SmartRingPassRequest) -> Dict[str, Any]:
    """Smart ring passing: select recipient per strategy, then pass via standard flow.
    
    Enforces: caller must hold ring. If no eligible candidates, raises 409 ConflictError.
    
    Idempotency: same (draft_id, from_user_id, idempotency_key) returns cached result.
    
    Args:
        draft_id: Draft UUID
        from_user_id: User passing the ring (must be current holder)
        request: SmartRingPassRequest with strategy and idempotency_key
    
    Returns:
        Dict with:
        - draft: Updated CollabDraft
        - selected_to_user_id: User ID selected
        - strategy_used: Strategy name
        - reasoning: Explanation
        - metrics: Candidate count and metadata
    
    Raises:
        NotFoundError: Draft not found
        PermissionError: Caller doesn't hold ring
        ConflictError (409): No eligible candidates
    """
    # Check idempotency FIRST (before permission check)
    # This allows replaying the same idempotency key even if the state has changed
    idempotency_cache_key = f"{draft_id}:{from_user_id}:{request.idempotency_key}"
    if idempotency_cache_key in _smart_pass_idempotency:
        return _smart_pass_idempotency[idempotency_cache_key]
    
    draft = get_draft(draft_id)
    if not draft:
        raise NotFoundError(f"Draft {draft_id} not found")

    if draft.ring_state.current_holder_id != from_user_id:
        raise PermissionError(f"User {from_user_id} is not ring holder for draft {draft_id}")

    with start_span("collab.pass_ring_smart", {
        "draft_id": draft_id,
        "from_user_id": from_user_id,
        "strategy": request.strategy.value,
        "allow_ai": request.allow_ai
    }):
        to_user_id, reason = _select_next_holder(draft, request.strategy)
        if not to_user_id:
            raise ConflictError(
                "No eligible collaborators to pass the ring to.",
                code="no_collaborator_candidates",
                status_code=409,
                request_id=get_request_id()
            )

        # Count eligible candidates for metrics
        all_candidates = [draft.creator_id] + list(draft.collaborators)
        eligible_candidates = [u for u in all_candidates if u != draft.ring_state.current_holder_id]

        # Reuse standard pass_ring for ring holder update, idempotency, audit, events
        updated = pass_ring(draft_id, from_user_id, RingPassRequest(
            to_user_id=to_user_id,
            idempotency_key=request.idempotency_key
        ))

        # Build response
        result = {
            "draft": updated,
            "selected_to_user_id": to_user_id,
            "strategy_used": request.strategy.value,
            "reasoning": reason,
            "metrics": {
                "strategy": request.strategy.value,
                "candidate_count": len(eligible_candidates),
                "computed_from": "activity_history",
            },
        }

        # Record for idempotency (in-memory, TTL not enforced but acceptable for this session)
        _smart_pass_idempotency[idempotency_cache_key] = result

        # Enhance audit event with strategy details
        record_audit_event(
            action="collab.pass_ring_smart",
            user_id=from_user_id,
            draft_id=draft_id,
            request_id=get_request_id(),
            metadata={
                "to_user_id": to_user_id,
                "strategy": request.strategy.value,
                "allow_ai": request.allow_ai,
                "idempotency_key": request.idempotency_key,
                "candidate_count": len(eligible_candidates),
                "reasoning": reason,
            },
        )

        return result


def add_collaborator(draft_id: str, creator_user_id: str, collaborator_id: str, role: str = "contributor") -> CollabDraft:
    """
    Add a collaborator to a draft (creator only).
    
    Args:
        draft_id: Draft UUID
        creator_user_id: User ID of the creator (must be creator to add collaborators)
        collaborator_id: User ID to add as collaborator
        role: Role (e.g., "contributor", "viewer")
    
    Returns:
        Updated CollabDraft
    
    Raises:
        NotFoundError: If draft not found
        PermissionError: If caller is not the creator
    """
    draft = get_draft(draft_id)
    if not draft:
        raise NotFoundError(f"Draft {draft_id} not found")
    
    # Only creator can add collaborators
    if draft.creator_id != creator_user_id:
        raise PermissionError(f"Only draft creator can add collaborators")

    if settings.MAX_COLLABORATORS_PER_DRAFT and settings.MAX_COLLABORATORS_PER_DRAFT > 0:
        if len(draft.collaborators) >= settings.MAX_COLLABORATORS_PER_DRAFT:
            raise LimitExceededError(
                f"Collaborator cap reached for draft {draft_id}",
                request_id=get_request_id(),
            )
    
    with start_span("collab.add_collaborator", {"draft_id": draft_id, "creator_user_id": creator_user_id, "collaborator_id": collaborator_id}):
        # Add via persistence
        persistence = _get_persistence()
        if persistence:
            persistence.add_collaborator(draft_id, collaborator_id, role)
            # Reload draft to get updated collaborators
            draft = persistence.get_draft(draft_id)
        else:
            # In-memory fallback
            pass

        record_audit_event(
            action="collab.add_collaborator",
            user_id=creator_user_id,
            draft_id=draft_id,
            request_id=get_request_id(),
            metadata={
                "collaborator_id": collaborator_id,
                "role": role,
            },
        )
        
        # Emit event
        emit_event(
            "collab.collaborator_added",
            {
                "draft_id": draft_id,
                "collaborator_id": collaborator_id,
                "role": role,
            },
        )

        collab_mutations_total.inc(labels={"type": "add_collaborator"})
        
        return draft


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
