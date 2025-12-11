import pytest
from backend.agents.langgraph.orchestrator import run_workflow

def test_run_workflow_basic():
    result = run_workflow("Test prompt: make this go viral", user_context={"brand":"test"})
    assert isinstance(result, dict)
    assert result.get("ok") in (True, False)
