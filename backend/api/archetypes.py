"""
Archetype API Routes

Endpoints:
1. GET /v1/archetypes/me?user_id=... - Get user's archetype snapshot
2. POST /v1/archetypes/signal - Record behavioral signal
3. GET /v1/archetypes/public?user_id=... - Public subset only
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from backend.models.archetype import ArchetypeSignal, ArchetypeSnapshot
from backend.features.archetypes import service


router = APIRouter(prefix="/v1/archetypes")


# Request/Response models
class RecordSignalRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    source: str = Field(..., pattern="^(coach|challenge|post)$")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    payload: dict = Field(default_factory=dict)


class RecordSignalResponse(BaseModel):
    success: bool
    snapshot: dict
    events: list[dict] = Field(default_factory=list)


# Endpoints

@router.get("/me")
async def get_my_archetype(
    user_id: str = Query(..., description="User ID (from Clerk)")
) -> dict:
    """
    Get user's current archetype snapshot.
    
    Returns full snapshot including scores.
    Requires authentication (user_id validated by caller).
    
    Response:
        { success: true, data: ArchetypeSnapshot }
    """
    try:
        snapshot = service.get_snapshot(user_id)
        return {
            "success": True,
            "data": snapshot.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving archetype: {str(e)}")


@router.post("/signal")
async def record_signal(request: RecordSignalRequest) -> RecordSignalResponse:
    """
    Record a behavioral signal and update archetype.
    
    Idempotency: identical signals (user_id + date + payload) are skipped.
    
    Body:
        { user_id, source, date, payload }
    
    Response:
        { success: true, snapshot: {...}, events: [...] }
    """
    try:
        signal = ArchetypeSignal(
            source=request.source,
            date=request.date,
            payload=request.payload,
        )
        
        snapshot, events = service.record_signal(request.user_id, signal)
        
        return RecordSignalResponse(
            success=True,
            snapshot=snapshot.model_dump(),
            events=events,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording signal: {str(e)}")


@router.get("/public")
async def get_public_archetype(
    user_id: str = Query(..., description="User ID")
) -> dict:
    """
    Get public subset of archetype data (safe for sharing).
    
    No authentication required.
    Excludes: scores, version, internal details.
    
    Response:
        { success: true, data: { userId, primary, secondary, explanation, updatedAt } }
    """
    try:
        snapshot = service.get_snapshot(user_id)
        return {
            "success": True,
            "data": snapshot.to_public_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving public archetype: {str(e)}")
