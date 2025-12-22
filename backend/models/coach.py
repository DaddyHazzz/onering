"""Coach domain models and contracts."""

from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime


# Request/Response types
CoachPlatform = Literal["x", "instagram", "linkedin"]
CoachPostType = Literal["simple", "viral_thread"]
CoachValuesMode = Literal["faith_aligned", "optimistic", "confrontational", "neutral"]
CoachTone = Literal["hopeful", "neutral", "confrontational", "reflective", "playful"]


@dataclass
class CoachRequest:
    """Coach feedback request."""
    
    user_id: str
    platform: CoachPlatform
    draft: str
    type: CoachPostType = "simple"
    values_mode: CoachValuesMode = "neutral"
    archetype: str | None = None  # Pass-through for future personalization
    
    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not self.user_id or not self.user_id.strip():
            errors.append("user_id is required")
        if self.platform not in ["x", "instagram", "linkedin"]:
            errors.append(f"platform must be one of: x, instagram, linkedin (got {self.platform})")
        if not self.draft or len(self.draft.strip()) < 1:
            errors.append("draft is required and must be at least 1 character")
        if len(self.draft) > 4000:
            errors.append(f"draft exceeds 4000 character limit (got {len(self.draft)})")
        if self.type not in ["simple", "viral_thread"]:
            errors.append(f"type must be one of: simple, viral_thread (got {self.type})")
        if self.values_mode not in ["faith_aligned", "optimistic", "confrontational", "neutral"]:
            errors.append(f"values_mode must be one of: faith_aligned, optimistic, confrontational, neutral (got {self.values_mode})")
        return errors


@dataclass
class CoachResponse:
    """Coach feedback response."""
    
    # Identifiers
    event_id: str  # Idempotency key; typically hash(user_id + draft)
    
    # Overall score (0-100)
    overall_score: int
    
    # Dimension scores (each 0-100)
    clarity_score: int
    resonance_score: int  # Emotional resonance
    platform_fit_score: int
    authenticity_score: int
    momentum_alignment_score: int
    
    # Tone detection
    tone_label: CoachTone
    tone_confidence: float  # 0.0 - 1.0
    
    # Warnings (values violations, disallowed language, etc.)
    warnings: list[str] = field(default_factory=list)
    
    # Suggestions (max 5, concrete and actionable)
    suggestions: list[str] = field(default_factory=list)
    
    # Optional: template-based revised example (deterministic)
    revised_example: str | None = None  # Max 600 chars
    
    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz=None))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "overall_score": self.overall_score,
            "dimensions": {
                "clarity": self.clarity_score,
                "resonance": self.resonance_score,
                "platform_fit": self.platform_fit_score,
                "authenticity": self.authenticity_score,
                "momentum_alignment": self.momentum_alignment_score,
            },
            "tone": {
                "label": self.tone_label,
                "confidence": self.tone_confidence,
            },
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "revised_example": self.revised_example,
            "generated_at": self.generated_at.isoformat(),
        }
