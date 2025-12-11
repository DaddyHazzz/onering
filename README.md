OneRing backend skeleton (FastAPI + RQ worker)
---------------------------------------------
Quickstart (development):
  1. python -m venv .venv
  2. source .venv/bin/activate   # or .venv\Scripts\activate on Windows
  3. pip install -r requirements.txt
  4. Start Redis (recommended via docker-compose in repo root):
     docker-compose -f infra/docker-compose.yml up -d
  5. Start the app:
     uvicorn main:app --reload --port 8000
  6. Start worker (in a separate shell):
     rq worker -u redis://localhost:6379 default
