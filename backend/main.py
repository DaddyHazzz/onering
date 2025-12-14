import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load env from backend/.env
backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(backend_dir, '.env'))

# Add backend to path for imports
sys.path.insert(0, backend_dir)
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

# Import after dotenv is loaded
try:
    from backend.core.config import settings
    from backend.core.logging import configure_logging
    from backend.api import auth, posts
    from backend.agents.viral_thread import generate_viral_thread
    import groq
    from redis import Redis
    from rq import Queue
except ImportError as e:
    print(f"[FATAL] Import error: {e}")
    print(f"[FATAL] backend_dir: {backend_dir}")
    print(f"[FATAL] parent_dir: {parent_dir}")
    print(f"[FATAL] sys.path: {sys.path}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

configure_logging()

app = FastAPI(title="OneRing - Backend (dev)")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger = logging.getLogger("onering")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {"error": str(exc)}

# CORS (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

@app.get("/healthz")
def health():
    return {"status": "ok", "env": settings.ENV}


@app.get("/v1/health")
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    import time
    uptime = int(time.time() - app.state.startup_time) if hasattr(app.state, 'startup_time') else 0
    return {
        "status": "healthy",
        "uptime": uptime,
        "routes": len(app.routes)
    }


@app.get("/v1/test")
def test_endpoint():
    """Simple test endpoint to verify backend is accessible."""
    logger = logging.getLogger("onering")
    logger.info("[/v1/test] endpoint called")
    return {"message": "Backend is running", "version": "0.1.0"}


# Define request schema for generation endpoint
class GenerateRequest(BaseModel):
    prompt: str
    mode: str = "simple"  # "simple" or "viral_thread"
    user_id: Optional[str] = None  # Optional: for personalized context with pgvector


async def stream_groq_response(prompt: str):
    """Stream tokens from Groq API as server-sent events."""
    groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
    logger = logging.getLogger("onering")

    logger.info(f"[/v1/generate/content] streaming from Groq for prompt: {prompt[:50]}...")

    try:
        stream = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an elite viral content creator for X/Twitter. Write in first person, raw, emotional, zero fluff. Use short sentences. Add controversy when possible. End with a strong CTA. Always return exactly one long tweet or a numbered thread.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="llama-3.1-8b-instant",
            temperature=0.9,
            max_tokens=1024,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                yield f"data: {token}\n\n"

        logger.info("[/v1/generate/content] streaming completed")
    except Exception as e:
        logger.error(f"[/v1/generate/content] Groq streaming error: {e}", exc_info=True)
        yield f"data: ERROR: {str(e)}\n\n"


async def stream_viral_thread_response(prompt: str, user_id: str = None):
    """Stream a viral thread from LangGraph agent chain with pgvector context."""
    logger = logging.getLogger("onering")
    logger.info(f"[/v1/generate/content] generating viral thread for: {prompt[:50]}...")

    try:
        # Call sync function - it should not block since LangGraph is fast
        thread_lines = generate_viral_thread(prompt, user_id=user_id)
        
        if not thread_lines:
            logger.warning(f"[/v1/generate/content] no tweets generated for prompt")
            yield "data: ERROR: Failed to generate thread\n\n"
            return
            
        logger.info(f"[/v1/generate/content] generated thread with {len(thread_lines)} tweets")

        # Stream each tweet separately (no numbering, they're already clean from optimizer)
        import re
        for tweet in thread_lines:
            # Final cleanup: remove any remaining numbering the LLM might have added
            tweet_clean = tweet.strip()
            # Remove patterns like "1/6 ", "1. ", "[1] ", etc.
            tweet_clean = re.sub(r'^\d+(/\d+)?[.):\-\]]*\s*', '', tweet_clean).strip()
            # Remove leading bullets
            tweet_clean = re.sub(r'^[-•*]+\s*', '', tweet_clean).strip()
            
            if tweet_clean:
                yield f"data: {tweet_clean}\n\n"

        logger.info("[/v1/generate/content] viral thread streaming completed")
    except Exception as e:
        logger.error(f"[/v1/generate/content] viral thread error: {e}", exc_info=True)
        yield f"data: ERROR: {str(e)}\n\n"


@app.post("/v1/generate/content", response_class=StreamingResponse)
async def generate_content(body: GenerateRequest):
    """
    Stream generated content from Groq model or LangGraph viral thread chain.
    Supports mode: "simple" or "viral_thread"
    Optional user_id enables personalized context via pgvector similarity search.
    """
    logger = logging.getLogger("onering")
    logger.info(f"[/v1/generate/content] POST received, mode: {body.mode}, prompt length: {len(body.prompt)}")

    if not body.prompt or not body.prompt.strip():
        logger.error("[/v1/generate/content] empty prompt provided")
        async def error_gen():
            yield "data: ERROR: Prompt cannot be empty\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    if body.mode == "viral_thread":
        response_generator = stream_viral_thread_response(body.prompt, user_id=body.user_id)
    else:
        response_generator = stream_groq_response(body.prompt)

    return StreamingResponse(
        response_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.on_event("startup")
async def on_startup():
    logger = logging.getLogger("onering")
    logger.info("Starting OneRing backend...")
    # Track startup time for health check uptime calculation
    import time
    app.state.startup_time = time.time()


# Redis & RQ setup for job queuing
class SchedulePostRequest(BaseModel):
    content: str
    user_id: str
    delay_seconds: int
    post_id: str = None


def get_redis_conn():
    """Get Redis connection."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url)


@app.post("/v1/jobs/schedule-post")
async def schedule_twitter_post(body: SchedulePostRequest):
    """
    Enqueue a scheduled post job to RQ.
    Called from Next.js schedule-post route.
    """
    logger = logging.getLogger("onering")
    logger.info(f"[/v1/jobs/schedule-post] received request for user: {body.user_id}, delay: {body.delay_seconds}s")

    try:
        redis_conn = get_redis_conn()
        queue = Queue(connection=redis_conn)

        # Enqueue the job to run after delay_seconds
        job = queue.enqueue_in(
            timedelta(seconds=body.delay_seconds),
            schedule_post,
            body.content,
            body.user_id,
            body.delay_seconds,
            body.post_id,
            job_timeout="10m",
            result_ttl=3600,
        )

        logger.info(f"[/v1/jobs/schedule-post] enqueued job: {job.id}")

        return {
            "success": True,
            "job_id": job.id,
            "scheduled_for": (datetime.now() + timedelta(seconds=body.delay_seconds)).isoformat(),
            "message": f"Post scheduled for {body.delay_seconds} seconds from now",
        }
    except Exception as e:
        logger.error(f"[/v1/jobs/schedule-post] error: {e}")
        return {
            "success": False,
            "error": str(e),
        }, 500


@app.on_event("shutdown")
async def on_shutdown():
    logging.getLogger("onering").info("Stopping OneRing backend...")
