"""
Momentum API Endpoints

GET /v1/momentum/today — today's momentum score
GET /v1/momentum/weekly — last 7 days of momentum
"""

from fastapi import APIRouter, HTTPException, Query
from backend.models.momentum import MomentumSnapshot
from backend.features.momentum.service import MomentumService

router = APIRouter(prefix="/v1/momentum", tags=["momentum"])


@router.get("/today")
async def get_momentum_today(user_id: str = Query(..., description="User ID")) -> dict:
    """
    Get today's momentum score.

    Query params:
        user_id: User ID (Clerk user ID)

    Returns:
        {
            "data": {
                "userId": "user_...",
                "date": "2025-12-21",
                "score": 75.5,
                "trend": "up",
                "components": {
                    "streakComponent": 20.0,
                    "challengeComponent": 15.0,
                    "consistencyComponent": 10.0,
                    "coachComponent": 5.0
                },
                "nextActionHint": "You're in flow. Keep riding this wave today.",
                "computedAt": "2025-12-21T14:30:00+00:00"
            }
        }
    """
    try:
        if not user_id:
            raise ValueError("user_id is required")

        snapshot = MomentumService.compute_today_momentum(user_id)
        return {"data": snapshot.to_dict()}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing momentum: {str(e)}")


@router.get("/weekly")
async def get_momentum_weekly(user_id: str = Query(..., description="User ID")) -> dict:
    """
    Get last 7 days of momentum scores (most recent first).

    Query params:
        user_id: User ID (Clerk user ID)

    Returns:
        {
            "data": [
                { momentum snapshot for today },
                { momentum snapshot for yesterday },
                ...
                { momentum snapshot for 6 days ago }
            ]
        }
    """
    try:
        if not user_id:
            raise ValueError("user_id is required")

        snapshots = MomentumService.compute_weekly_momentum(user_id)
        return {"data": [s.to_dict() for s in snapshots]}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing weekly momentum: {str(e)}")
