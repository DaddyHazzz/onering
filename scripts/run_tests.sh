#!/usr/bin/env bash
set -euo pipefail

# Backend tests
if [ -d "backend" ]; then
  echo "Running backend tests (pytest)"
  (cd backend && pytest -q)
fi

# Frontend tests
echo "Running frontend tests (vitest)"
pnpm test -- --run
