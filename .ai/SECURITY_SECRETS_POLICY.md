# Secrets Policy

## Scope
- Applies to all repositories, branches, and tags for OneRing.
- Secrets must never be committed to git history.
- All developers must follow this policy before every commit and push.

## Allowed Patterns in Repo
- Environment variable references: `STRIPE_WEBHOOK_SECRET=` (key only, no value)
- Short placeholders: `whsec_test`, `sk_test_4242...`, `localhost:5432/user:pass` (example templates)
- Documentation refs: examples in comments like "e.g., `sk_live_...`"
- `.env.example` with PLACEHOLDER values (never real secrets)

## Disallowed Patterns (Blocked by `python tools/secret_scan.py`)
The following patterns trigger automated rejection:
- Stripe Live: `sk_live_` + 20+ alphanumeric chars
- Stripe Test: `sk_test_` + 20+ alphanumeric chars
- Stripe Webhooks: `whsec_` + 20+ alphanumeric chars (CRITICAL: can replay events)
- Stripe Restricted: `rk_live_` + 20+ alphanumeric chars
- AWS Access: `AKIA` + 16 uppercase/digits
- AWS Secret: `aws_secret_access_key` in URLs or plaintext
- Private Keys: `-----BEGIN PRIVATE KEY-----`, `-----BEGIN RSA PRIVATE KEY-----`, `-----BEGIN OPENSSH PRIVATE KEY-----`
- Groq API: `gsk_` + 20+ alphanumeric chars
- GitHub PAT: `ghp_` + 32+ alphanumeric chars
- Slack: `xox[aAsB]` + 20+ alphanumeric chars
- Database Passwords: `postgresql://user:password@host`, `mysql://user:password@host`

## How Gates Enforce Secret Scanning

### Local Development (Before Commit)
```powershell
# Automatic (if pre-commit hooks enabled):
$env:ONERING_HOOKS=1 $env:ONERING_GATE=fast git commit -m "msg"

# Manual (always safe):
python tools/secret_scan.py --staged
```

### CI/Gate Enforcement (`pnpm gate`)
The `pnpm gate` command now enforces secret scanning at all levels:
```bash
pnpm gate --mode docs   # Scans all files, skips tests
pnpm gate --mode fast   # Scans changed files, runs fast tests
pnpm gate --mode full   # Scans all files, runs full test suite
```

**Gate behavior:**
- Runs `python tools/secret_scan.py` before any tests
- On secret found: Prints file, line, pattern, remediation steps → Exit code 1
- On no secrets: Proceeds to test phase based on mode
- If `ONERING_GATE=fast` set: Only changed files scanned (faster)
- If `ONERING_GATE=full` set: All files scanned (most thorough)

### Pre-Commit Hooks (Opt-In)
Enable with: `$env:ONERING_HOOKS=1 ONERING_GATE=fast`

Behavior when enabled:
1. Runs `python tools/secret_scan.py --staged` before commit
2. Scans ONLY staged files (fast, focused)
3. If secrets found: Rejects commit with remediation help
4. If clean: Proceeds based on `ONERING_GATE` level

To bypass (EMERGENCY ONLY): `$env:ONERING_SECRET_SCAN_BYPASS=1 git commit`
- Documents intent in commit hook logs
- Requires team notification (post to #security)

## Managing Secrets Safely

### Store Secrets
- Real secrets → `.env.local` (git-ignored)
- Deployment secrets → GitHub Secrets or secret manager
- `.env.example` → PLACEHOLDER values only (safe to commit)

### Pre-Commit Verification Checklist
- [ ] Run `python tools/secret_scan.py --staged` (exit code 0)
- [ ] Verify no `.env` or `.env.local` files staged: `git diff --cached --name-only | grep -E "\.env"`
- [ ] Review full diff: `git diff --cached` (manually scan for patterns)
- [ ] Check for secret-like strings in commit message
- [ ] Confirm `.gitignore` includes: `.env`, `.env.local`, `.env.test`

### Stripe Webhook Secrets (Special Case)
**Why critical:** Webhook secrets can be used to replay old events and forge signatures, compromising data integrity.

**Rotation procedure:**
1. **Immediately (< 5 min):**
   - Go to Stripe Dashboard → API Keys → Webhooks
   - Reveal and copy new webhook secret
   - Update `STRIPE_WEBHOOK_SECRET` in GitHub Secrets
   - Deploy changes

2. **Minutes (5-30 min):**
   - Verify deployments are live and accepting events
   - Update local `.env` files for developers
   - Notify #security Slack channel with rotation timestamp

3. **Hours (30 min - 4 hours):**
   - Monitor logs for any webhook signature failures
   - Review event delivery logs for anomalies
   - Confirm no replay attacks detected

4. **Next-day (24 hours):**
   - Revoke old secret in Stripe Dashboard
   - Audit logs for any old-secret usage
   - Post post-mortem if incident occurred

## Rotation Procedure (All Secrets)

### General (Non-Stripe)
1. Create new secret in provider
2. Update in GitHub Secrets + local `.env`
3. Deploy (verify live)
4. Revoke old secret
5. Audit logs

### Stripe Special
See "Stripe Webhook Secrets (Special Case)" above.

## If Secret Accidentally Committed

### Immediate (< 5 minutes)
1. **STOP** — do not push
2. **ALERT** — post `URGENT: Secret committed to main. Do not pull.` in #security
3. **Identify** — which secret? (Stripe, AWS, GitHub, etc.)
4. **Rotate** — immediately regenerate in provider

### Minutes (5-30 min)
5. Notify Codex for git history rewrite (tag current HEAD)
6. Remove secret from file + push fix to new branch
7. Verify all deployments have rotated secret
8. Post summary in #security with timeline

### Hours (30 min - 4 hours)
9. Codex rewrites history: `git filter-repo --invert-paths --path <secret_file>`
10. Force-push rewritten history
11. Notify all developers to re-clone
12. Verify secret scanner catches same pattern in future

### Next-day (24 hours)
13. Post-mortem: why did it get committed? (missing hook? bypass used?)
14. Implement process improvement (e.g., enable pre-commit hooks)
15. Document incident in `.ai/INCIDENT_*.md`

## Pre-Commit Hook Setup (Optional)

Enable for automatic secret scanning:
```powershell
# Windows
$env:ONERING_HOOKS=1
git config core.hooksPath .githooks
git commit -m "my changes"

# Commit will fail if secrets in staged files
# To bypass (rare): $env:ONERING_SECRET_SCAN_BYPASS=1 git commit
```

Enable for full gate on every commit:
```powershell
$env:ONERING_HOOKS=1 $env:ONERING_GATE=full git commit -m "msg"
# Runs secret scan + full test suite before commit
# Slower but most thorough
```

## Documentation
- [API_REFERENCE.md](.ai/API_REFERENCE.md) — Webhook signing (see "Security" section)
- [RUNBOOK_EXTERNAL_ENABLEMENT.md](.ai/RUNBOOK_EXTERNAL_PLATFORM.md) — Secret handling in production
- [tools/secret_scan.py](tools/secret_scan.py) — Implementation details
- [.githooks](.githooks/) — Pre-commit hook implementation
- [scripts/gate.ps1](scripts/gate.ps1) — Gate enforcement logic
