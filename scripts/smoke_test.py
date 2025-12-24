"""Smoke test for REST + WS flows.

Steps:
1) Create draft
2) Add collaborator
3) Append segment
4) Connect WS and await first event
5) Pass ring

Requires BASE_URL (default http://localhost:8000) and uses X-User-Id header only.
"""
import asyncio
import os
import sys
from uuid import uuid4

import httpx
import websockets

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
USER_ID = os.getenv("SMOKE_USER_ID", "smoke-user")
COLLAB_ID = os.getenv("SMOKE_COLLAB_ID", "smoke-collab")
TIMEOUT_SECONDS = float(os.getenv("SMOKE_TIMEOUT", "5"))


def _ws_url(path: str) -> str:
    if BASE_URL.startswith("https://"):
        return BASE_URL.replace("https://", "wss://", 1) + path
    return BASE_URL.replace("http://", "ws://", 1) + path


def _require_data(resp: httpx.Response, step: str):
    if resp.status_code != 200:
        raise RuntimeError(f"{step} failed: status={resp.status_code}, body={resp.text}")
    body = resp.json()
    if "data" not in body:
        raise RuntimeError(f"{step} missing data field: {body}")
    return body["data"]


def run_rest_flow(client: httpx.Client):
    headers = {"X-User-Id": USER_ID}

    draft_resp = client.post(
        f"{BASE_URL}/v1/collab/drafts",
        json={"title": "Smoke Draft", "platform": "x", "initial_segment": "hello"},
        headers=headers,
    )
    draft = _require_data(draft_resp, "create draft")
    draft_id = draft.get("draft_id") or draft.get("id") or draft.get("draftId")
    if not draft_id:
        raise RuntimeError(f"Missing draft_id in create draft response: {draft}")

    collab_resp = client.post(
        f"{BASE_URL}/v1/collab/drafts/{draft_id}/collaborators",
        params={"collaborator_id": COLLAB_ID, "role": "contributor"},
        headers=headers,
        json={},
    )
    _require_data(collab_resp, "add collaborator")

    seg_resp = client.post(
        f"{BASE_URL}/v1/collab/drafts/{draft_id}/segments",
        json={"content": "Smoke segment", "idempotency_key": str(uuid4())},
        headers=headers,
    )
    _require_data(seg_resp, "append segment")

    return draft_id


async def wait_for_ws_event(draft_id: str) -> None:
    headers = {"X-User-Id": USER_ID, "X-Request-Id": str(uuid4())}
    ws_path = f"/v1/ws/drafts/{draft_id}"
    ws_url = _ws_url(ws_path)

    async with websockets.connect(ws_url, extra_headers=headers) as websocket:
        msg = await asyncio.wait_for(websocket.recv(), timeout=TIMEOUT_SECONDS)
        if not msg:
            raise RuntimeError("No WS message received")


def pass_ring(client: httpx.Client, draft_id: str):
    headers = {"X-User-Id": USER_ID}
    resp = client.post(
        f"{BASE_URL}/v1/collab/drafts/{draft_id}/pass-ring",
        json={"to_user_id": COLLAB_ID, "idempotency_key": str(uuid4())},
        headers=headers,
    )
    _require_data(resp, "pass ring")


def main() -> int:
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            draft_id = run_rest_flow(client)
            asyncio.run(wait_for_ws_event(draft_id))
            pass_ring(client, draft_id)
        print("SMOKE PASS")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
