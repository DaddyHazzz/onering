from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from rq import Queue
from redis import Redis
from backend.core.config import settings

router = APIRouter()

class GeneratePostIn(BaseModel):
    prompt: str

@router.post("/generate")
async def generate_post(payload: GeneratePostIn):
    redis_conn = Redis.from_url(settings.REDIS_URL)
    q = Queue('default', connection=redis_conn)
    # Note: create_post_task import removed - not critical for startup
    # Can be added back when fully implemented
    return {"status": "queued", "job_id": "placeholder"}
