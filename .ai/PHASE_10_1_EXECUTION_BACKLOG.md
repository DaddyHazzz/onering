# Phase 10.1 — Execution Backlog (Agent-First Enforcement)

Last Updated: December 25, 2025
Source of Truth: [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md#part-b-agent-enforcement-deep-dive-phase-101)

## Objective (Tight)
Make AI agents mandatory gates for all content generation, with telemetry, audit trails, and QA enforcement; roll out safely via feature flags from off → advisory → enforced.

## Workstream Dependency Graph

Workstreams (W1–W8):
- W1: Contracts & Schemas
- W2: Audit Persistence
- W3: Enforcement Orchestrator
- W4: Endpoint Integration
- W5: Error Shapes & suggestedFix
- W6: Feature Flags & Rollout
- W7: Tests
- W8: Docs Updates

Dependencies:
```
W1 (Contracts) ─┬─> W3 (Enforcer) ─┬─> W4 (Endpoints)
                │                  └─> W7 (Tests)
                └─> W2 (Audit) ──────> W7 (Tests)
W5 (Errors) ──────────────────────────> W4 (Endpoints), W7
W6 (Flags)  ──────────────────────────> W3, W4, W7
W8 (Docs)   ──────────────────────────> all
```

## Backlog — One Commit Per Task

Notes:
- Rollout impact: none = internal-only docs/config; advisory = surfaces metadata/warnings, never blocks; enforced = can block generation/posting via QA.
- Owner role: backend/frontend/devops as primary driver.

### Rebase Snapshot (2025-12-26)
- Current code implements a minimal enforcement pipeline + audit writes (see [PHASE_10_1_POST_IMPLEMENTATION_AUDIT.md](PHASE_10_1_POST_IMPLEMENTATION_AUDIT.md)).
- Flag names differ (`ONERING_ENFORCEMENT_MODE`, `ONERING_AUDIT_LOG`, `ONERING_TOKEN_ISSUANCE`); rollout defaults to off.
- QA policy is minimal (numbering/line-length/policy-tags/citations only); Posting/Analytics agents are stubs; error taxonomy and suggestedFix not emitted.
- SSE enforcement event exists but payload shape diverges from doc (lowercase decision statuses, warnings/audit_ok fields); frontend posting gate only checks `qa_summary.status` and `audit_ok` in enforced mode.
- No tests yet for enforcement contracts/pipeline/SSE/posting gate; runtime table creation occurs during audit writes.

## NEXT SLICES AFTER INFRA HARDENING (one-commit each)
1) **Frontend enforcement receipt wiring**
    - Scope: Capture enforcement SSE payload (request_id/receipt_id/mode/qa_summary) during generation; persist in UI state; pass `enforcement_request_id` to posting; render badge with status + copy button; surface suggestedFix on errors.
    - Files: `src/app/dashboard/page.tsx` (generation + posting UI/state), `src/app/api/post-to-x/route.ts` (client call site adjustments if needed), `src/components` (new badge/button if created).
    - Acceptance: Generated content stores latest enforcement receipt; posting automatically includes receipt when mode ≠ off; UI shows status chip (PASS/FAIL/ADVISORY) with copy; errors display suggestedFix.
    - Tests: Add/react tests for SSE parsing/state update and posting payload assembly (mock fetch). Do not run.
    - Docs: Note UI behavior in `.ai/API_REFERENCE.md` (client expectations) if payload fields used.

2) **Monitoring UX for enforcement**
    - Scope: Monitoring page shows latest enforcement status per workflow: request_id, mode, qa status, audit_ok, last error; add filters for FAIL vs PASS.
    - Files: `src/app/monitoring/page.tsx`, `backend/api/monitoring` (if new fields required), styling components.
    - Acceptance: Cards/table render enforcement fields; auto-refresh preserves data; non-admins still blocked per existing rule (if added later).
    - Tests: Frontend component test for rendering a sample enforcement trace; API contract test stub if backend fields added. Do not run.
    - Docs: Update `.ai/PROJECT_STATE.md` or `.ai/PHASE_10_1_ENFORCED_READINESS_CHECKLIST.md` with observability fields.

3) **QA policy v1 hardening**
    - Scope: Add deterministic checks for profanity, harmful/self-harm, platform TOS keywords, length-per-post; emit canonical violation codes + suggestedFix templates.
    - Files: `backend/features/enforcement/policy.py`, `backend/features/enforcement/service.py` (wire codes), tests under `backend/tests/agents/test_qa_policy_v1.py`.
    - Acceptance: QA returns violations and required_edits for each check; decisions use uppercase `PASS/FAIL`; suggestedFix provided per code.
    - Tests: Unit tests covering each violation path and clean path. Do not run.
    - Docs: `.ai/PHASE_10_1_QA_POLICY_V1.md` (new spec), `.ai/API_REFERENCE.md` (codes/examples).

4) **Contract tests + SSE snapshot**
    - Scope: Add backend contract tests to assert SSE `event: enforcement` contains required fields and uppercase statuses; snapshot example stored.
    - Files: `backend/tests/api/test_enforcement_sse.py`, fixtures; may touch `backend/main.py` for testability hooks.
    - Acceptance: Test fails if required fields missing or casing wrong; docs reflect schema.
    - Tests: New contract test file. Do not run.
    - Docs: Ensure `.ai/API_REFERENCE.md` matches emitted shape.

5) **Audit retention + cleanup job plan**
    - Scope: Document and stub a lightweight scheduled job (cron/worker) to prune `audit_agent_decisions` >30d and optionally export to cold storage; ownership assigned.
    - Files: `.ai/MIGRATIONS.md`, `.ai/PROJECT_STATE.md`, optional stub `backend/workers/cleanup.py` (no scheduling yet).
    - Acceptance: Retention policy written; stub job callable exists; no runtime DDL.
    - Tests: None (doc-only/stub). Do not run.
    - Docs: As above.

## NEXT 12 SLICES (one-commit each)
| ID | Goal | Files | Acceptance | Tests (add, don't run) | Risk |
|----|------|-------|------------|-------------------------|------|
| 10.1-N01 | Server-side enforcement receipt lookup (posting uses request_id) | backend/features/enforcement/service.py, backend/main.py, backend/features/enforcement/audit.py, docs refs | Posting rejects missing/invalid receipt; accepts valid PASS+audit_ok receipt; request_id persisted | Add unit for receipt fetch/validation; integration stub for posting gate | Medium |
| 10.1-N02 | Remove runtime `create_all_tables()`; add migration doc | backend/features/enforcement/audit.py, .ai/MIGRATIONS.md | Audit writes never invoke runtime DDL; migration DDL documented | Add unit to assert audit path does not call create_all_tables; doc test pointer | Low |
| 10.1-N03 | SSE/status normalization to `PASS`/`FAIL` | backend/main.py, backend/features/enforcement/service.py, docs | SSE/event decisions and qa_summary emit uppercase; schema docs align | Contract test for SSE payload casing; snapshot of enforcement event | Medium |
| 10.1-N04 | QA policy hardening (profanity/harmful/TOS/length-per-post) | backend/features/enforcement/policy.py | QA returns violations + required_edits for new checks; numbering kept | Unit tests for profanity/harmful/TOS/length | Medium |
| 10.1-N05 | Error taxonomy + suggestedFix emission | backend/features/enforcement/service.py, backend/main.py | Errors return `{code,message,suggestedFix,details}` with canonical codes | Unit tests for error mapping; SSE/posting error shape | Medium |
| 10.1-N06 | Posting gate uses server-side receipt + canonical errors | src/app/api/post-to-x/route.ts | Enforced mode rejects missing receipt (ENFORCEMENT_RECEIPT_REQUIRED); QA_BLOCKED uses required_edits/violations | Route unit/integration test with mocked receipt service | Medium |
| 10.1-N07 | Audit retention/cleanup job documented + owner | .ai/MIGRATIONS.md, .ai/PROJECT_STATE.md | Retention (30d hot, 90d archive) documented; owner named; job plan written | Doc test pointer only | Low |
| 10.1-N08 | SSE payload contract test + schema doc sync | backend/tests (new), .ai/API_REFERENCE.md | Contract test ensures required fields + casing; docs match implementation | Add contract test file | Low |
| 10.1-N09 | Posting rate-limit alignment (5/15min baseline) | src/app/api/post-to-x/route.ts | Rate limit matches plan (baseline 5/15m); friendly error | Unit test for limiter window | Low |
| 10.1-N10 | Observability wiring (metrics/log fields) | backend/features/enforcement/service.py, backend/main.py | Logs include request_id/mode/qa_status/audit_ok; metrics counters added | Unit test for logger fields (structured) | Medium |
| 10.1-N11 | Migration readiness + kill-switch verification | .ai/PHASE_10_1_ENFORCED_READINESS_CHECKLIST.md, .ai/PHASE_10_1_POST_IMPLEMENTATION_AUDIT.md | Checklist references receipt, migration, kill-switch; verified steps documented | Doc test pointer | Low |
| 10.1-N12 | Advisory burn-in report | .ai/PROJECT_STATE.md, .ai/PHASE_10_1_EXECUTION_BACKLOG.md | Report telemetry coverage, rejection rates, p90 latency after advisory window; ready-to-flip evidence | Doc update | Low |

### Tasks (IDs 10.1-T01 … 10.1-T28)

1. 10.1-T01 — Contracts: Enforcement Metadata model
   - Scope: Define canonical Pydantic model for enforcement metadata (status, workflowId, warnings[], policyVersion).
   - Files: `backend/models/enforcement.py`
   - Acceptance: Model includes fields: `status: "off"|"advisory"|"enforced"`, `workflow_id`, `warnings: string[]`, `policy_version`, `checks: string[]`.
   - Test plan: Add backend unit tests under `backend/tests/test_enforcement_models.py` covering serialization and required fields.
   - Rollout: none
   - Risk: Low
   - Owner: backend

2. 10.1-T02 — Contracts: Enforcement Failure shape
   - Scope: Define `EnforcementError` (code/message/suggestedFix/details) for generation/posting failures.
   - Files: `backend/models/enforcement.py`
   - Acceptance: Error codes enumerated: `QA_REJECTED`, `HARMFUL_CONTENT`, `CIRCUIT_BREAKER_TRIPPED`; includes `suggestedFix`.
   - Test plan: Unit tests validate schema and exhaustive enum mapping.
   - Rollout: none
   - Risk: Low
   - Owner: backend

3. 10.1-T03 — Audit: Agent workflow telemetry schema
   - Scope: Define append-only schema for agent runs (workflow_id, agent, start_ms, end_ms, success, failure_reason).
   - Files: `backend/features/analytics/event_store.py`, migration note in `.ai/MIGRATIONS.md`
   - Acceptance: Event store accepts `AgentRunRecorded` events; fields required per master plan.
   - Test plan: Reducer/unit tests under `backend/tests/analytics/test_agent_telemetry.py`.
   - Rollout: none
   - Risk: Medium
   - Owner: backend

4. 10.1-T04 — Audit: Persistence table DDL (document-only)
   - Scope: Draft SQL DDL for `agent_runs` (append-only); no code changes in this task.
   - Files: `.ai/MIGRATIONS.md`
   - Acceptance: DDL includes indexes on `(workflow_id, agent)` and `(created_at)`; documented retention policy reference.
   - Test plan: N/A (docs-only)
   - Rollout: none
   - Risk: Low
   - Owner: backend

5. 10.1-T05 — Enforcer: Feature flag configuration design
   - Scope: Specify env/config flags: `AGENT_ENFORCEMENT_ENABLED`, `AGENT_ENFORCEMENT_MODE`, `QA_BLOCKING_ENABLED`.
   - Files: `.ai/DECISIONS.md`, `.ai/PROJECT_STATE.md`
   - Acceptance: Flags documented with allowed values and defaults (OFF initially).
   - Test plan: N/A (docs-only)
   - Rollout: none
   - Risk: Low
   - Owner: devops

6. 10.1-T06 — Enforcer: Orchestrator responsibilities (document-only)
   - Scope: Define orchestration responsibilities and boundaries between Writer, QA, Posting in enforcement mode.
   - Files: `.ai/PHASE_10_MASTER_PLAN.md` (append subsection), `.ai/PHASE_10_1_EXECUTION_BACKLOG.md`
   - Acceptance: Responsibilities documented: only QA may block; circuit breaker rule; telemetry emission points.
   - Test plan: N/A (docs-only)
   - Rollout: none
   - Risk: Low
   - Owner: backend

7. 10.1-T07 — Endpoint Integration: Generation response metadata (advisory)
   - Scope: Add optional enforcement metadata fields to generation responses (docs + contract only in this task).
   - Files: `.ai/API_REFERENCE.md`
   - Acceptance: New subsection describes `enforcement` object and backward-compat guarantees.
   - Test plan: N/A (docs-only)
   - Rollout: advisory
   - Risk: Low
   - Owner: backend

8. 10.1-T08 — Endpoint Integration: Error shape documentation (advisory)
   - Scope: Document enforcement failure error shape and `suggestedFix`.
   - Files: `.ai/API_REFERENCE.md`
   - Acceptance: Error fields present; example provided; guarantees noted.
   - Test plan: N/A (docs-only)
   - Rollout: advisory
   - Risk: Low
   - Owner: backend

9. 10.1-T09 — Observability UX decision write-up
   - Scope: Lock UX approach (hybrid: user summary + admin full trace) and record consequences.
   - Files: `.ai/PHASE_10_DECISION_LOG.md`, `.ai/DECISIONS.md`
   - Acceptance: Decision recorded with metrics and measurables.
   - Test plan: N/A
   - Rollout: none
   - Risk: Medium
   - Owner: frontend

10. 10.1-T10 — Error taxonomy & suggestedFix catalog
    - Scope: Catalog common enforcement failures and actionable fixes (Twitter creds, profanity, length limits).
    - Files: `.ai/DECISIONS.md`, `.ai/API_REFERENCE.md`
    - Acceptance: At least 6 failure types documented with fixes aligned to master plan patterns.
    - Test plan: N/A
    - Rollout: advisory
    - Risk: Low
    - Owner: backend

11. 10.1-T11 — Telemetry retention policy lock-in
    - Scope: Decide retention (30 days) and document in decisions.
    - Files: `.ai/PHASE_10_DECISION_LOG.md`, `.ai/DECISIONS.md`
    - Acceptance: Decision noted with monitoring metrics and storage estimate.
    - Test plan: N/A
    - Rollout: none
    - Risk: Medium
    - Owner: devops

12. 10.1-T12 — Circuit breaker threshold lock-in
    - Scope: Decide threshold (3 consecutive failures) and document.
    - Files: `.ai/PHASE_10_DECISION_LOG.md`, `.ai/DECISIONS.md`
    - Acceptance: Decision recorded with measurement plan.
    - Test plan: N/A
    - Rollout: none
    - Risk: Medium
    - Owner: backend

13. 10.1-T13 — Latency SLA lock-in
    - Scope: Target p90 <2s end-to-end for enforced chain; record metrics plan.
    - Files: `.ai/PHASE_10_DECISION_LOG.md`, `.ai/DECISIONS.md`
    - Acceptance: Decision recorded with SLO/SLA definitions and dashboards to measure.
    - Test plan: N/A
    - Rollout: none
    - Risk: Medium
    - Owner: backend

14. 10.1-T14 — Flag policy & rollout constraints
    - Scope: Document safe rollout: OFF → advisory (≥72h) → enforced (guarded) with kill-switch.
    - Files: `.ai/DECISIONS.md`, `.ai/PROJECT_STATE.md`
    - Acceptance: Policy present; rollback steps explicit.
    - Test plan: N/A
    - Rollout: none
    - Risk: Low
    - Owner: devops

15. 10.1-T15 — Tests: Model & contract validation
    - Scope: Add tests covering enforcement models, error enums, serialization.
    - Files: `backend/tests/test_enforcement_models.py`
    - Acceptance: 100% pass; covers required fields and error mapping.
    - Test plan: Unit tests only.
    - Rollout: none
    - Risk: Low
    - Owner: backend

16. 10.1-T16 — Tests: Agent telemetry pipeline (unit)
    - Scope: Add reducer/unit tests for recording agent runs and computing durations.
    - Files: `backend/tests/analytics/test_agent_telemetry.py`
    - Acceptance: Deterministic results; handles success/failure states.
    - Test plan: Reducer tests, no DB.
    - Rollout: none
    - Risk: Medium
    - Owner: backend

17. 10.1-T17 — Tests: Circuit breaker behavior (unit)
    - Scope: Unit-test CB policy: after 3 consecutive optimizer failures, return writer draft.
    - Files: `backend/tests/agents/test_circuit_breaker.py`
    - Acceptance: Passes both happy-path and CB triggers.
    - Test plan: Unit tests with mocked optimizer.
    - Rollout: advisory
    - Risk: Medium
    - Owner: backend

18. 10.1-T18 — Tests: QA gatekeeper rules (unit)
    - Scope: Unit-test profanity list, TOS compliance, length limits, harmful redirection.
    - Files: `backend/tests/agents/test_qa_gatekeeper.py`
    - Acceptance: Deterministic approvals/rejections; sanitized content produced.
    - Test plan: Unit tests only.
    - Rollout: advisory
    - Risk: Medium
    - Owner: backend

19. 10.1-T19 — Endpoint integration tests (changed-only)
    - Scope: Add integration tests for generation route emitting advisory metadata; do not block content.
    - Files: `backend/tests/api/test_generate_enforcement.py`
    - Acceptance: Response contains optional `enforcement` object in advisory mode.
    - Test plan: Integration tests using FastAPI test client.
    - Rollout: advisory
    - Risk: Medium
    - Owner: backend

20. 10.1-T20 — Monitoring docs: Agent trace dashboard
    - Scope: Document `/monitoring` additions for agent traces (fields, filters) and measurement.
    - Files: `.ai/ARCHITECTURE.md`, `.ai/PROJECT_STATE.md`
    - Acceptance: Dashboard fields listed; latency metrics described.
    - Test plan: N/A (docs-only)
    - Rollout: none
    - Risk: Low
    - Owner: frontend

21. 10.1-T21 — API Reference: Enforcement Metadata subsection
    - Scope: Add enforcement metadata and error shape docs (backward compatibility guarantees).
    - Files: `.ai/API_REFERENCE.md`
    - Acceptance: Subsection present with example payloads and guarantees.
    - Test plan: N/A
    - Rollout: advisory
    - Risk: Low
    - Owner: backend

22. 10.1-T22 — Decision Log: Phase 10.1 P1 questions
    - Scope: Create decision log with options, recommended decisions, consequences, measurement.
    - Files: `.ai/PHASE_10_DECISION_LOG.md`
    - Acceptance: Q1–Q4 captured and resolved; ties to DECISIONS.md.
    - Test plan: N/A
    - Rollout: none
    - Risk: Low
    - Owner: TPM

23. 10.1-T23 — DECISIONS.md append-only section
    - Scope: Add Phase 10.1 decision bullets incl. flags policy, invariants (QA authority, audit required).
    - Files: `.ai/DECISIONS.md`
    - Acceptance: New section appended; no edits to prior content.
    - Test plan: N/A
    - Rollout: none
    - Risk: Low
    - Owner: TPM

24. 10.1-T24 — PROJECT_STATE.md preflight section
    - Scope: Add small section: "Phase 10.1 Execution Approved Pending" and preflight checklist referencing backlog/decision log.
    - Files: `.ai/PROJECT_STATE.md`
    - Acceptance: Section added without rewriting file; links present.
    - Test plan: N/A
    - Rollout: none
    - Risk: Low
    - Owner: TPM

25. 10.1-T25 — Rollout plan doc (OFF → advisory → enforced)
    - Scope: Write explicit rollout steps and guardrails; kill-switch and rollback path.
    - Files: `.ai/PHASE_10_1_EXECUTION_BACKLOG.md`, `.ai/DECISIONS.md`
    - Acceptance: Plan present; durations labeled "rough planning estimate"; no surprise-break prod.
    - Test plan: N/A
    - Rollout: none
    - Risk: Low
    - Owner: devops

26. 10.1-T26 — Error messages catalog (examples)
    - Scope: Provide example error payloads with `suggestedFix` for common enforcement failures.
    - Files: `.ai/API_REFERENCE.md`
    - Acceptance: At least 3 realistic examples included; aligns with existing X 403 pattern.
    - Test plan: N/A
    - Rollout: advisory
    - Risk: Low
    - Owner: backend

27. 10.1-T27 — Advisory mode acceptance test plan
    - Scope: Define acceptance plan for advisory: metadata visible, zero blocking, logs complete.
    - Files: `.ai/PHASE_10_1_EXECUTION_BACKLOG.md`
    - Acceptance: Checklist written with measurable thresholds (telemetry coverage ≥95%).
    - Test plan: N/A
    - Rollout: advisory
    - Risk: Low
    - Owner: TPM

28. 10.1-T28 — Enforced mode acceptance test plan
    - Scope: Define acceptance plan for enforced: QA blocks per rules; CB functions; user override logged.
    - Files: `.ai/PHASE_10_1_EXECUTION_BACKLOG.md`
    - Acceptance: Checklist written; targets: failure rate <2%, p90 <2s, override logging 100%.
    - Test plan: N/A
    - Rollout: enforced
    - Risk: Medium
    - Owner: TPM

## Definition of Done (Phase 10.1)

- Contracts: Enforcement metadata + error shapes finalized and referenced in API docs.
- Audit: Agent run telemetry schema documented; append-only persistence DDL drafted.
- Enforcement: Orchestrator boundaries locked; QA is sole blocker; circuit breaker threshold defined; flags documented.
- Endpoints: Generation responses documented with optional enforcement metadata; error shape documented with suggestedFix.
- Feature Flags: OFF by default; staged rollout plan and kill-switch documented.
- Tests: Plans for model, agent telemetry, circuit breaker, QA rules, endpoint metadata in place; owners assigned.
- Docs: `.ai/API_REFERENCE.md`, `.ai/DECISIONS.md`, `.ai/PROJECT_STATE.md` updated.
- Rollout: OFF → advisory → enforced plan ready; approval checklist prepared.

## Rollout Plan (OFF → advisory → enforced)

- OFF (default): Flags disabled; no user-visible changes; prepare telemetry and contracts.
- Advisory (rough planning estimate: 3–7 days):
  - Enable `AGENT_ENFORCEMENT_ENABLED=true`, `AGENT_ENFORCEMENT_MODE=advisory` in staging then production.
  - Generation responses include `enforcement` metadata; warnings logged; no blocking.
  - Measure telemetry coverage (target ≥95%), p90 latency baseline, failure taxonomies.
  - Kill-switch verified (can revert to OFF instantly).
- Enforced (after advisory success):
  - Enable `AGENT_ENFORCEMENT_MODE=enforced`, `QA_BLOCKING_ENABLED=true`.
  - QA may block per rules; circuit breaker returns degraded content; user override logs.
  - Targets: agent failure rate <2%, p90 <2s, telemetry coverage 100% of workflows.
  - Rollback path: set `AGENT_ENFORCEMENT_MODE=advisory` or disable entirely.

## Approval Checklists

Advisory Mode Entry:
- Decision log Q1–Q4 locked in `.ai/DECISIONS.md`.
- API docs updated with enforcement metadata and error shapes.
- Telemetry schema documented; retention set (30 days).
- Kill-switch documented and tested.

Enforced Mode Entry:
- Advisory telemetry coverage ≥95%.
- p90 latency <2s across enforced chain (measured).
- QA rules reviewed by security; override logging in place.
- Monitoring dashboard shows agent traces end-to-end.
