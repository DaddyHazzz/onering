Source: .ai/DECISIONS.md (Sections: Governance, Hooks, Testing)

# Repository Policies (Session Handoff)

- Canonical docs live in .ai/; docs/ are stubs.
- Hooks are disabled by default. Enable explicitly with env vars:
  - pre-commit: `ONERING_HOOKS=1 ONERING_GATE=docs|fast|full`
  - pre-push: `ONERING_HOOKS=1 ONERING_GATE=full`
- Recursion guard: `ONERING_HOOK_RUNNING` prevents nested gate invocations.
- One commit per task. Never push without explicit instruction.
- Default to `pnpm gate --mode docs` for docs-only work.
- GREEN ALWAYS: all tests pass, zero skipped.
- Preserve core stack choices (Clerk, Groq, FastAPI, RQ, Redis, Postgres+pgvector, Stripe).
- Avoid deleting files unless explicitly asked.
