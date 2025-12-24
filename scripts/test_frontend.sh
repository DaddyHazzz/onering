#!/usr/bin/env bash
set -euo pipefail

pnpm install --frozen-lockfile
pnpm lint
pnpm test -- --run
pnpm typecheck
