"""
backend/models/sharecard_collab.py
Share card response model for collaborative drafts.
Used by /v1/collab/drafts/{draft_id}/share-card endpoint.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ShareCardMetrics(BaseModel):
    """Ring velocity metrics for share card"""
    model_config = ConfigDict(frozen=True)

    contributors_count: int = Field(..., description="Unique contributors + creator")
    ring_passes_last_24h: int = Field(..., description="Ring passes in last 24 hours")
    avg_minutes_between_passes: Optional[int] = Field(None, description="Avg minutes between passes, None if <2 passes")
    segments_count: int = Field(..., description="Total number of segments in draft")


class ShareCardCTA(BaseModel):
    """Call-to-action for share card"""
    model_config = ConfigDict(frozen=True)

    label: str = Field(..., description="CTA button text")
    url: str = Field(..., description="Target URL (always /dashboard/collab?draftId=...)")


class ShareCardTheme(BaseModel):
    """Visual theme for share card rendering"""
    model_config = ConfigDict(frozen=True)

    bg: str = Field(default="from-slate-900 to-indigo-700", description="Tailwind gradient background")
    accent: str = Field(default="indigo", description="Accent color (indigo, emerald, rose, amber)")


class CollabShareCard(BaseModel):
    """
    Share card response for collaborative drafts.
    Deterministic: same inputs + same now => identical response.
    Safe: never includes token_hash, invite tokens, emails, raw secrets.
    """
    model_config = ConfigDict(frozen=True)

    draft_id: str = Field(..., description="Draft ID")
    title: str = Field(..., description="Formatted title: 'Collab Thread: [draft_title]'")
    subtitle: str = Field(..., description="Supportive subtitle with ring holder + metrics")
    
    # Metrics
    metrics: ShareCardMetrics = Field(..., description="Ring velocity metrics")
    
    # Contributors
    contributors: List[str] = Field(..., description="@u_XXXXXX display names (max 5, deterministic order)")
    
    # Copy/description
    top_line: str = Field(..., description="Supportive summary line, no shame words")
    
    # Call-to-action
    cta: ShareCardCTA = Field(..., description="Button label + URL")
    
    # Theme
    theme: ShareCardTheme = Field(default_factory=ShareCardTheme, description="Visual theme")
    
    # Generated timestamp
    generated_at: str = Field(..., description="ISO timestamp when card was generated")


class ShareCardRequest(BaseModel):
    """Query parameters for share card endpoint"""
    viewer_id: Optional[str] = Field(None, description="User viewing the card (for future personalization)")
    style: str = Field(default="default", description="Card style (currently only 'default')")
    now: Optional[str] = Field(None, description="ISO timestamp for deterministic metric computation (testing only)")
