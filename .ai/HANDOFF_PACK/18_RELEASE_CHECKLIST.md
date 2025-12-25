Source: .ai/PROJECT_STATE.md, .ai/ROADMAP.md

# Release Checklist (Practical)

- Version bump and changelog updated
- All gates GREEN (fast + full)
- Stripe webhook verified (if payments affected)
- Redis + RQ workers healthy
- Database migrations applied (prisma + backend)
- Environment variables audited (frontend + backend)
- Monitoring dashboard shows stable KPIs
- Post-to-X credentials validated via `client.v2.me()`
- Error responses provide suggestedFix where applicable
- Docs updated (.ai/* and relevant stubs)
