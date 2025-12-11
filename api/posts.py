from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from rq import Queue
from redis import Redis
from core.config import settings
from services.posting_service import create_post_task

router = APIRouter()

class GeneratePostIn(BaseModel):
    prompt: str

@router.post("/generate")
async def generate_post(payload: GeneratePostIn):
    redis_conn = Redis.from_url(settings.REDIS_URL)
    q = Queue('default', connection=redis_conn)
    job = q.enqueue(create_post_task, payload.prompt)
    return {"status": "queued", "job_id": job.id}
