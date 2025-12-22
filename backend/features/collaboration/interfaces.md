# Interfaces — Collaboration (Conceptual)

## Inputs
- participants: userId[]
- contentDraftRefs: string[]

## Outputs
- CollaborativeThread: { id, externalIds[], contributors[] }
- Attribution: { userId, contributionPercent }

## Notes
- Deterministic ordering; explicit consent; idempotent posting
