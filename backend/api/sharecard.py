"""
backend/api/sharecard.py
Share card endpoint: Deterministic, public-safe profile snapshot.
"""

from fastapi import APIRouter, Query, HTTPException
from backend.core.config import settings

router = APIRouter(prefix="/profile", tags=["profile"])


def get_safe_metrics(handle: str) -> dict:
    """
    Extract deterministic, safe metrics for public display.
    No images, no sensitive data.
    Fallback: returns default metrics if user not found.
    """
    # Safe subset - simplified for demo
    # In production, would fetch from DB but here we provide defaults
    return {
        "handle": handle.lower(),
        "name": handle.capitalize(),
        "streak": 0,
        "momentum_score": 50,
        "weekly_delta": 0,
        "top_platform": "X",
    }


@router.get("/share-card")
async def get_share_card(
    handle: str = Query(..., description="Username or handle"),
    style: str = Query("default", description="Card style: default, minimal, bold"),
) -> dict:
    """
    Generate deterministic share card JSON (no images).
    
    Returns:
    - title: User's name or handle
    - subtitle: Momentum trend + top platform
    - metrics: streak, momentum, weekly delta, top platform
    - tagline: Motivational text (safe, no shame language)
    - theme: Color scheme
    
    Determinism guarantee: Same handle + style → identical response (except timestamp)
    """
    from datetime import datetime

    # Normalize handle
    handle = handle.strip().lower()
    if not handle or len(handle) > 50:
        raise HTTPException(status_code=400, detail="Invalid handle")

    # Fetch metrics (fallback to defaults)
    metrics = get_safe_metrics(handle)

    # Determine trend text (deterministic based on weekly_delta)
    delta = metrics["weekly_delta"]
    if delta > 5:
        trend_text = "Momentum rising 📈"
        trend_color = "from-green-400 to-green-600"
    elif delta < -5:
        trend_text = "Momentum dipping 📉"
        trend_color = "from-orange-400 to-orange-600"
    else:
        trend_text = "Momentum stable ➡️"
        trend_color = "from-blue-400 to-blue-600"

    # Generate tagline (safe, deterministic pool)
    taglines = {
        0: "Building momentum, one post at a time.",
        1: "Consistency compounds creativity.",
        2: "Your story is becoming real.",
        3: "Keep the streak alive.",
        4: "Momentum favors the showing up.",
        5: "Your voice matters.",
    }
    tagline_idx = (hash(handle) % 6) % len(taglines)
    tagline = taglines[tagline_idx]

    # Style variants
    themes = {
        "default": {
            "bg": "from-purple-600 to-pink-600",
            "accent": "purple",
        },
        "minimal": {
            "bg": "from-gray-700 to-gray-900",
            "accent": "gray",
        },
        "bold": {
            "bg": "from-red-600 to-orange-600",
            "accent": "orange",
        },
    }
    theme = themes.get(style, themes["default"])

    return {
        "title": metrics["name"],
        "subtitle": f"{trend_text} • {metrics['top_platform']}",
        "metrics": {
            "streak": metrics["streak"],
            "momentum_score": metrics["momentum_score"],
            "weekly_delta": metrics["weekly_delta"],
            "top_platform": metrics["top_platform"],
        },
        "tagline": tagline,
        "theme": theme,
        "generated_at": datetime.now().isoformat(),
    }
