Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# Smoke Test (REST + WS)

Use `scripts/smoke_test.py` to validate a deployed environment end-to-end.

## Prereqs
- Backend reachable at `BASE_URL` (default `http://localhost:8000`).
- Python 3.10+ with `pip install -r backend/requirements.txt` (includes `httpx` and `websockets`).

## Run
```bash
export BASE_URL=http://localhost:8000
export SMOKE_USER_ID=smoke-user
export SMOKE_COLLAB_ID=smoke-collab
python scripts/smoke_test.py
```

On Windows PowerShell:
```powershell
$env:BASE_URL="http://localhost:8000"
$env:SMOKE_USER_ID="smoke-user"
$env:SMOKE_COLLAB_ID="smoke-collab"
python scripts/smoke_test.py
```

The script will:
1) Create a draft
2) Add a collaborator
3) Append a segment
4) Open a WebSocket to `/v1/ws/drafts/{id}` and wait for the first message
5) Pass the ring to the collaborator

Outputs `SMOKE PASS` on success and exits non-zero with `SMOKE FAIL` on error.
