# Interfaces — Events (Conceptual)

## Inputs
- eventId: string
- userId: string
- submissionRef?: string

## Outputs
- Participation: { status: 'verified' | 'pending' | 'rejected' }
- Reward: { ring: number }

## Notes
- Idempotent verification and reward issuance; retry-safe
