import logging
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load env from backend/.env
backend_dir = os.path.dirname(os.path.abspath(__file__))
if "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))

# Add backend to path for imports
sys.path.insert(0, backend_dir)
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

# Import after dotenv is loaded
try:
    from backend.core.config import settings, validate_config
    from backend.core.logging import configure_logging
    from backend.core.middleware.request_id import RequestIdMiddleware
    from backend.core.middleware.metrics import MetricsMiddleware
    from backend.core.middleware.tracing import TracingMiddleware
    from backend.core.validation import validate_env
    from backend.core.errors import (
        AppError,
        app_error_handler,
        http_error_handler,
        unhandled_exception_handler,
    )
    from backend.core.middleware.ratelimit import RateLimitMiddleware
    from backend.core.ratelimit import build_rate_limit_config_from_env
    from backend.core.tracing import setup_tracing
    from backend.api import auth, posts, analytics, streaks, challenges, coach, momentum, profile, archetypes, sharecard, collaboration, collaboration_invites, health, billing, admin_billing, realtime, metrics, ai, format as format_api, timeline, export as export_api, waitmode, insights, enforcement, monitoring_enforcement, monitoring_tokens, monitoring_external, tokens, external, external_admin
    from backend.agents.viral_thread import generate_viral_thread
    from backend.features.enforcement.service import EnforcementRequest, run_enforcement_pipeline, get_enforcement_mode
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

configure_logging(settings.ENV)
validate_env()
validate_config(strict=getattr(settings, "CONFIG_STRICT", False))
setup_tracing(enabled=settings.OTEL_ENABLED)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("onering")
    logger.info("Starting OneRing backend...")
    import time
    app.state.startup_time = time.time()
    try:
        yield
    finally:
        logging.getLogger("onering").info("Stopping OneRing backend...")


app = FastAPI(title="OneRing - Backend (dev)", lifespan=lifespan)

# Middlewares
app.add_middleware(RequestIdMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(RateLimitMiddleware, config=build_rate_limit_config_from_env(os.environ))
app.add_middleware(MetricsMiddleware)


def strip_numbering_line(text: str) -> str:
    """Remove any leading numbering or bullets from a single line."""
    return re.sub(r"^\s*(?:\d+(?:/\d+)?[.):\-\]]*\s*|(?:Tweet\s+)?\d+\s*[-:).]?\s*|[-•*]+\s*)", "", text).lstrip()

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

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
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
# Legacy alias to support direct /v1/analytics/* paths used in tests/clients
app.include_router(analytics.router, tags=["analytics-legacy"])
app.include_router(insights.router, tags=["insights"])
app.include_router(streaks.router, tags=["streaks"])
app.include_router(challenges.router, tags=["challenges"])
app.include_router(coach.router, tags=["coach"])
app.include_router(momentum.router, tags=["momentum"])
app.include_router(profile.router, tags=["profile"])
app.include_router(sharecard.router, prefix="/v1", tags=["sharecard"])
app.include_router(collaboration.router, tags=["collaboration"])
app.include_router(collaboration_invites.router, tags=["collaboration-invites"])
app.include_router(realtime.router, tags=["realtime"])
app.include_router(archetypes.router, tags=["archetypes"])
app.include_router(health.router, tags=["health"])
app.include_router(health.root_router, tags=["health"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(billing.router, prefix="/api", tags=["billing"])
app.include_router(admin_billing.router, tags=["admin-billing"])
app.include_router(ai.router, tags=["ai"])
app.include_router(enforcement.router, tags=["enforcement"])
app.include_router(monitoring_enforcement.router, tags=["monitoring"])
app.include_router(monitoring_tokens.router, tags=["monitoring"])
app.include_router(monitoring_external.router, tags=["monitoring"])
app.include_router(format_api.router, tags=["format"])
app.include_router(timeline.router, tags=["timeline"])
app.include_router(export_api.router, tags=["export"])
app.include_router(waitmode.router, tags=["waitmode"])
app.include_router(tokens.router, tags=["tokens"])
app.include_router(external.router, tags=["external"])
app.include_router(external_admin.router, tags=["admin-external"])

@app.get("/v1/test")
def test_endpoint():
    """Simple test endpoint to verify backend is accessible."""
    logger = logging.getLogger("onering")
    logger.info("[/v1/test] endpoint called")
    return {"message": "Backend is running", "version": "0.1.0"}


# Define request schema for generation endpoint
class GenerateRequest(BaseModel):
    prompt: str
    type: str  # "simple" or "viral_thread"
    platform: str
    user_id: str
    stream: bool = True


async def stream_groq_response(prompt: str, collector: list | None = None):
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

        buffer = ""

        for chunk in stream:
            if not chunk.choices[0].delta.content:
                continue
            token = chunk.choices[0].delta.content
            buffer += token

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                cleaned = strip_numbering_line(line)
                if collector is not None and cleaned:
                    collector.append(cleaned)
                if cleaned:
                    yield f"data: {cleaned}\n\n"

        if buffer.strip():
            cleaned = strip_numbering_line(buffer)
            if collector is not None and cleaned:
                collector.append(cleaned)
            yield f"data: {cleaned}\n\n"

        logger.info("[/v1/generate/content] streaming completed")
    except Exception as e:
        logger.error(f"[/v1/generate/content] Groq streaming error: {e}", exc_info=True)
        yield f"data: ERROR: {str(e)}\n\n"


async def stream_viral_thread_response(prompt: str, user_id: str = None, collector: list | None = None):
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
        for tweet in thread_lines:
            tweet_clean = strip_numbering_line(tweet.strip()).strip()

            if tweet_clean:
                if collector is not None:
                    collector.append(tweet_clean)
                yield f"data: {tweet_clean}\n\n"

        logger.info("[/v1/generate/content] viral thread streaming completed")
    except Exception as e:
        logger.error(f"[/v1/generate/content] viral thread error: {e}", exc_info=True)
        yield f"data: ERROR: {str(e)}\n\n"


def _format_enforcement_event(payload: dict) -> str:
    return f"event: enforcement\ndata: {json.dumps(payload, default=str)}\n\n"


@app.post("/v1/generate/content")
async def generate_content(body: GenerateRequest, request: Request):
    """Generate or stream content with deterministic validation shared for streaming/non-streaming."""
    logger = logging.getLogger("onering")
    logger.info(
        f"[/v1/generate/content] POST received, type={body.type}, platform={body.platform}, stream={body.stream}"
    )

    if not body.prompt or not body.prompt.strip():
        logger.error("[/v1/generate/content] empty prompt provided")
        raise HTTPException(status_code=422, detail="prompt cannot be empty")

    if not body.platform.strip():
        logger.error("[/v1/generate/content] empty platform provided")
        raise HTTPException(status_code=422, detail="platform is required")

    if not body.user_id.strip():
        logger.error("[/v1/generate/content] empty user_id provided")
        raise HTTPException(status_code=422, detail="user_id is required")

    if body.type not in {"simple", "viral_thread"}:
        logger.error(f"[/v1/generate/content] invalid type: {body.type}")
        raise HTTPException(status_code=422, detail="type must be 'simple' or 'viral_thread'")

    enforcement_mode = get_enforcement_mode()

    def _build_enforcement_request(content: str) -> EnforcementRequest:
        return EnforcementRequest(
            prompt=body.prompt,
            platform=body.platform,
            user_id=body.user_id,
            request_id=getattr(request.state, "request_id", None),
            content=content,
            publish_intent=False,
        )

    if body.stream:
        if enforcement_mode == "off":
            response_generator = (
                stream_viral_thread_response(body.prompt, user_id=body.user_id)
                if body.type == "viral_thread"
                else stream_groq_response(body.prompt)
            )
            return StreamingResponse(
                response_generator,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        collector: list[str] = []
        response_generator = (
            stream_viral_thread_response(body.prompt, user_id=body.user_id, collector=collector)
            if body.type == "viral_thread"
            else stream_groq_response(body.prompt, collector=collector)
        )

        async def _stream_with_enforcement():
            async for chunk in response_generator:
                yield chunk
            content = "\n".join(collector)
            result = run_enforcement_pipeline(_build_enforcement_request(content))
            enforcement_payload = {
                "request_id": result.request_id,
                "mode": result.mode,
                "receipt": result.receipt.model_dump(mode="json") if result.receipt else None,
                "decisions": [
                    {
                        "agent_name": d.agent_name,
                        "status": d.status,
                        "violation_codes": d.violation_codes,
                        "required_edits": d.required_edits,
                        "decision_id": d.decision_id,
                    }
                    for d in result.decisions
                ],
                "qa_summary": result.qa_summary,
                "would_block": result.would_block,
                "required_edits": result.required_edits,
                "audit_ok": result.audit_ok,
                "warnings": result.warnings,
            }
            yield _format_enforcement_event(enforcement_payload)

        return StreamingResponse(
            _stream_with_enforcement(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming: collect the same cleaned tokens deterministically
    content_parts = []
    response_generator = (
        stream_viral_thread_response(body.prompt, user_id=body.user_id)
        if body.type == "viral_thread"
        else stream_groq_response(body.prompt)
    )
    async for chunk in response_generator:
        token = chunk.replace("data: ", "", 1).strip()
        if token and not token.startswith("ERROR:"):
            content_parts.append(token)

    content = "".join(content_parts)
    if enforcement_mode == "off":
        return {"content": content}

    enforcement_result = run_enforcement_pipeline(_build_enforcement_request(content))
    return {
        "content": content,
        "enforcement": {
            "request_id": enforcement_result.request_id,
            "mode": enforcement_result.mode,
            "receipt": enforcement_result.receipt.model_dump(mode="json") if enforcement_result.receipt else None,
            "decisions": [
                {
                    "agent_name": d.agent_name,
                    "status": d.status,
                    "violation_codes": d.violation_codes,
                    "required_edits": d.required_edits,
                    "decision_id": d.decision_id,
                }
                for d in enforcement_result.decisions
            ],
            "qa_summary": enforcement_result.qa_summary,
            "would_block": enforcement_result.would_block,
            "required_edits": enforcement_result.required_edits,
            "audit_ok": enforcement_result.audit_ok,
            "warnings": enforcement_result.warnings,
        },
    }

# (startup handled by lifespan)


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


# (shutdown handled by lifespan)
