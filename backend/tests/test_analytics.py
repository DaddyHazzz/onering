import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_ring_daily():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/analytics/ring/daily",
            params={"userId": "test-user"},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_ring_weekly():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/analytics/ring/weekly",
            params={"userId": "test-user"},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_ring_daily_empty(monkeypatch):
    import backend.api.analytics as analytics

    def no_posts(user_id: str, start, end):
        return []

    monkeypatch.setattr(analytics, "_mock_fetch_user_posts", no_posts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/analytics/ring/daily",
            params={"userId": "test-user"},
        )
        assert res.status_code == 200
