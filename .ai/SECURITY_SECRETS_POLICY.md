# Secrets Policy

## Scope
- Applies to all repositories, branches, and tags for OneRing.
- Secrets must never be committed to git history.

## Allowed patterns in repo
- Environment variable references only (e.g., `STRIPE_WEBHOOK_SECRET=`).
- Explicit placeholders: `whsec_REDACTED`, `whsec_test`, `sk_test_...` (short placeholders only).

## Disallowed patterns (blocked)
- `whsec_` followed by 16+ alphanumeric characters
- `sk_live_` and `rk_live_` followed by 16+ alphanumeric characters
- `sk_test_` followed by 16+ alphanumeric characters
- `AKIA` followed by 16 uppercase letters/digits
- `-----BEGIN PRIVATE KEY-----`

## Handling secrets
- Store real secrets in `.env.local` or secret managers.
- `.env*` files remain ignored (except `.env.example`).
- Never paste secrets into docs, test fixtures, or commit messages.

## Rotation
- Rotate in the provider (Stripe, AWS, etc.) first.
- Update deployments and CI secrets.
- Revoke old secrets immediately after rollout.

## Incident response
- Tag current HEAD before history rewrite.
- Use `git filter-repo` to purge secrets from history.
- Force-push rewritten history and notify collaborators.
