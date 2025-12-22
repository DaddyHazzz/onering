"""Coach service with event emission and archetype-aware suggestions."""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from backend.models.coach import CoachRequest, CoachResponse, CoachPlatform, CoachValuesMode, CoachPostType
from backend.features.coach.scoring_engine import CoachScoringEngine


class CoachService:
    """Service for coach feedback generation."""
    
    @staticmethod
    def generate_feedback(
        request: CoachRequest,
        archetype_primary: Optional[str] = None,
        archetype_secondary: Optional[str] = None
    ) -> tuple[CoachResponse, list[dict]]:
        """
        Generate deterministic coach feedback.
        
        Archetypes influence suggestion tone (softly):
        - builder: more actionable steps
        - philosopher: more reflective framing
        - connector: more questions + community invitation
        - truth_teller: stronger clarity + directness
        - firestarter: energy with guardrails
        - storyteller: narrative hooks + specificity
        
        Args:
            request: CoachRequest with draft + platform
            archetype_primary: optional primary archetype (e.g., "builder")
            archetype_secondary: optional secondary archetype
        
        Returns:
            (CoachResponse, emitted_events)
        """
        
        # Generate event_id (idempotency key) based on user + draft
        # Deterministic: same draft always produces same event_id
        event_id = hashlib.sha256(
            f"{request.user_id}:{request.draft}".encode()
        ).hexdigest()[:16]
        
        # Compute scores
        scores = CoachScoringEngine.score_draft(
            request.draft,
            request.platform,
            request.values_mode,
            request.type,
        )
        
        # Apply archetype influence to suggestions (deterministic tone shift)
        suggestions = scores["suggestions"]
        if archetype_primary:
            suggestions = CoachService._archetype_inflect_suggestions(
                suggestions,
                archetype_primary,
                archetype_secondary
            )
        
        # Build response
        response = CoachResponse(
            event_id=event_id,
            overall_score=scores["overall_score"],
            clarity_score=scores["clarity"],
            resonance_score=scores["resonance"],
            platform_fit_score=scores["platform_fit"],
            authenticity_score=scores["authenticity"],
            momentum_alignment_score=scores["momentum_alignment"],
            tone_label=scores["tone_label"],
            tone_confidence=scores["tone_confidence"],
            warnings=scores["warnings"],
            suggestions=suggestions,
            revised_example=scores["revised_example"],
            generated_at=datetime.now(timezone.utc),
        )
        
        # Emit event
        event = {
            "type": "coach.feedback_generated",
            "userId": request.user_id,
            "draftId": event_id,
            "platform": request.platform,
            "archetype": archetype_primary,
            "scores": {
                "overall": response.overall_score,
                "clarity": response.clarity_score,
                "resonance": response.resonance_score,
                "platform_fit": response.platform_fit_score,
                "authenticity": response.authenticity_score,
                "momentum_alignment": response.momentum_alignment_score,
            },
            "suggestions": response.suggestions,
            "warnings": response.warnings,
            "generatedAt": response.generated_at.isoformat(),
        }
        
        return response, [event]
    
    @staticmethod
    def _archetype_inflect_suggestions(
        suggestions: list[str],
        primary: str,
        secondary: Optional[str]
    ) -> list[str]:
        """
        Apply archetype-specific tone to suggestions (deterministic).
        
        Does NOT change meaning or scores, only phrasing style.
        """
        inflected = []
        
        for suggestion in suggestions:
            # Apply primary archetype inflection
            if primary == "builder":
                # More actionable: "Consider X" => "Try X"
                s = suggestion.replace("Consider ", "Try ")
                s = s.replace("could ", "should ")
                inflected.append(s)
            elif primary == "philosopher":
                # More reflective: "Add X" => "Explore adding X"
                s = suggestion.replace("Add ", "Consider adding ")
                s = s.replace("Try ", "Reflect on ")
                inflected.append(s)
            elif primary == "connector":
                # More inviting: "Clarify X" => "What if you clarified X?"
                if "?" not in suggestion:
                    s = f"What if you {suggestion.lower()}?"
                else:
                    s = suggestion
                inflected.append(s)
            elif primary == "truth_teller":
                # More direct: "might" => "should"
                s = suggestion.replace("might ", "should ")
                s = s.replace("Could you ", "")
                inflected.append(s)
            elif primary == "firestarter":
                # More energetic: "Consider" => "Go bold:"
                if "Add" in suggestion or "Try" in suggestion:
                    s = f"Push further: {suggestion.lower()}"
                else:
                    s = suggestion
                inflected.append(s)
            elif primary == "storyteller":
                # More narrative: "Add details" => "Paint the scene with details"
                s = suggestion.replace("Add details", "Paint the scene with specific details")
                s = s.replace("Be specific", "Show us the moment")
                inflected.append(s)
            else:
                # Unknown archetype: no change
                inflected.append(suggestion)
        
        return inflected
