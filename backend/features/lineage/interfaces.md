# Interfaces — Lineage (Conceptual)

## Inputs
- contentRef: string
- linkReason: 'refactor' | 'expand' | 'respond' | 'fork' | 'merge'

## Outputs
- LineageNode: { id, contentRef }
- LineageEdge: { from, to, reason }

## Notes
- Stable IDs and deterministic edge creation; idempotent writes
