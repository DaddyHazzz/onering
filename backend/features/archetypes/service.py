"""
Archetype Service — In-Memory Store with Deterministic Fallback

Provides:
- get_snapshot(user_id) -> ArchetypeSnapshot
- record_signal(user_id, signal) -> (snapshot, events)
- recompute_today(user_id, date) -> snapshot

Storage: In-memory dict (acceptable for Phase 2).
Deterministic fallback: if no snapshot exists, compute from streak + momentum.

Idempotency: signals keyed by hash(user_id + date + payload) to prevent double-apply.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from backend.models.archetype import ArchetypeId, ArchetypeSignal, ArchetypeSnapshot
from backend.features.archetypes import engine


# In-memory stores
_snapshots: dict[str, ArchetypeSnapshot] = {}
_applied_signals: set[str] = set()  # idempotency keys


def get_snapshot(user_id: str) -> ArchetypeSnapshot:
    """
    Get current archetype snapshot for user.
    
    If no snapshot exists, compute initial snapshot from:
    - streak state (builder signal if active)
    - momentum weekly (consistency signal)
    
    Returns:
        ArchetypeSnapshot (always valid)
    """
    if user_id in _snapshots:
        return _snapshots[user_id]
    
    # Deterministic initial state
    return _compute_initial_snapshot(user_id)


def record_signal(
    user_id: str,
    signal: ArchetypeSignal
) -> tuple[ArchetypeSnapshot, list[dict]]:
    """
    Record a behavioral signal and update archetype snapshot.
    
    Idempotency: signals with identical (user_id, date, payload hash) are skipped.
    
    Args:
        user_id: user identifier
        signal: ArchetypeSignal (source, date, payload)
    
    Returns:
        (updated_snapshot, emitted_events)
        
        Events:
        - archetype.updated with idempotency key
    """
    # Check idempotency
    signal_key = _hash_signal(user_id, signal.date, signal.payload)
    if signal_key in _applied_signals:
        # Already applied, return current snapshot
        return (get_snapshot(user_id), [])
    
    # Get current snapshot
    current = get_snapshot(user_id)
    
    # Compute new scores from signal
    if signal.source == "post":
        text = signal.payload.get("text", "")
        platform = signal.payload.get("platform", "generic")
        new_scores = engine.score_from_text(text, platform)
    elif signal.source == "coach":
        coach_scores = signal.payload.get("scores", {})
        suggestions = signal.payload.get("suggestions", [])
        warnings = signal.payload.get("warnings", [])
        new_scores = engine.score_from_coach_feedback(coach_scores, suggestions, warnings)
    elif signal.source == "challenge":
        challenge_type = signal.payload.get("type", "")
        new_scores = engine.score_from_challenge_type(challenge_type)
    else:
        # Unknown source, no-op
        return (current, [])
    
    # Merge with current scores
    merged_scores = engine.merge_scores(current.scores, new_scores, decay=0.92)
    
    # Pick primary + secondary
    primary, secondary = engine.pick_primary_secondary(merged_scores)
    
    # Generate explanation
    supporting_signals = [signal.source]
    explanation = engine.explain(primary, secondary, supporting_signals)
    
    # Build new snapshot
    updated_at = datetime.now(timezone.utc).isoformat()
    new_snapshot = ArchetypeSnapshot(
        user_id=user_id,
        primary=primary,
        secondary=secondary,
        scores=merged_scores,
        explanation=explanation,
        updated_at=updated_at,
        version=current.version + 1,
    )
    
    # Store
    _snapshots[user_id] = new_snapshot
    _applied_signals.add(signal_key)
    
    # Emit event
    event_key = _event_idempotency_key(user_id, signal.date, primary, secondary)
    event = {
        "type": "archetype.updated",
        "idempotencyKey": event_key,
        "userId": user_id,
        "primary": primary.value,
        "secondary": secondary.value if secondary else None,
        "updatedAt": updated_at,
        "version": new_snapshot.version,
    }
    
    return (new_snapshot, [event])


def recompute_today(user_id: str, date: str) -> ArchetypeSnapshot:
    """
    Recompute archetype snapshot for given date (deterministic).
    
    Used for testing or manual refresh.
    Does NOT emit events (idempotent recompute).
    
    Args:
        user_id: user identifier
        date: YYYY-MM-DD UTC date
    
    Returns:
        ArchetypeSnapshot
    """
    # For now, just return current snapshot
    # In production, could replay signals from that date
    return get_snapshot(user_id)


def _compute_initial_snapshot(user_id: str) -> ArchetypeSnapshot:
    """
    Compute initial archetype snapshot for new user (deterministic fallback).
    
    Algorithm:
    - Hash user_id to pick initial scores
    - All archetypes start at base 50.0
    - Apply small deterministic variation (+/- 10 points)
    - Pick primary + secondary
    - Generate supportive explanation
    
    Returns:
        ArchetypeSnapshot
    """
    # Deterministic hash
    hash_int = int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16)
    
    # Base scores with small variation
    scores = {}
    for i, archetype in enumerate(ArchetypeId):
        variation = ((hash_int + i * 17) % 20) - 10  # -10 to +9
        scores[archetype.value] = 50.0 + variation
    
    # Pick primary + secondary
    primary, secondary = engine.pick_primary_secondary(scores)
    
    # Generate explanation
    explanation = engine.explain(primary, secondary, [])
    
    # Build snapshot
    snapshot = ArchetypeSnapshot(
        user_id=user_id,
        primary=primary,
        secondary=secondary,
        scores=scores,
        explanation=explanation,
        updated_at=datetime.now(timezone.utc).isoformat(),
        version=1,
    )
    
    # Store
    _snapshots[user_id] = snapshot
    
    return snapshot


def _hash_signal(user_id: str, date: str, payload: dict) -> str:
    """Generate idempotency key for signal."""
    payload_str = str(sorted(payload.items()))
    combined = f"{user_id}|{date}|{payload_str}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _event_idempotency_key(
    user_id: str,
    date: str,
    primary: ArchetypeId,
    secondary: Optional[ArchetypeId]
) -> str:
    """Generate event idempotency key."""
    sec = secondary.value if secondary else "none"
    combined = f"{user_id}|{date}|{primary.value}|{sec}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
