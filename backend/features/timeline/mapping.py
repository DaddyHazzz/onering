"""Timeline event mapping from audit logs.

Converts audit records into normalized TimelineEvent objects.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from backend.features.timeline.models import TimelineEvent


def map_audit_to_timeline(audit_record: Dict[str, Any]) -> TimelineEvent:
    """Map an audit record to a normalized TimelineEvent.
    
    Args:
        audit_record: Raw audit record with keys: id, ts, user_id, action, draft_id, metadata
    
    Returns:
        TimelineEvent with normalized type and human-readable summary
    """
    action = audit_record.get("action", "unknown")
    user_id = audit_record.get("user_id")
    draft_id = audit_record.get("draft_id", "")
    metadata = audit_record.get("metadata") or {}
    ts = audit_record.get("ts")
    
    # Ensure ts is datetime object
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    
    # Map action to event type and generate summary
    event_type, summary = _map_action_to_type_and_summary(action, user_id, metadata)
    
    # Build event
    event = TimelineEvent(
        event_id=str(audit_record.get("id", "synthetic")),
        ts=ts,
        type=event_type,
        actor_user_id=user_id,
        draft_id=draft_id,
        summary=summary,
        meta=_extract_meta(action, metadata)
    )
    
    return event


def _map_action_to_type_and_summary(
    action: str,
    user_id: Optional[str],
    metadata: Dict[str, Any]
) -> tuple[str, str]:
    """Map audit action to event type and human summary.
    
    Returns:
        (event_type, summary_text)
    """
    actor = f"@{user_id[-6:]}" if user_id else "unknown"
    
    if action == "draft_created":
        title = metadata.get("title", "Untitled")
        return ("draft_created", f"{actor} created draft '{title}'")
    
    elif action == "segment_added":
        content_preview = metadata.get("content", "")[:50]
        return ("segment_added", f"{actor} added segment: {content_preview}...")
    
    elif action == "ring_passed":
        from_user = metadata.get("from_user_id", "unknown")
        to_user = metadata.get("to_user_id", "unknown")
        from_display = f"@{from_user[-6:]}"
        to_display = f"@{to_user[-6:]}"
        return ("ring_passed", f"{from_display} passed ring to {to_display}")
    
    elif action == "collaborator_added":
        collaborator_id = metadata.get("collaborator_user_id", "unknown")
        collab_display = f"@{collaborator_id[-6:]}"
        return ("collaborator_added", f"{actor} added {collab_display} as collaborator")
    
    elif action == "ai_suggest":
        mode = metadata.get("mode", "default")
        platform = metadata.get("platform", "")
        platform_text = f" for {platform}" if platform and platform != "default" else ""
        return ("ai_suggested", f"{actor} requested AI suggestion ({mode}{platform_text})")
    
    elif action == "format_generate":
        platform_count = metadata.get("platform_count", 0)
        return ("format_generated", f"{actor} generated {platform_count} platform formats")
    
    else:
        # Generic fallback
        return ("other", f"{actor} performed {action}")


def _extract_meta(action: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant metadata for timeline event.
    
    Includes action-specific fields for detail views.
    """
    meta = {}
    
    if action == "segment_added":
        if "segment_id" in metadata:
            meta["segment_id"] = metadata["segment_id"]
        if "content_type" in metadata:
            meta["content_type"] = metadata["content_type"]
        if "word_count" in metadata:
            meta["word_count"] = metadata["word_count"]
    
    elif action == "ring_passed":
        if "from_user_id" in metadata:
            meta["from_user_id"] = metadata["from_user_id"]
        if "to_user_id" in metadata:
            meta["to_user_id"] = metadata["to_user_id"]
    
    elif action == "collaborator_added":
        if "collaborator_user_id" in metadata:
            meta["collaborator_user_id"] = metadata["collaborator_user_id"]
    
    elif action == "ai_suggest":
        if "mode" in metadata:
            meta["mode"] = metadata["mode"]
        if "platform" in metadata:
            meta["platform"] = metadata["platform"]
    
    elif action == "format_generate":
        if "platform_count" in metadata:
            meta["platform_count"] = metadata["platform_count"]
        if "platforms" in metadata:
            meta["platforms"] = metadata["platforms"]
    
    return meta
