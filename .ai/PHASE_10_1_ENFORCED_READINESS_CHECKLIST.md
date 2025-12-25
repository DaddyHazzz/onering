# Phase 10.1 Enforced Readiness Checklist

Date: 2025-12-26  
Owner: Platform / Backend  
Scope: Preconditions and steps to flip `ONERING_ENFORCEMENT_MODE` to `enforced` safely.

## Preconditions
- `audit_agent_decisions` migration applied (no runtime DDL).
- Server-side enforcement receipt lookup deployed (request_id -> QA PASS + audit_ok=true) and reachable by posting service.
- SSE payload normalized to canonical schema (status casing `PASS`/`FAIL`).
- QA policy includes profanity/harmful/TOS/length + numbering checks; required edits returned.
- Feature flags set: `ONERING_AUDIT_LOG="1"`; `ONERING_TOKEN_ISSUANCE=shadow` (10.1).
- Monitoring endpoints live and `/monitoring` shows enforcement panel.
- Retention cleanup job configured and dry-run verified.

## Observability Requirements
- Logs: enforcement pipeline entry/exit with request_id, mode, QA status, would_block, audit_ok.
- Metrics: audit write success rate, SSE schema conformance, posting rejection reasons (`QA_BLOCKED`, `AUDIT_WRITE_FAILED`, `ENFORCEMENT_RECEIPT_REQUIRED`).
- Dashboards: p90 end-to-end latency for enforced chain; QA rejection rate; receipt lookup error rate.

## Safety Thresholds
- QA false positive rate <=2% in advisory sampling; false negative spot checks documented.
- SSE schema compliance >=99% (uppercase statuses, required fields present).
- Posting block reasons: <2% missing/invalid receipts after rollout; QA_BLOCKED reflects true violations.
- Audit write success >=99.5% in enforced.
- p90 enforcement latency <2s in enforced mode.

## Rollout Steps
1) **Off -> Advisory (min 72h):**
   - Set `ONERING_ENFORCEMENT_MODE=advisory`.
   - Verify SSE payload shape, telemetry coverage >=95%, audit writes success, QA rejection telemetry.
   - Validate receipt lookup end-to-end (posting accepts valid receipt, logs missing receipt).
2) **Advisory -> Enforced:**
   - Preconditions met + thresholds above.
   - Flip `ONERING_ENFORCEMENT_MODE=enforced`; keep `ONERING_AUDIT_LOG="1"`.
   - Monitor for 24h: rejection reasons, audit_ok failures, latency p90 <2s.

## Kill-Switch Procedure
- Trigger conditions: spike in `ENFORCEMENT_RECEIPT_REQUIRED` or `AUDIT_WRITE_FAILED`, p90 >2s, QA false positives >2%, posting outage.
- Action: set `ONERING_ENFORCEMENT_MODE=advisory` (soft) or `off` (hard) and restart relevant services; keep `ONERING_AUDIT_LOG` enabled for forensics.
- Notify: open incident per RUNBOOK_INCIDENT, page Platform lead.

## "If Something Goes Wrong" Flow
- Symptom: Posting blocked for many users -> check receipt lookup + audit_ok; if failing, flip to advisory and file incident.
- Symptom: SSE payload schema errors -> revert to advisory; fix emitter normalization; add contract test.
- Symptom: Audit DB errors -> keep advisory; disable writes only if DB impact; restore from backup; rerun migration.
- Symptom: QA over-blocking -> adjust policy list; keep enforced only after false positives <2%.
