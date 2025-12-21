import pytest
from httpx import ASGITransport, AsyncClient
from types import SimpleNamespace
from backend.main import app

class FakeGroq:
    def __init__(self, *args, **kwargs):
        pass

@pytest.mark.asyncio
async def test_viral_thread_stream_strips_numbering(monkeypatch):
    # Monkeypatch the viral thread generator to return numbered lines
    import backend.agents.viral_thread as vt
    monkeypatch.setattr(vt, "generate_viral_thread", lambda prompt, user_id=None: [
        "1/6 First tweet",
        "Tweet 2: Second tweet",
        "(3) Third",
        "[4] Fourth",
        "5. Fifth",
        "- Sixth"
    ])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/v1/generate/content",
            json={
                "type": "viral_thread",
                "prompt": "topic",
                "platform": "x",
                "user_id": "u",
                "stream": True,
            },
        )
        assert res.status_code == 200
        body = await res.aread()
        text = body.decode("utf-8")
        assert "1/6" not in text
        assert "Tweet 2" not in text
        assert "(3)" not in text
        assert "[4]" not in text
        assert "5." not in text
        assert text.count("data: ") >= 1
