# Phase 10.1 — Decision Log (Locked Before Execution)

Last Updated: December 25, 2025
Scope: Agent-First Productization (Phase 10.1)
Source: [OPEN_QUESTIONS_AND_TODOS.md](OPEN_QUESTIONS_AND_TODOS.md#phase-101-agent-first-productization)

## Q1 — Agent Latency SLA

- Context: Enforced agent chain may slow UX; need realistic SLA.
- Options:
  - A) p90 <2s end-to-end (Research→Writer→QA→Posting preflight), achievable without model changes.
  - B) p90 <1s end-to-end, requires aggressive caching or model switch (risk of quality regressions).
- Recommendation: A) p90 <2s.
- Consequences (if wrong): If users consistently experience >2s, drop-off increases; need queue UI and progressive rendering.
- Measurement: Dashboard metrics for per-agent durations; SLO alerts if p90 >2s for 24h.
- DECISIONS.md entry: “Phase 10.1 SLA: p90 <2s; measured via agent telemetry; enforced mode requires meeting SLA in staging first.”

## Q2 — Circuit Breaker Thresholds

- Context: Optimizer failures should degrade gracefully.
- Options:
  - A) 3 consecutive failures → CB trip.
  - B) 3 failures in 10 attempts → CB trip (less sensitive).
- Recommendation: A) 3 consecutive failures.
- Consequences: If too sensitive, degraded content shown more; if too lenient, users stuck waiting; monitor CB rate.
- Measurement: CB trip rate per 100 workflows; alert if >5 trips/day.
- DECISIONS.md entry: “CB: 3 consecutive optimizer failures returns writer draft with warning; log trip with workflow_id.”

## Q3 — Telemetry Retention Policy

- Context: Storage vs observability trade-off.
- Options:
  - A) 7 days (minimal storage).
  - B) 30 days (moderate, trend-capable).
  - C) 90 days (heavy, historical analysis).
- Recommendation: B) 30 days.
- Consequences: Shorter retention weakens incident forensics; longer retention raises cost; re-evaluate quarterly.
- Measurement: Storage footprint and query latency; alert if telemetry store exceeds budget threshold.
- DECISIONS.md entry: “Agent telemetry retention: 30 days; monthly snapshotting allowed; append-only events.”

## Q4 — Agent Observability UX

- Context: Transparency vs complexity.
- Options:
  - A) User-facing full trace.
  - B) Admin-only full trace.
  - C) Hybrid: user summary + admin full trace.
- Recommendation: C) Hybrid.
- Consequences: Some users may misinterpret summaries; ensure copy clarity; admin trace gated.
- Measurement: UX feedback (support tickets), usage of monitoring; adjust copy as needed.
- DECISIONS.md entry: “Observability UX: Hybrid — dashboard shows summary (workflow_id, status); admin `/monitoring` shows full trace.”

## Feature Flag Policy & Rollout Constraints

- Flags: `AGENT_ENFORCEMENT_ENABLED`, `AGENT_ENFORCEMENT_MODE: off|advisory|enforced`, `QA_BLOCKING_ENABLED`.
- Policy:
  - Default OFF in production.
  - Advisory requires ≥72h stable telemetry, coverage ≥95%.
  - Enforced requires p90 <2s and security review of QA rules.
  - Kill-switch: instant revert to OFF; rollback path documented.
- Measurement: Telemetry coverage, p90 latency, failure rate; daily review in `/monitoring`.
- DECISIONS.md entry: “Flags default OFF; staged rollout OFF→advisory→enforced; kill-switch mandatory.”

## Invariants (Reaffirmed)


## New P1 Decisions (Lock Before Enforced Mode)

### D1 — Server-Side Enforcement Receipt Required for Posting
- Context: Posting currently relies on client-forwarded enforcement payload; Codex is adding server-side receipt lookup.
- Options:
  - A) Require server-side receipt (request_id or receipt_id) and reject if absent.
  - B) Accept client-forwarded payload as today (higher spoof risk).
- Recommendation: A) Require server-side receipt keyed by `request_id`, with QA PASS + `audit_ok=true` enforced; reject missing/invalid receipts.
- Consequences: Blocks spoofed payloads; requires persistence/lookup; mild latency hit.
- Measurement: Posting rejection rate due to missing/invalid receipts; target <2% once shipped.
- Owner: Backend/Platform. Status: LOCKED.

### D2 — Status Casing Standard
- Context: SSE decisions currently lowercase; clients/docs ambiguous.
- Options: A) Uppercase `PASS`/`FAIL` everywhere. B) Lowercase `pass`/`fail` everywhere.
- Recommendation: A) Uppercase for consistency with QA policy and future enums; normalize at emit time.
- Consequences: Requires one-time normalization in backend emitters and doc alignment; clients rely on uppercase.
- Measurement: SSE schema conformance (>=99% events uppercase); contract tests added.
- Owner: Backend. Status: LOCKED.

### D3 — Audit Persistence Strategy
- Context: `create_all_tables()` runs on request path; risk of lock/permission errors.
- Options: A) Pre-migrate table via Alembic/DDL; never create at runtime. B) Keep runtime creation best-effort.
- Recommendation: A) Pre-migrate; fail-open in advisory, fail-closed in enforced only if QA PASS but audit write fails AND no receipt.
- Consequences: Requires migration pipeline; removes runtime DDL risk; clearer SLOs.
- Measurement: Audit write success rate; alert if <99.5% in enforced.
- Owner: DevOps/Backend. Status: LOCKED.

### D4 — Telemetry/Audit Retention & Cleanup
- Context: No retention policy documented for `audit_agent_decisions`.
- Options: A) 30 days hot, 90 days cold archive; B) 30 days only; C) 90 days hot.
- Recommendation: A) 30d hot in primary DB, optional 90d cold export; weekly cleanup job ownership assigned to Platform.
- Consequences: Controls storage growth; retains incident forensics window.
- Measurement: Table size trend; cleanup job success; alert if >30d data remains in primary.
- Owner: DevOps/Platform. Status: LOCKED.

## What to Add to DECISIONS.md

- Phase 10.1 SLA target (p90 <2s) and measurement approach.
- Circuit breaker threshold (3 consecutive failures) and logging.
- Telemetry retention policy (30 days) with append-only events.
- Observability UX approach (Hybrid summary + admin full trace).
- Feature flag defaults and staged rollout constraints + kill-switch.
- Invariants: QA authority and audit requirements.
