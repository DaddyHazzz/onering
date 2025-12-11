"""Small orchestrator to be invoked by RQ worker jobs.

Example usage (from RQ job):
    from backend.agents.langgraph.orchestrator import run_workflow
    run_workflow(prompt, user_context)

This file should be imported by your existing RQ task implementation.
"""
from .workflows import generate_and_post
import logging

logger = logging.getLogger("onering.langgraph.orch")

def run_workflow(prompt: str, user_context: dict = None):
    logger.info("Orchestrator received prompt: %s", prompt[:120])
    result = generate_and_post(prompt, user_context)
    logger.info("Orchestrator finished: %s", result)
    return result
