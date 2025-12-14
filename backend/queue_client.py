# backend/queue_client.py
"""
RQ Queue client for use from Next.js API routes via subprocess or HTTP.
This module provides functions to enqueue jobs to the Redis queue.
"""
import os
import json
from redis import Redis
from rq import Queue
from workers.post_worker import schedule_post

# Initialize Redis and queue
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)
queue = Queue(connection=redis_conn)


def enqueue_scheduled_post(content: str, user_id: str, delay_seconds: int, post_id: str = None):
    """
    Enqueue a scheduled post job to RQ.

    Args:
        content: Tweet content
        user_id: Clerk user ID
        delay_seconds: Delay before posting
        post_id: Database post ID

    Returns:
        Job ID
    """
    job = queue.enqueue_in(
        "seconds" if delay_seconds < 60 else "minutes",
        schedule_post,
        content,
        user_id,
        delay_seconds,
        post_id,
        job_timeout="10m",
        result_ttl=3600,  # Keep result for 1 hour
    )
    return job.id


if __name__ == "__main__":
    # For testing
    job_id = enqueue_scheduled_post(
        "test content",
        "test_user",
        60,
        "test_post"
    )
    print(f"Enqueued job: {job_id}")
