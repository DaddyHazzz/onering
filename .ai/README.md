# OneRing AI Documentation — Canonical Source

**Purpose:** Single source of truth for AI agents, developers, and stakeholders. All docs here are kept in sync.

**Last Updated:** December 25, 2025

## Quick Navigation

| Need | Link | Purpose |
|------|------|---------|
| **What is OneRing?** | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Vision, narrative, scope |
| **How do I build it?** | [ARCHITECTURE.md](ARCHITECTURE.md) | Backend/frontend/DB/auth stack |
| **What APIs exist?** | [API_REFERENCE.md](API_REFERENCE.md) | Stable endpoints + contracts |
| **How do I test?** | [TESTING.md](TESTING.md) | Fast gates, full gates, CI/CD |
| **What's the plan?** | [ROADMAP.md](ROADMAP.md) | Next phases, priorities |
| **What's the status?** | [PROJECT_STATE.md](PROJECT_STATE.md) | Latest test counts + date |
| **Why design X?** | [DECISIONS.md](DECISIONS.md) | Architecture + trade-off rationale |
| **Open questions?** | [OPEN_QUESTIONS_AND_TODOS.md](OPEN_QUESTIONS_AND_TODOS.md) | Unresolved decisions + tech debt |
| **Phase 10 plan?** | [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) | Comprehensive Phase 10 execution plan |
| **Phase history** | [PHASES/](PHASES/) | Active specs + archives in PHASES/COMPLETED |
| **Agent system** | [AGENTS_OVERVIEW.md](AGENTS_OVERVIEW.md) | Strategy, Research, Writer, QA agents + more |
| **Agent tasks** | [TASKS.md](TASKS.md) | Fast tasks vs. agent delegations |
| **Agent template** | [AGENT_BRIEF.md](AGENT_BRIEF.md) | How to brief a background agent |
| **Session handoff** | [HANDOFF_PACK/README.md](HANDOFF_PACK/README.md) | 20 critical docs to start sessions |

## Structure

```
.ai/
  README.md                    <- You are here
  PROJECT_CONTEXT.md          <- Vision + narrative
  ARCHITECTURE.md             <- Tech stack + design
  API_REFERENCE.md            <- Stable contracts
  TESTING.md                  <- Test strategies + gates
  ROADMAP.md                  <- Next phases
  PROJECT_STATE.md            <- Current status + test counts
  DECISIONS.md                <- Design decisions + rationale
  OPEN_QUESTIONS_AND_TODOS.md <- Unresolved questions + tech debt
  TASKS.md                    <- Task board (fast + agent)
  AGENTS_OVERVIEW.md          <- Agent system (Strategy, Research, Writer, QA, etc.)
  AGENT_BRIEF.md              <- Agent work template
  PHASES/
    PHASE_8.md                <- Phase 8 rollup (8.4–8.7.1b)
    PHASE_9.md                <- Phase 9 stub (next)
```

## For New Developers

**Onboarding (15 min):**
1. Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) (what are we building?)
2. Skim [ARCHITECTURE.md](ARCHITECTURE.md) (where do I code?)
3. Check [TESTING.md](TESTING.md) (how do I run tests?)
4. Browse [ROADMAP.md](ROADMAP.md) (what's next?)

**For feature work:** Check [ROADMAP.md](ROADMAP.md) → find phase → see [PHASES/](PHASES/) for specs.

**For refactors:** Check [DECISIONS.md](DECISIONS.md) for "why" before changing design.

## For AI Agents

**Starting a task:**
1. Read the issue/brief
2. Link relevant `.ai/*` files
3. Run [TESTING.md](TESTING.md) fast lane (fast + local verification)
4. Run full gates before push
5. Report: files changed + test diffs

**Delegating work:** Use [AGENT_BRIEF.md](AGENT_BRIEF.md) template to brief background agents.

## Source Migration

Old docs (root + `/docs/`) → New canonical (`.ai/`):

| Old | New | Status |
|-----|-----|--------|
| `/docs/ARCHITECTURE.md` | `ARCHITECTURE.md` | ✅ Migrated |
| `/docs/API_REFERENCE.md` | `API_REFERENCE.md` | ✅ Migrated |
| `/docs/ROADMAP.md` | `ROADMAP.md` | ✅ Migrated |
| `PROJECT_STATE.md` (root) | `PROJECT_STATE.md` | ✅ Moved |
| `DESIGN_DECISIONS.md` (root) | `DECISIONS.md` | ✅ Consolidated |
| `/docs/PHASE8_*.md` | `PHASES/PHASE_8.md` | ✅ Consolidated |
| `/docs/AGENTS_OVERVIEW.md` | `TASKS.md` + `AGENT_BRIEF.md` | ✅ Consolidated |

**Old doc locations:** Contain banners linking to `.ai/` canonical. Safe to reference old paths; they redirect.

## Key Invariants

✅ **GREEN ALWAYS:** No skipped tests in mainline. Fast gates before push.  
✅ **Windows-friendly:** All scripts support PowerShell 5.1+.  
✅ **Deterministic:** Stable selectors, no flaky timeouts.  
✅ **Single source:** If it's not in `.ai/`, it's not canonical.  
✅ **Choose your gate:** `ONERING_GATE=fast|full|docs` controls hooks; pre-commit runs fast by default, pre-push runs full only if `full`.

## Questions?

- **"Where do I find...?"** → Check the Navigation table above.
- **"Why is this design?"** → Check [DECISIONS.md](DECISIONS.md).
- **"What's the test status?"** → Check [PROJECT_STATE.md](PROJECT_STATE.md).
- **"What should I work on?"** → Check [ROADMAP.md](ROADMAP.md) or [TASKS.md](TASKS.md).
