"""Example LangGraph-style workflow orchestration.

This file shows a simple synchronous orchestration pattern that calls each agent in sequence.
Replace the 'call_agent' placeholders with real LangGraph or LangChain calls, or with direct LLM SDK calls.
"""
import logging
from agents import strategy_agent, research_agent, writer_agent, posting_agent, analytics_agent

logger = logging.getLogger("onering.langgraph")

def call_agent(agent_fn, *args, **kwargs):
    """Wrapper to call agent functions with centralized error handling.
    Replace internal logic with proper LangGraph task invocation.
    """
    try:
        result = agent_fn.run(*args, **kwargs)
        return {"ok": True, "result": result}
    except Exception as e:
        logger.exception("Agent %s failed: %s", agent_fn.__name__, e)
        return {"ok": False, "error": str(e)}

def generate_and_post(prompt: str, user_context: dict = None):
    """High-level workflow:
    1. Strategy -> define angle / pillars
    2. Research -> fetch sources / facts
    3. Writer -> produce multi-format content
    4. Posting -> schedule/post to platforms
    5. Analytics -> record metrics
    """
    user_context = user_context or {}

    # 1) Strategy
    logger.info("Workflow: running Strategy Agent")
    s = call_agent(strategy_agent, prompt, user_context)
    if not s['ok']:
        return {"ok": False, "stage": "strategy", "error": s.get('error')}

    strategy = s['result']

    # 2) Research
    logger.info("Workflow: running Research Agent")
    r = call_agent(research_agent, strategy, user_context)
    if not r['ok']:
        return {"ok": False, "stage": "research", "error": r.get('error')}

    research = r['result']

    # 3) Writer
    logger.info("Workflow: running Writer Agent")
    w = call_agent(writer_agent, strategy, research, user_context)
    if not w['ok']:
        return {"ok": False, "stage": "writer", "error": w.get('error')}

    content = w['result']

    # 4) Posting
    logger.info("Workflow: running Posting Agent")
    p = call_agent(posting_agent, content, user_context)
    if not p['ok']:
        return {"ok": False, "stage": "posting", "error": p.get('error')}

    post_result = p['result']

    # 5) Analytics
    logger.info("Workflow: running Analytics Agent")
    a = call_agent(analytics_agent, post_result, user_context)
    if not a['ok']:
        # non-fatal in some modes; choose rollback behavior in config
        return {"ok": False, "stage": "analytics", "error": a.get('error')}

    analytics = a['result']

    return {
        "ok": True,
        "strategy": strategy,
        "research": research,
        "content": content,
        "post_result": post_result,
        "analytics": analytics
    }
