import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_generate_content_success():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/v1/generate/content",
            json={
                "type": "simple",
                "prompt": "test topic",
                "platform": "x",
                "user_id": "test-user",
                "stream": False,
            },
        )

        assert res.status_code == 200
