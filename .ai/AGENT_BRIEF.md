# Agent Brief Template

Fill this before delegating larger tasks to agents.

## Objective
What outcome is required? State constraints and success criteria.

## Context
Relevant architecture, files, prior phases. Link to .ai/* docs.

## Deliverables
- Code changes (files, modules)
- Tests (unit/integration/UI)
- Docs updates

## Acceptance Tests
Explicit steps and expected outputs. Deterministic inputs with `now` if time-based.

## Non-Negotiables
- All tests GREEN (backend+frontend), zero skipped, no `--no-verify`
- Windows-friendly scripts
- Preserve existing architecture decisions (.ai/DECISIONS.md)

## Reporting
Provide summary: what changed, why, where. Update .ai/PROJECT_STATE.md.
