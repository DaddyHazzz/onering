# Domain — Content Lineage

## Concept Definition
Trace idea evolution across posts, drafts, and collaborations; visualize how concepts compound.

## Core Entities
- LineageNode: id, contentRef, createdAt, authorId
- LineageEdge: fromNodeId, toNodeId, reason (refactor, expand, respond)

## Example State Transitions
- new node -> linked expansion -> fork -> merge
- attribution maintained through edges

## Metrics Involved
- Depth and breadth of lineage
- Time between linked nodes

## Backend Systems
- Embeddings associate related content
- Analytics emits lineage events
- Posting stores references for edges
