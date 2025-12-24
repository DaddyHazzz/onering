# Incident Response Runbook

## Triage Checklist
- Confirm blast radius: which routes/regions/users affected? Check `/healthz` and `/readyz`.
- Gather recent errors by `request_id` in logs; note HTTP status patterns (429/500/503).
- Verify feature flags: `RATE_LIMIT_ENABLED`, `WS_LIMITS_ENABLED`, `AUDIT_ENABLED`, `CONFIG_STRICT`.

## Common Failure Modes & Mitigations
- **Database down/slow**: `/readyz` returns 503. Mitigate by failing over DB, scaling, or reducing traffic. Disable audit if writes fail.
- **Clerk auth issues**: invalid/expired keys. In non-prod, set `CONFIG_STRICT=false` to keep service up while rotating keys.
- **WS overload or origin blocks**: look for `ws_limit` or origin-block logs; raise limits (`WS_MAX_*`) or widen `WS_ALLOWED_ORIGINS` temporarily.
- **Rate limit misconfig (429 spikes)**: increase `RATE_LIMIT_PER_MINUTE_DEFAULT` or `RATE_LIMIT_BURST_DEFAULT`, or disable `RATE_LIMIT_ENABLED` temporarily.
- **Stripe outages**: degrade gracefully; queue billing operations if possible; ensure webhook retries enabled.
- **Redis down**: posting queues fail; switch to sync mode if needed; monitor RQ worker logs.

## Stabilization Steps
1) Toggle limits off if blocking traffic (`RATE_LIMIT_ENABLED=false`, `WS_LIMITS_ENABLED=false`).
2) Restart pods/processes with updated env vars; monitor reconnects.
3) Run smoke test after mitigation to confirm basic flows work.

## Communication & Handoff
- Log all actions with timestamps and `request_id` references.
- Update status page / stakeholders with impact + ETA.
- File a postmortem with timeline, root cause, and preventive actions.
