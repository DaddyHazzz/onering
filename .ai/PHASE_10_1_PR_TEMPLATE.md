# Phase 10.1 PR Template

## Summary
- What changed and why (one paragraph)
- Which slice/backlog item does this PR close (e.g., 10.1-N0X)?

## Feature Flags
- `ONERING_ENFORCEMENT_MODE`: off | advisory | enforced (state in staging/prod after deploy)
- `ONERING_AUDIT_LOG`: "1" | "0"
- `ONERING_TOKEN_ISSUANCE`: off | shadow | live
- Other flags touched:

## Testing
- Commands run (paste output):
  - [] pnpm test (or targeted)
  - [] pnpm lint
  - [] pnpm gate --mode docs/fast/full (if applicable)
- Screenshots (required for UI changes):
  - Generation UI with enforcement badge
  - Posting error state showing suggestedFix (if relevant)
  - Monitoring page (if touched)

## Backward Compatibility
- [ ] off mode unchanged (no payload requirement)
- [ ] advisory mode non-blocking
- [ ] enforced mode validated receipts and canonical errors

## Rollout & Kill-Switch
- Rollout plan: off → advisory → enforced? (notes)
- Kill-switch reference: `ONERING_ENFORCEMENT_MODE=off|advisory` (per readiness checklist)
- Any data migrations? link to DDL/migration PR

## Checklist
- [ ] Docs updated (API_REFERENCE / backlog / readiness checklist if needed)
- [ ] Added/updated tests (listed above)
- [ ] No runtime DDL on request path
- [ ] Receipt lookup paths validated (if applicable)
- [ ] SSE payload matches canonical schema (PASS/FAIL, required fields)
