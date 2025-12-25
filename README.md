# OneRing

Canonical documentation lives in `.ai/`.

Start here → **[.ai/README.md](.ai/README.md)**

## Quick Links
- **Project Context:** `.ai/PROJECT_CONTEXT.md`
- **Architecture:** `.ai/ARCHITECTURE.md`
- **API Reference:** `.ai/API_REFERENCE.md`
- **Testing & Gates:** `.ai/TESTING.md`
- **Current State:** `.ai/PROJECT_STATE.md`

## Quick Start
- Frontend: `pnpm install && pnpm dev`
- Backend: `pip install -r backend/requirements.txt`
- API: `python -m uvicorn backend.main:app --port 8000`

## Testing
- Fast (default): `pnpm gate --mode fast`
- Full (manual, once): `pnpm gate --mode full`
- Docs-only: `pnpm gate --mode docs`

## Hooks
- Hooks live in `.githooks/`
- `pre-commit` → fast gate
- `pre-push` → opt-in full gate via `ONERING_GATE=full`

Nothing else belongs in this file.
