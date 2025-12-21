import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_generate_requires_fields(client):
    # Missing platform
    res = await client.post("/v1/generate/content", json={
        "prompt": "hello",
        "type": "simple",
        "user_id": "u",
        "stream": True,
    })
    assert res.status_code == 422

    # Missing user_id
    res = await client.post("/v1/generate/content", json={
        "prompt": "hello",
        "type": "simple",
        "platform": "x",
        "stream": True,
    })
    assert res.status_code == 422

    # Invalid type
    res = await client.post("/v1/generate/content", json={
        "prompt": "hello",
        "type": "unknown",
        "platform": "x",
        "user_id": "u",
        "stream": True,
    })
    assert res.status_code == 422

@pytest.mark.asyncio
async def test_generate_openapi_snapshot():
    # Snapshot the openapi schema for the endpoint and assert required fields
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    assert "/v1/generate/content" in paths
    post = paths["/v1/generate/content"].get("post")
    assert post is not None
    schema = post["requestBody"]["content"]["application/json"]["schema"]
    # Resolve $ref if present
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        schema = openapi["components"]["schemas"][ref]
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    assert {"prompt", "type", "platform", "user_id"}.issubset(required)
    assert "stream" in props

@pytest.mark.asyncio
async def test_analytics_openapi_snapshot():
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    assert "/api/analytics/ring/daily" in paths
    assert "/api/analytics/ring/weekly" in paths
