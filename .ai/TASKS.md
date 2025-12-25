# Task Conventions

## Fast-Lane Tasks
- Small scope, localized changes
- Use changed-only test lanes (see .ai/TESTING.md)
- Aim for <30 minutes turnaround

## Agent Tasks
- Multi-step, cross-cutting (backend + frontend + docs)
- Require a brief (see .ai/AGENT_BRIEF.md)
- Must update .ai/PROJECT_STATE.md when done

## Definition of Done
- All tests green (backend and frontend)
- Zero skipped, no `--no-verify`
- Deterministic, Windows-friendly commands
- Docs updated if behavior or contracts changed
