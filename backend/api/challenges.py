from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.features.challenges.service import challenge_service
from backend.features.streaks.service import streak_service
from backend.features.archetypes import service as archetype_service

router = APIRouter()


class AcceptRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    challenge_id: str = Field(..., min_length=1)


class CompleteRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    challenge_id: str = Field(..., min_length=1)
    completion_source: Optional[str] = None  # post_id if tied to a post


@router.get("/v1/challenges/today")
def get_today_challenge(user_id: str = Query(..., min_length=1)):
    """
    Get today's challenge for a user (idempotent assignment).
    
    Automatically fetches user's archetype to softly weight challenge selection.
    """
    try:
        # Get user's archetype (soft influence on challenge type)
        try:
            archetype_snapshot = archetype_service.get_snapshot(user_id)
            archetype_primary = archetype_snapshot.primary.value
        except:
            archetype_primary = None
        
        result = challenge_service.get_today_challenge(
            user_id=user_id,
            archetype=archetype_primary
        )
        return {
            "challenge_id": result.challenge_id,
            "date": result.date,
            "type": result.type,
            "prompt": result.prompt,
            "status": result.status,
            "next_action_hint": result.next_action_hint,
            "streak_effect": result.streak_effect,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/challenges/today/accept")
def accept_challenge(req: AcceptRequest):
    """Accept today's challenge."""
    try:
        result, emitted = challenge_service.accept_challenge(
            user_id=req.user_id,
            challenge_id=req.challenge_id,
            accepted_at=datetime.now(timezone.utc),
        )
        return {
            "challenge_id": result.challenge_id,
            "status": result.status,
            "next_action_hint": result.next_action_hint,
            "emitted": emitted,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/challenges/today/complete")
def complete_challenge(req: CompleteRequest):
    """Complete today's challenge and conditionally increment streak."""
    try:
        result, challenge_events = challenge_service.complete_challenge(
            user_id=req.user_id,
            challenge_id=req.challenge_id,
            completed_at=datetime.now(timezone.utc),
            completion_source=req.completion_source,
        )

        # Streak integration: only increment if not already incremented today
        streak_events: list = []
        current_day = datetime.now(timezone.utc).date()
        streak_state = streak_service.get_state(req.user_id)

        # Check if streak already advanced today
        last_active = streak_state.get("last_active_date")
        already_incremented_today = last_active and last_active == current_day.isoformat()

        if not already_incremented_today and result.status == "completed":
            # Challenge completion can advance streak
            _, streak_events = streak_service.record_posted(
                user_id=req.user_id,
                post_id=req.challenge_id,  # Use challenge_id as unique event key
                posted_at=datetime.now(timezone.utc),
                platform="challenge",
            )

        return {
            "challenge_id": result.challenge_id,
            "status": result.status,
            "next_action_hint": result.next_action_hint,
            "streak_effect": "incremented" if streak_events else "none",
            "emitted": challenge_events + streak_events,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
