"""Ring-aware AI suggestion service (Phase 8.1).

Deterministic, additive-only suggestions that never mutate drafts.
Supports next-segment ideas, rewrites, summaries, and read-only commentary.
"""

from typing import Literal, Optional
from datetime import datetime, timezone

from backend.core.errors import NotFoundError, RingRequiredError, ValidationError
from backend.core.tracing import start_span
from backend.features.ai.prompts import BASE_PROMPT, PLATFORM_PROMPTS
from backend.features.collaboration.service import get_draft, display_for_user
from backend.models.collab import CollabDraft

AllowedMode = Literal["next", "rewrite", "summary", "commentary"]
AllowedPlatform = Literal["x", "youtube", "instagram", "blog"]


def _platform_key(platform: Optional[str]) -> str:
    key = (platform or "").lower()
    return key if key in PLATFORM_PROMPTS else "default"


def _platform_voice(platform: Optional[str]) -> str:
    tpl = PLATFORM_PROMPTS.get(_platform_key(platform), PLATFORM_PROMPTS["default"])
    return f"Tone: {tpl['tone']}. Format: {tpl['structure']}"


def _clamp(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _format_for_platform(text: str, platform: Optional[str]) -> str:
    key = _platform_key(platform)
    if key == "x":
        return _clamp(text, 240)
    if key == "instagram":
        return _clamp(text, 2200) + "\n\nCTA: Save this and share your take."
    if key == "youtube":
        return _clamp(text, 800) + "\n\nBeat map: intro → payoff → CTA."
    if key == "blog":
        return _clamp(text, 1200)
    return text


def _recent_segments(draft: CollabDraft, count: int = 3):
    return draft.segments[-count:]


def _context_block(draft: CollabDraft) -> str:
    holder_display = display_for_user(draft.ring_state.current_holder_id)
    title = draft.title or "Untitled"
    platform = draft.platform or "unknown"
    parts = [
        f"Title: {title}",
        f"Platform: {platform}",
        f"Current ring holder: {holder_display}",
    ]
    recent = _recent_segments(draft, 2)
    if recent:
        snippets = [f"{seg.segment_order + 1}: {_clamp(seg.content.strip(), 160)}" for seg in recent]
        parts.append("Recent segments → " + " | ".join(snippets))
    return " \n".join(parts)


def _suggest_next(draft: CollabDraft, platform: Optional[str]) -> str:
    context = _context_block(draft)
    last = draft.segments[-1].content.strip() if draft.segments else ""
    prompt = (
        "Next segment: keep momentum, add one concrete detail, and end with a mini-CTA. "
        f"Context → {context}. Last line to build on: {_clamp(last, 160) if last else 'n/a'}."
    )
    return _format_for_platform(f"{BASE_PROMPT}\n{_platform_voice(platform)}\n{prompt}", platform)


def _rewrite_last(draft: CollabDraft, platform: Optional[str]) -> str:
    if not draft.segments:
        raise ValidationError("Cannot rewrite: draft has no segments")
    last = draft.segments[-1]
    prompt = (
        f"Rewrite the last segment with tighter phrasing and a stronger hook. "
        f"Keep the original intent. Original: {_clamp(last.content.strip(), 200)}"
    )
    return _format_for_platform(f"{BASE_PROMPT}\n{_platform_voice(platform)}\n{prompt}", platform)


def _summarize(draft: CollabDraft, platform: Optional[str]) -> str:
    if not draft.segments:
        return _format_for_platform(
            f"{BASE_PROMPT}\nNo segments yet. Proposed opener: a one-line hook for '{draft.title}'.",
            platform,
        )
    selected = _recent_segments(draft, 3)
    joined = "; ".join(_clamp(seg.content.strip(), 120) for seg in selected)
    prompt = f"Summary so far: {joined}. Provide a crisp recap and a suggested next beat."
    return _format_for_platform(f"{BASE_PROMPT}\n{_platform_voice(platform)}\n{prompt}", platform)


def _commentary(draft: CollabDraft, platform: Optional[str]) -> str:
    context = _context_block(draft)
    prompt = (
        "You do NOT hold the ring. Offer a concise idea for when you receive it. "
        "One actionable suggestion only. "
        f"Context → {context}"
    )
    return _format_for_platform(f"{BASE_PROMPT}\n{_platform_voice(platform)}\n{prompt}", platform)


def suggest_ai_response(
    *, user_id: str, draft_id: str, mode: AllowedMode, platform: Optional[str] = None
) -> dict:
    """Generate a deterministic AI suggestion for a draft.

    Raises:
        NotFoundError: Draft missing
        RingRequiredError: Mutative modes requested without ring
        ValidationError: Bad input
    """
    with start_span("ai.suggest", {"draft_id": draft_id, "mode": mode, "user_id": user_id}):
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")

        ring_holder = draft.ring_state.current_holder_id == user_id
        if mode != "commentary" and not ring_holder:
            raise RingRequiredError("You must hold the ring to request this suggestion")

        if mode == "next":
            content = _suggest_next(draft, platform)
        elif mode == "rewrite":
            content = _rewrite_last(draft, platform)
        elif mode == "summary":
            content = _summarize(draft, platform)
        elif mode == "commentary":
            content = _commentary(draft, platform)
        else:
            raise ValidationError("Unsupported suggestion mode")

        return {
            "mode": mode,
            "content": content,
            "ring_holder": ring_holder,
            "platform": platform or "default",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
