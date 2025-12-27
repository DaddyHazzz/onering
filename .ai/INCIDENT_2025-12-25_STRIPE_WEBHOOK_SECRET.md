# Incident: Stripe Webhook Secret Leak (2025-12-25)

## Summary
- **Type:** Secret leak (Stripe webhook signing secret)
- **Detected by:** GitGuardian
- **First seen:** 2025-12-25 22:57:18 UTC
- **Status:** Remediated

## Timeline
- 2025-12-25 22:57:18 UTC: GitGuardian alert created.
- 2025-12-27: Rotation initiated and history rewrite completed.

## Root Cause
- A real webhook secret was committed in documentation as an example value.

## Impact
- Potential exposure of Stripe webhook signing secret.
- No confirmed misuse at time of remediation.

## Actions Taken
1. Rotated Stripe webhook secret (new secret generated, old invalidated).
2. Removed leaked value from HEAD.
3. Rewrote git history to purge leaked value.
4. Added secret scanning guardrails (pre-commit + CI gate).
5. Added secrets policy documentation.

## Verification
- Local history scan for `whsec_` patterns returns no leaked values.
- `git log -S` for the leaked value returns no results after rewrite.
- GitHub secret scanning/GitGuardian shows the finding resolved (may take time to refresh).

## Follow-ups
- Ensure all environments are updated to the rotated secret.
- Reinforce “no secrets in git” training and reviews.
