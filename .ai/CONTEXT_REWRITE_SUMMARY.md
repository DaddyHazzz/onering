# `.ai/context.md` Rewrite Summary (Dec 21, 2025)

**Goal:** Align `.ai/context.md` 100% with `PROJECT_STATE.md` (canonical truth). Remove aspirational features not yet implemented.

---

## Key Changes Made

### Section 0: Canon & Guardrails (NEW)
- **Added explicit "This is canonical" statement**
- Clear checklist of what IS implemented (Phase 1-3.3c)
- Clear checklist of what IS PLANNED (Phase 3.4+)
- Explicit "Do Not Hallucinate" section calling out:
  - ❌ WebSocket presence (not implemented — polling only)
  - ❌ Multi-instance persistence (not implemented — in-memory)
  - ❌ Image rendering for share cards (not implemented — JSON only)
  - ❌ Stripe/payments integration (NOT IMPLEMENTED — listed aspirationally in DESIGN_DECISIONS, but PROJECT_STATE does not claim it)
  - ❌ Referral system, RING staking, family pools (NOT IMPLEMENTED — same caveat)

### Section 1: Product Identity
- **Reframed:** Removed mission statement about "viral content generation" and "RING token economics"
- **Focused:** Kept only ethos commitments that are actually implemented
- 6 core principles: momentum over vanity, determinism, no shame, authentic attribution, safety, anti-dark-patterns

### Section 2: Architecture Snapshot
- **Removed:** All aspirational Stripe, referral, staking, family pool, embeddings language
- **Clarified:** LangGraph is planned for Phase 4+, not used for core collaboration logic today
- **Emphasized:** In-memory stores with explicit `# STUB` markers
- **Removed:** Multi-platform posting references (X, IG, TikTok, YouTube) — Phase 4 feature, not Phase 3

### Section 4: Analytics & Leaderboards (REWRITTEN)
- **Changed paradigm:** From "ad-hoc counters" → Event-reducer model
- **Added:**
  - Event schema (planned, not yet created)
  - Event store interface (in-memory, Phase 3.5 will be PostgreSQL)
  - Reducers as pure deterministic functions
  - Read models vs raw events distinction
  - Anti-shame constraints (explicit list of forbidden language)
- **Rationale:** Phase 3.4 is designed to use event reducers, not ad-hoc analytics functions

### Section 6: LLM Usage Policy
- **Reconciled:** One crisp rule instead of scattered statements
- **Explicit:** "LLM can draft and suggest; scoring, awards, and eligibility are deterministic reducers only."
- **Enforcement:** All rewards must come from deterministic reducer logic, never directly from LLM

### Section 8: Roadmap
- **Updated:** Phase 3.4 explicitly calls out event schema design
- **Reordered:** Phase 3.5 emphasis on "Critical blocker for multi-instance deployment"
- **Removed:** All payment/staking/referral/publishing language (Phase 4 is publishing, not complete)

### Sections Removed Entirely
- "Exact Implemented Endpoints & Files" (was overclaimning)
- "Required Environment Variables" (scope creep — covered in DESIGN_DECISIONS)
- "How to Reproduce Flows" (scope creep — covered in README)
- "Error Fixes (Dec 13)" (outdated, not relevant)
- "Current Priorities / TODO" (covered in roadmap)

### Sections Added
- **Section 0:** Canon & Guardrails
- **Section 5:** Backend Extension Points (how to add features safely)
- **Section 9:** Glossary (key terms)
- **Section 10:** Architecture Patterns (copy these)
- **Known Technical Debt** (honest assessment)
- **Quick Reference:** File Locations

---

## What Was Removed (Alignment with PROJECT_STATE)

### NOT IN PROJECT_STATE — REMOVED
| Feature | Was Claimed | Actual Status |
|---------|------------|---------------|
| Stripe Checkout | ✅ (DESIGN_DECISIONS) | ❌ NOT IN PROJECT_STATE |
| RING staking/yield | ✅ (DESIGN_DECISIONS) | ❌ NOT IN PROJECT_STATE |
| Referral system | ✅ (DESIGN_DECISIONS) | ❌ NOT IN PROJECT_STATE |
| Family pools | ✅ (DESIGN_DECISIONS) | ❌ NOT IN PROJECT_STATE |
| Multi-platform posting | ✅ (DESIGN_DECISIONS) | ❌ Phase 4 only |
| User embeddings (pgvector) | ✅ (DESIGN_DECISIONS) | ❌ Phase 3.5+ only |
| Temporal.io workflows | ✅ (DESIGN_DECISIONS) | ⏳ Stubs only (Phase 4+) |
| Real Instagram API | ✅ (DESIGN_DECISIONS) | ⏳ Stub/mock only |
| Monitoring dashboard | ✅ (DESIGN_DECISIONS) | ❌ NOT IN PROJECT_STATE |

**Rationale:** DESIGN_DECISIONS is aspirational (future-focused). PROJECT_STATE is the ground truth of what IS working.

---

## What Was Kept / Emphasized

### IN PROJECT_STATE — FULLY DOCUMENTED
- ✅ Daily streaks + momentum (Phase 1)
- ✅ Profiles + archetypes (Phase 2)
- ✅ Collaborative drafts (Phase 3.1)
- ✅ Secure invites (Phase 3.2)
- ✅ Presence + attribution (Phase 3.3)
- ✅ Share cards v2 (Phase 3.3c)
- ⏳ Analytics + leaderboards (Phase 3.4, detailed design)

### DETERMINISM & SAFETY (CORE COMMITMENTS)
- Determinism-first: Optional `now` parameter for reproducible testing
- Safety-first: No token_hash, no secrets, frozen models
- No dark patterns: No shame language, no engagement chasing
- Idempotency everywhere: Prevent double-processing

---

## Tone & Perspective Shifts

| Old Tone | New Tone |
|----------|----------|
| "OneRing generates viral content" | "OneRing builds momentum through authentic collaboration" |
| Multi-feature laundry list | Honest "Implemented vs Planned" checklist |
| Aspirational architecture | Current architecture (with explicit STUB markers) |
| Ad-hoc analytics counter functions | Event-reducer model (deterministic, testable, event-sourced) |
| "All features working" | "Phase 1-3.3c complete, Phase 3.4+ in design" |

---

## Validation Checklist (What This Rewrite Enforces)

- ✅ Every major claim checked against PROJECT_STATE
- ✅ No Stripe/staking/referral language in implementation section
- ✅ Explicit "Planned vs Implemented" markers throughout
- ✅ Event-reducer model for Phase 3.4 analytics
- ✅ Crisp LLM usage policy (one rule, clearly stated)
- ✅ Anti-shame constraints explicitly listed
- ✅ In-memory stores marked as STUB for Phase 3.5
- ✅ No WebSocket claimed for presence (polling only)
- ✅ No real Instagram/LinkedIn integration claimed
- ✅ Extension points documented (where to add features safely)
- ✅ Testing contract summarized (per-route requirements)

---

## Usage Guidance for Future AI Agents

**This file is now the source of truth for all AI agents.** When working on OneRing:

1. **Read Section 0** — Understand what's implemented vs planned
2. **Avoid Section 2 aspirations** — Stick to in-memory stores, no fancy persistence until Phase 3.5
3. **Follow Section 3 determinism rules** — All time-dependent logic must accept `now` parameter
4. **Use Section 4 event-reducer model** — Phase 3.4 analytics must be pure functions over events
5. **Follow Section 5 extension points** — Know where to plug in new code
6. **Preserve Section 6 LLM policy** — Scoring is reducers only, never direct LLM output
7. **Check Section 8 roadmap** — Understand Phase 3.5+ blockers before making architectural changes

**If you disagree with this context, update PROJECT_STATE.md first, then update this file. Don't let them diverge.**

---

**Rewrite completed: December 21, 2025**  
**Files affected: `.ai/context.md` (533 lines, rewritten completely)**  
**Status: Ready for immediate use by AI agents and developers**
