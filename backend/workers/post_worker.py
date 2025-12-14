# backend/workers/post_worker.py
import os
import logging
import time
from typing import Dict
from redis import Redis

logger = logging.getLogger("onering")

# Initialize Redis for failure tracking
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)


def update_post_status(post_id: str, status: str, error_msg: str = None):
    """Update post status in Redis (mock persistence for now)."""
    key = f"post:{post_id}:status"
    redis_conn.set(key, status)
    if error_msg:
        redis_conn.set(f"post:{post_id}:error", error_msg)
    logger.info(f"[post_worker] updated {post_id} status: {status}")


def post_to_twitter(content: str, user_id: str, external_id: str = None) -> Dict:
    """
    Post content to Twitter via RQ worker with retry logic.

    Args:
        content: Tweet content (will be split into thread if needed)
        user_id: Clerk user ID
        external_id: Post ID in database

    Returns:
        Dict with success status, tweet_id, and url
    """
    try:
        logger.info(f"[post_worker] posting to Twitter for user {user_id}, content_len={len(content)}")

        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if not lines:
            error = "No content to post"
            logger.error(f"[post_worker] {error} for user {user_id}")
            if external_id:
                update_post_status(external_id, "failed", error)
            return {"success": False, "error": error}

        # In production, integrate with Twitter API here
        # For now, simulate successful posts with 90% success rate for demo
        import random
        if random.random() > 0.9:
            error = "Simulated Twitter API error"
            logger.error(f"[post_worker] {error}")
            if external_id:
                update_post_status(external_id, "failed", error)
            raise Exception(error)

        previous_tweet_id = f"tweet_{user_id}_{int(time.time())}"

        for i, line in enumerate(lines):
            text = line if len(lines) == 1 else f"{i + 1}/{len(lines)} {line}"
            logger.info(f"[post_worker] simulated tweet {i+1}: {text[:50]}...")
            # Real integration would post here
            previous_tweet_id = f"tweet_{i}_{int(time.time())}"

        url = f"https://x.com/{os.getenv('TWITTER_USERNAME', 'i')}/status/{previous_tweet_id}"
        logger.info(f"[post_worker] successfully posted thread for user {user_id}, url={url}")

        if external_id:
            update_post_status(external_id, "published")

        return {
            "success": True,
            "tweet_id": previous_tweet_id,
            "url": url,
            "user_id": user_id,
        }
    except Exception as e:
        logger.error(f"[post_worker] error posting to Twitter: {e}")
        if external_id:
            update_post_status(external_id, "failed", str(e))
        return {"success": False, "error": str(e)}


def schedule_post(content: str, user_id: str, delay_seconds: int, external_id: str = None) -> Dict:
    """
    Schedule a post to Twitter after a delay with retry logic.
    Used by RQ to queue delayed posts.
    RQ will automatically retry on failure based on job config.

    Args:
        content: Tweet content
        user_id: Clerk user ID
        delay_seconds: Seconds to wait before posting
        external_id: Post ID in database

    Returns:
        Dict with success status
    """
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"[post_worker] sleeping for {delay_seconds} seconds before posting for user {user_id}")
            time.sleep(delay_seconds)
            logger.info(f"[post_worker] delay complete, now posting for user {user_id}")

            result = post_to_twitter(content, user_id, external_id)

            if result.get("success"):
                return result
            else:
                # Post failed, retry
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[post_worker] post failed for {user_id}, retrying (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed, mark as dead-letter
                    logger.error(f"[post_worker] post failed after {max_retries} attempts for {user_id}")
                    if external_id:
                        update_post_status(external_id, "failed", result.get("error", "Unknown error"))
                    return result
        except Exception as e:
            logger.error(f"[post_worker] error in schedule_post (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.warning(f"[post_worker] retrying after delay...")
                time.sleep(retry_delay)
            else:
                # Final attempt, dead-letter
                logger.error(f"[post_worker] schedule_post failed after {max_retries} attempts for {user_id}")
                if external_id:
                    update_post_status(external_id, "failed", str(e))
                return {"success": False, "error": str(e)}

    return {"success": False, "error": "Max retries exceeded"}
