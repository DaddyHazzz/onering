#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."

echo "==========================================="
echo "OneRing Test Suite (Phase 3.7)"
echo "==========================================="
echo

# Detect Python (prefer venv on Windows and POSIX)
PYTHON="python"
if [ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]; then
  PYTHON="${REPO_ROOT}/.venv/Scripts/python.exe"
elif [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PYTHON="${REPO_ROOT}/.venv/bin/python"
fi

# Backend tests
echo "BACKEND TESTS"
echo "Running backend tests with DATABASE_URL..."
export DATABASE_URL="postgresql://user:pass@localhost:5432/onering"
export PYTHONPATH="${REPO_ROOT}"

pushd "${REPO_ROOT}" >/dev/null
"${PYTHON}" -m pytest backend/tests/ -q --tb=no
popd >/dev/null

# Frontend tests
echo
echo "FRONTEND TESTS"
echo "Running: pnpm test -- --run"
pushd "${REPO_ROOT}" >/dev/null
pnpm test -- --run
popd >/dev/null
