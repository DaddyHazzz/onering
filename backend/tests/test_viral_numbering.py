import pytest
import re

from backend.agents import viral_thread as vt

class FakeResponse:
    def __init__(self, content: str):
        self.content = content

class FakeLLM:
    def invoke(self, messages):
        # Return numbered tweets to test cleanup
        numbered = (
            "1/6 First tweet with number\n\n"
            "Tweet 2: Second tweet label\n\n"
            "(3) Third tweet parentheses\n\n"
            "[4] Fourth tweet bracket\n\n"
            "5. Fifth tweet dot\n\n"
            "- Sixth tweet bullet"
        )
        return FakeResponse(numbered)

@pytest.mark.parametrize("topic", ["AI", "Startups", "Growth hacking"])
def test_optimizer_removes_numbering(monkeypatch, topic):
    # Patch the llm used by writer/optimizer
    monkeypatch.setattr(vt, 'llm', FakeLLM())

    tweets = vt.generate_viral_thread(topic)
    assert tweets, "expected some tweets"

    for t in tweets:
        assert not re.match(r"^\d", t), f"tweet starts with digit: {t}"
        assert not re.match(r"^(?:Tweet\s+)?\d+", t), f"tweet has 'Tweet X' prefix: {t}"
        assert not re.match(r"^[\-•*]", t), f"tweet starts with bullet: {t}"
        assert len(t) > 10
