Source: ../CONTRIBUTIONS.md

# Contributing to OneRing

See the canonical guidance files:
- .ai/TESTING.md — test requirements, fast/full gates
- .ai/TASKS.md — task conventions
- .ai/AGENT_BRIEF.md — delegation brief template
- .ai/DECISIONS.md — architecture constraints

## Quick Checklist
- [ ] Read .ai/PROJECT_STATE.md for current status
- [ ] Run `pnpm gate` (fast lane) or `pnpm gate -Full` (full suites)
- [ ] All tests GREEN, zero skipped
- [ ] Update .ai/ docs if behavior changed
- [ ] Commit with scope from DECISIONS.md (docs/api/feature/fix/chore)
- [ ] No `--no-verify` commits
