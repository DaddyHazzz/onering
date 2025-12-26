# Phase 10.1 Post-Implementation Audit (Codex Enforcement Scaffold)

**Date:** 2025-12-26  
**Scope:** Review of Codex enforcement scaffolding now present in code; map reality → planned backlog; highlight risks and required follow-ups.

## What Landed in Code
- **Enforcement pipeline:** Implemented in [backend/features/enforcement/service.py](backend/features/enforcement/service.py). Builds Strategy → (optional) Research → Writer → QA → Posting → Analytics shadows. Mostly deterministic stubs; no Groq calls. QA decision drives `would_block` and `required_edits`.
- **Contracts:** Pydantic models + hashing in [backend/features/enforcement/contracts.py](backend/features/enforcement/contracts.py). Contracts enforce extra="forbid"; hashes used in audit metadata.
- **Policy checks:** Minimal rules in [backend/features/enforcement/policy.py](backend/features/enforcement/policy.py): per-line length caps, numbering regex, policy_tags required, optional citations gate. No profanity/harmful content/brand rules yet.
- **Audit logging:** Agent decisions are written to `audit_agent_decisions` (see [backend/features/enforcement/audit.py](backend/features/enforcement/audit.py) and table in [backend/core/database.py](backend/core/database.py)). Writes run when `ONERING_AUDIT_LOG=1` (default). Failure only blocks in enforced mode.
- **SSE enforcement event:** `/v1/generate/content` streams `event: enforcement` when enforcement mode ≠ off (see [backend/main.py](backend/main.py)). Includes decisions array, qa_summary, audit_ok, warnings, would_block.
- **Frontend posting gate:** [src/app/api/post-to-x/route.ts](src/app/api/post-to-x/route.ts) enforces only in `ONERING_ENFORCEMENT_MODE=enforced`: blocks on `audit_ok=false` or `qa_summary.status !== "PASS"`; ignores decisions/warnings.
- **Flags present:** `ONERING_ENFORCEMENT_MODE (off|advisory|enforced)`, `ONERING_AUDIT_LOG ("0"|"1")`, `ONERING_TOKEN_ISSUANCE (off|shadow|live)` in [backend/core/config.py](backend/core/config.py). Default mode is **off**.

## Deviations & Gaps vs Plan
- **Feature flag names differ from plan:** Plan expects `AGENT_ENFORCEMENT_*` / `QA_BLOCKING_ENABLED`; code uses `ONERING_ENFORCEMENT_MODE` and ties QA blocking to same flag. Docs need reconciliation.
- **Enforcement default off:** No advisory rollout active; generation/posting bypass enforcement unless env set.
- **QA policy minimal:** Only numbering/length/policy_tags/citations. Missing profanity, TOS, harmful-content redirection, platform limits per whole post, brand filters.
- **No suggestedFix/error taxonomy in backend:** Errors returned are generic HTTP errors; no `EnforcementError` model or enum mapping.
- **Audit path creates tables at runtime:** `create_all_tables()` on every audit write may clash with migrations/permissions; no retention policy enforcement.
- **Analytics/Post-tokenization missing:** Posting/Analytics agents are placeholders; no RING calc, no integration with posting service, no telemetry reducers/tests.
- **SSE contract mismatches:** `decisions[].status` is lowercase (`pass|fail`), while plan/API reference document uppercase. `would_block` logic sets `False` in advisory even if audit fails.
- **Frontend gate narrow:** Posting gate ignores `decisions` and `warnings`; rate limit remains 5 posts/hour (plan says 5 per 15min baseline). No guard for missing enforcement payload in enforced mode.
- **Tests absent:** No unit/integration tests cover enforcement models, pipeline, SSE, or posting gate behavior.

## Backlog Rebase (Map to 10.1-Txx)
- **10.1-T01/T02 (Contracts + errors):** Partial. Contracts exist but not in `backend/models/enforcement.py`; no error enum/suggestedFix mapping.
- **10.1-T03/T04 (Telemetry schema + DDL):** Partial. `audit_agent_decisions` table exists and writes occur; no documented DDL in `.ai/MIGRATIONS.md`; runtime table creation remains.
- **10.1-T05/T14/T25 (Flag policy/rollout):** Not implemented. Flags differ from docs; rollout OFF→advisory→enforced not wired; kill-switch undocumented in code.
- **10.1-T06 (Orchestrator responsibilities):** Partial. QA is only blocker in code, but Posting/Analytics remain stubs; no circuit breaker.
- **10.1-T07/T08/T21/T26 (API doc metadata & errors):** Docs describe metadata; actual payload shape differs (lowercase statuses, warnings, audit_ok) and errors lack suggestedFix. Needs doc sync + examples from real payload.
- **10.1-T10 (Error catalog):** Not implemented; backend does not emit catalogued codes.
- **10.1-T15–T19/T27/T28 (Tests/acceptance):** Not implemented.
- **10.1-T20 (Monitoring docs):** Observability dashboard changes not wired to enforcement telemetry.

## Risks
- **Silent bypass:** Default off + frontend ignoring enforcement payload allows posting without QA even if backend runs advisory.
- **Operational load:** Runtime table creation on every audit write can block under contention or limited DB perms.
- **Policy weakness:** Missing profanity/harmful checks and platform TOS allow disallowed content through in enforced mode.
- **Contract drift:** SSE payload shape diverges from documented plan; consumers may misparse statuses/edits.

## Recommended Next Steps
1. Align flags/names: adopt `AGENT_ENFORCEMENT_MODE` or document `ONERING_*` as canonical; add kill-switch path.
2. Harden QA policy: add profanity/harmful/TOS/length-per-post checks; keep numbering regex; return suggestedFix list.
3. Stop runtime migrations: remove `create_all_tables()` from request path; add Alembic/SQL DDL in `.ai/MIGRATIONS.md` and migrations pipeline.
4. Fix SSE contract: uppercase statuses, include `mode` in event, keep `warnings`; update docs and posting gate to validate presence.
5. Expand posting gate: require enforcement payload in enforced mode, propagate violation codes to UI; sync rate limit to plan (5 per 15min or dynamic tiers).
6. Add tests: unit tests for contracts/policy, pipeline would_block logic, SSE event shape, posting gate behavior, audit write fallbacks.
7. Document DDL and retention: add `audit_agent_decisions` schema and retention/TTL decision to `.ai/MIGRATIONS.md` + `.ai/PROJECT_STATE.md`.
