import time
import logging
from services.x_client import post_to_x

logger = logging.getLogger("onering")

def create_post_task(prompt: str):
    """Background task that generates content (placeholder) and posts it."""
    logger.info("Running create_post_task for prompt: %s", prompt[:120])
    # Placeholder generation step (swap for Grok/Groq call)
    generated = f"[AUTO-GENERATED THREAD]\nPrompt: {prompt}\n1) Example line\n2) Example line\n\n#OneRing"
    # Simulate some processing time
    time.sleep(1)
    resp = post_to_x(generated)
    logger.info("Posted to X result: %s", resp)
    return {"ok": True, "resp": resp}
