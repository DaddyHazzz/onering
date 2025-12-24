#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}" || exit 1

# Frontend gates
pnpm lint
pnpm typecheck
pnpm test -- --run

# Backend gates (skip if DATABASE_URL is not configured to avoid blocking dev)
if [ -n "${DATABASE_URL:-}" ]; then
  python -m pytest backend/tests -q
else
  echo "Skipping backend tests (DATABASE_URL not set)."
fi
