import pytest
from httpx import AsyncClient, ASGITransport
from types import SimpleNamespace
from backend.main import app

class FakeGroq:
    def __init__(self, *args, **kwargs):
        pass

@pytest.mark.asyncio
async def test_simple_streaming(monkeypatch):
    import backend.main as main_mod
    monkeypatch.setattr(main_mod, "groq", SimpleNamespace(Groq=FakeGroq))

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/v1/generate/content",
            json={
                "type": "simple",
                "prompt": "hello world",
                "platform": "x",
                "user_id": "test-user",
                "stream": True,
            },
        )

        assert res.status_code == 200
        # Ensure response is SSE and contains tokens
        body = await res.aread()
        text = body.decode("utf-8")
        assert "data: " in text
