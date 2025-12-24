#!/usr/bin/env python
"""Debug non-holder ring enforcement."""

from fastapi.testclient import TestClient
from backend.main import app
import json

client = TestClient(app)

# Create draft
create_resp = client.post(
    "/v1/collab/drafts",
    headers={"X-User-Id": "holder2"},
    json={"title": "Ring Test 2", "platform": "x"}
)
draft_id = create_resp.json()["data"]["draft_id"]

# Non-holder tries to append
response = client.post(
    f"/v1/collab/drafts/{draft_id}/segments",
    headers={"X-User-Id": "nonholder"},
    json={"content": "Should fail", "idempotency_key": "seg2"}
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
