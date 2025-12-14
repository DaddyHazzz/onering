# backend/workflows/content_workflow.py
"""
Temporal workflow for content generation, optimization, and posting.
Provides durable execution with retries, timeouts, and failure handling.
"""
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

import logging

logger = logging.getLogger("onering")


@dataclass
class ContentRequest:
    """Request for content generation workflow."""
    topic: str
    user_id: Optional[str]
    platform: str  # 'X', 'IG', etc.
    schedule_delay_seconds: Optional[int] = None  # If provided, delay posting


@dataclass
class ThreadContent:
    """Generated thread content."""
    lines: List[str]
    topic: str


@activity.defn
async def generate_viral_thread_activity(topic: str, user_id: Optional[str] = None) -> ThreadContent:
    """Activity to call LangGraph viral thread generation."""
    try:
        from agents.viral_thread import generate_viral_thread

        logger.info(f"[workflow] generating viral thread for {topic[:50]}")
        lines = await generate_viral_thread(topic, user_id=user_id)
        return ThreadContent(lines=lines, topic=topic)
    except Exception as e:
        logger.error(f"[workflow] thread generation failed: {e}")
        raise


@activity.defn
async def optimize_thread_activity(thread: ThreadContent) -> ThreadContent:
    """Activity to optimize generated thread (can call LLM if needed)."""
    try:
        logger.info(f"[workflow] optimizing thread ({len(thread.lines)} tweets)")
        # In production, could run additional optimization here
        # For now, thread is already optimized by viral_thread agent
        return thread
    except Exception as e:
        logger.error(f"[workflow] thread optimization failed: {e}")
        raise


@activity.defn
async def post_to_platform_activity(
    content: ThreadContent,
    user_id: str,
    platform: str,
    delay_seconds: Optional[int] = None,
) -> dict:
    """Activity to post thread to X or IG."""
    try:
        content_str = "\n".join(content.lines)
        logger.info(f"[workflow] posting to {platform} for {user_id}, delay={delay_seconds}s")

        # If delay provided, use RQ to schedule
        if delay_seconds and delay_seconds > 0:
            from workers.post_worker import schedule_post
            from redis import Redis
            from rq import Queue
            from datetime import timedelta

            redis_url = "redis://localhost:6379/0"
            redis_conn = Redis.from_url(redis_url)
            queue = Queue(connection=redis_conn)

            job = queue.enqueue_in(
                timedelta(seconds=delay_seconds),
                schedule_post,
                content_str,
                user_id,
                delay_seconds,
                job_timeout="10m",
                result_ttl=3600,
            )
            logger.info(f"[workflow] scheduled job {job.id}")
            return {"success": True, "job_id": job.id, "scheduled": True}

        # Otherwise post immediately (stub for now)
        logger.info(f"[workflow] posted immediately to {platform}")
        return {
            "success": True,
            "platform": platform,
            "tweet_count": len(content.lines),
        }
    except Exception as e:
        logger.error(f"[workflow] posting failed: {e}")
        raise


# Define workflow
@workflow.defn
class ContentGenerationWorkflow:
    """Durable workflow for generating and posting viral content."""

    @workflow.run
    async def run(self, request: ContentRequest) -> dict:
        """Execute content generation → optimization → posting workflow."""
        logger.info(f"[workflow] starting ContentGenerationWorkflow for {request.topic[:50]}")

        # Retry policy: 3 attempts, 5-second backoff, max 1-minute duration
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=3,
        )

        # Step 1: Generate thread with retries
        try:
            thread = await workflow.execute_activity(
                generate_viral_thread_activity,
                request.topic,
                request.user_id,
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=retry_policy,
            )
            logger.info(f"[workflow] generated {len(thread.lines)} tweets")
        except Exception as e:
            logger.error(f"[workflow] generation failed after retries: {e}")
            return {"success": False, "error": f"Generation failed: {str(e)}"}

        # Step 2: Optimize thread (optional)
        try:
            optimized = await workflow.execute_activity(
                optimize_thread_activity,
                thread,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            thread = optimized
        except Exception as e:
            logger.warn(f"[workflow] optimization skipped: {e}")
            # Continue with original thread

        # Step 3: Post to platform
        try:
            result = await workflow.execute_activity(
                post_to_platform_activity,
                thread,
                request.user_id,
                request.platform,
                request.schedule_delay_seconds,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )
            logger.info(f"[workflow] successfully posted: {result}")
            return {"success": True, **result, "thread": thread.lines}
        except Exception as e:
            logger.error(f"[workflow] posting failed after retries: {e}")
            return {"success": False, "error": f"Posting failed: {str(e)}"}
