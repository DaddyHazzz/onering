"""Coach API endpoints with archetype integration."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from backend.models.coach import CoachRequest, CoachPlatform, CoachValuesMode, CoachPostType
from backend.features.coach.service import CoachService
from backend.features.archetypes import service as archetype_service


router = APIRouter(prefix="", tags=["coach"])


class CoachRequestSchema(BaseModel):
    """Pydantic schema for coach request."""
    
    user_id: str = Field(..., min_length=1)
    platform: CoachPlatform = Field(...)
    draft: str = Field(..., min_length=1, max_length=4000)
    type: CoachPostType = "simple"
    values_mode: CoachValuesMode = "neutral"


@router.post("/v1/coach/feedback")
async def get_coach_feedback(schema: CoachRequestSchema):
    """
    Get deterministic coach feedback on a draft.
    
    Automatically fetches user's archetype to influence suggestion tone.
    No authentication required (can be added later via middleware).
    """
    
    try:
        # Build request
        request = CoachRequest(
            user_id=schema.user_id,
            platform=schema.platform,
            draft=schema.draft,
            type=schema.type,
            values_mode=schema.values_mode,
        )
        
        # Validate
        errors = request.validate()
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        
        # Get user's archetype (soft influence on suggestions)
        try:
            archetype_snapshot = archetype_service.get_snapshot(schema.user_id)
            archetype_primary = archetype_snapshot.primary.value
            archetype_secondary = archetype_snapshot.secondary.value if archetype_snapshot.secondary else None
        except:
            # If archetype fetch fails, proceed without
            archetype_primary = None
            archetype_secondary = None
        
        # Generate feedback
        response, events = CoachService.generate_feedback(
            request,
            archetype_primary=archetype_primary,
            archetype_secondary=archetype_secondary
        )
        
        # Return response
        return {
            "data": response.to_dict(),
            "emitted": events,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
