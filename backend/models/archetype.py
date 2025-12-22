"""
Archetype Models

Identity labels that evolve over time based on creator behavior:
- truth_teller: Direct, clear, cuts through noise
- builder: Actionable, ships consistently
- philosopher: Reflective, explores ideas deeply
- connector: Community-oriented, asks questions
- firestarter: High energy, provocative (with guardrails)
- storyteller: Narrative-driven, specific details
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ArchetypeId(str, Enum):
    """Six core creator archetypes."""
    TRUTH_TELLER = "truth_teller"
    BUILDER = "builder"
    PHILOSOPHER = "philosopher"
    CONNECTOR = "connector"
    FIRESTARTER = "firestarter"
    STORYTELLER = "storyteller"


class ArchetypeSignal(BaseModel):
    """
    A single behavioral signal that influences archetype scoring.
    
    Sources:
    - "coach": feedback from AI coach (suggestions, warnings)
    - "challenge": challenge completion or attempt
    - "post": published content analysis
    """
    model_config = ConfigDict(frozen=True)
    
    source: str = Field(..., pattern="^(coach|challenge|post)$")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD UTC
    payload: dict = Field(default_factory=dict, max_length=1000)  # Limited size


class ArchetypeSnapshot(BaseModel):
    """
    Current archetype state for a user.
    
    Stability guarantee: primary archetype should not flip wildly day-to-day.
    Explanation: always supportive, never shameful.
    """
    model_config = ConfigDict(frozen=True)
    
    user_id: str = Field(..., min_length=1)
    primary: ArchetypeId
    secondary: Optional[ArchetypeId] = None
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Scores for each archetype (0..100)"
    )
    explanation: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly 3 supportive bullet points"
    )
    updated_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp"
    )
    version: int = Field(default=1, ge=1)
    
    def to_public_dict(self) -> dict:
        """Safe subset for public profiles."""
        return {
            "userId": self.user_id,
            "primary": self.primary.value,
            "secondary": self.secondary.value if self.secondary else None,
            "explanation": self.explanation,
            "updatedAt": self.updated_at,
        }
