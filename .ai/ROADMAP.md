
Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# OneRing Roadmap — Feature Tiers

## Tier 1 — Daily Pull (Addiction)
### Creator Streaks
- Behavior: Tracks consecutive days of meaningful creative actions; offers streak protection windows and partial resets.
- Pull: Daily commitment builds identity; breaking a streak matters emotionally.
- Systems: Streak service, posting endpoints, analytics events, RING awards.

### AI Post Coach
- Behavior: Context-aware guidance on clarity, tone, and audience fit; provides small nudges, not rewrites.
- Pull: Immediate, supportive feedback increases confidence and reduces friction.
- Systems: Generation context, archetypes, momentum scoring, values mode.

### Daily Challenges
- Behavior: Lightweight tasks tailored to creator goals (e.g., "Ship one insight in 4 lines").
- Pull: Specific, achievable prompts make showing up easy; completion fuels momentum.
- Systems: Temporal workflows for scheduling/chaining, RQ for reminders, analytics for completion.

## Tier 2 — Identity & Status
### Public Creator Profiles
- Behavior: Shareable pages showing momentum graphs, streaks, and recent content aligned to archetype.
- Pull: Status signaling and identity reflection attract peers and audience.
- Systems: Analytics aggregation, embeddings, RING stats, posting history.

### Creator Archetypes
- Behavior: Personality frameworks that shape prompts and feedback; user selects or evolves archetype.
- Pull: Identity scaffolding increases meaning and self-recognition.
- Systems: Archetype domain, AI coach tone, values mode constraints.

### Momentum Score
- Behavior: Composite score from streaks, challenge completion, content resonance, and lineage.
- Pull: Simple metric representing progress over time encourages ongoing effort.
- Systems: Analytics reducers, scoring service, RING bonuses.

## Tier 3 — Network Effects & Rewards
### Collaborative Threads
- Behavior: Co-authored threads with attribution and shared momentum gains.
- Pull: Social creation increases accountability and reach.
- Systems: Collaboration domain, posting router, lineage tracking.

### Content Lineage
- Behavior: Track how ideas evolve across posts, threads, and collaborators.
- Pull: Seeing the story of ideas deepens attachment and pride.
- Systems: Lineage domain, embeddings, analytics events.

### Ring Drops (Events)
- Behavior: Time-bound events that award RING for participation and completion.
- Pull: Scarcity and communal participation drive action.
- Systems: Events domain, Temporal workflows, RQ jobs, payments.

## Tier 4 — Press-Worthy Experiments
### Audience Simulator
- Behavior: Simulate target audience reactions to draft content using archetype-conditioned models.
- Pull: Safe practice grounds reduce fear and sharpen messaging.
- Systems: Generation + archetypes, analytics capture, coach feedback.

### Post Autopsy AI
- Behavior: Explain why a post worked or didn’t—structure, clarity, resonance—then suggest next steps.
- Pull: Narrative feedback turns outcomes into learning, fueling momentum.
- Systems: Analytics signals, embeddings, AI coach, lineage.

### Values Mode
- Behavior: Constrain prompts and output to user-defined values; filters tone and topics to align with identity.
- Pull: Integrity and alignment increase trust and consistency.
- Systems: Archetypes, AI behavior constraints, generation guardrails.
---

# Phase 10 — Platform Maturation (Planned)

**⚠️ EXECUTION PLANNING COMPLETE — See [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) for comprehensive details**

**One-Sentence Objective:** Make OneRing defensible by enforcing agent workflows, activating minimal token economics with audit trails, and exposing controlled external APIs—without blockchain, speculation, or architectural drift.

**Status:** Planning complete, awaiting execution approval  
**Duration:** 9-12 weeks (Q1 2026 estimate)  
**Prerequisites:** Phase 9.6 complete, all 1013 tests passing, all P0 questions resolved

## Phase 10.3 — External Platform Surface Area (COMPLETE)

**Status:** ✅ COMPLETE (December 25, 2025)  
**Commit:** `feat(phase10.3): add external read-only API and webhooks with signing`

**Deliverables:**
- ✅ External read-only API with 6 endpoints
- ✅ API key system with bcrypt hashing and scope enforcement
- ✅ Tiered rate limiting (free: 100/hr, pro: 1000/hr, enterprise: 10000/hr)
- ✅ Webhook delivery system with HMAC-SHA256 signing
- ✅ Retry policy with 3 attempts and exponential backoff
- ✅ Kill switches (both default disabled)
- ✅ Comprehensive test suite (27 tests, all passing)
- ✅ Documentation updates (API_REFERENCE, PROJECT_STATE, ROADMAP)

**Rollout Gates:**
1. Security review of API key hashing and signature verification
2. Production enablement checklist:
	- Set `ONERING_EXTERNAL_API_ENABLED=1` when ready for public API
	- Set `ONERING_WEBHOOKS_ENABLED=1` when ready for webhook emission
	- Monitor rate limit violations (429 responses)
	- Monitor webhook delivery failures
	- Set up blocklist entries for abusive keys/IPs
3. Scope expansion (future):
	- Write scopes (`write:drafts`, `write:posts`)
	- Admin scopes (`admin:users`, `admin:billing`)
	- Fine-grained permissions (per-resource access control)

**Strategic Intent:** Transform OneRing from an internal tool into a defensible, agent-first platform with minimal token loop activation and controlled external extensibility.

**Guiding Principles:**
- Agent workflows are mandatory, not optional
- $RING token loop must be minimal, enforceable, and audit-friendly
- External APIs must preserve architectural decisions and safety contracts
- Incremental rollout with clear acceptance gates between sub-phases

---

## Phase 10.1 — Agent-First Productization (3-4 weeks)

**Objective:** Make AI agents the default path for all content creation workflows, eliminating manual fallback modes.

**Core Changes:**
- **Agent Enforcement:** All content generation must flow through LangGraph agents (no direct Groq API calls from frontend)
- **Mandatory Chain:** Writer → QA (gatekeeper) → Posting → Analytics
- **Telemetry:** All steps logged with workflow IDs, durations, outcomes
- **Observability Dashboard:** Real-time agent execution traces in `/monitoring` page
- **Circuit Breakers:** Agent failures return degraded content (no permanent blocks)

**Key Agents Implemented:**
- Research Agent (trend retrieval, pgvector similarity)
- Strategy Agent (content strategy, archetype integration)
- Writer Agent (multi-platform content generation, harmful content redirection)
- QA Agent (brand safety, compliance, profanity filtering) — **ONLY BLOCKING AGENT**
- Posting Agent (platform routing, RING calculation)
- Analytics Agent (event logging, leaderboard updates)
- Visual/Video Agents (stubs only, Phase 11 for real implementation)

**Explicit Non-Goals:**
- Multi-LLM support (Groq remains sole provider)
- Agent marketplace or custom agent authoring
- Autonomous posting without user confirmation

**Success Criteria:**
- Zero direct LLM calls from frontend (all route through backend agents)
- Agent telemetry covers 100% of content workflows
- Agent failure rate < 2% (measured over 7 days)
- Agent dashboard shows real-time execution traces

**See:** [PHASE_10_MASTER_PLAN.md Part B](PHASE_10_MASTER_PLAN.md#part-b-agent-enforcement-deep-dive-phase-101) for agent-by-agent upgrade plan

---

## Phase 10.2 — Token Loop Activation (2-3 weeks)

**Objective:** Activate the $RING token economy with minimal complexity, clear enforcement, and zero decentralization promises.

**Core Changes:**
- **RING Deductions:** Failed posts (-10), abandoned drafts (-5/day after 7 days), QA overrides 3x (-50)
- **RING Decay:** 1% monthly on holdings >10K (encourages circulation)
- **Lifetime Cap:** 1,000,000 RING per user (prevents unchecked accumulation)
- **Audit Trail:** Append-only PostgreSQL table logs all RING transactions immutably
- **Anti-Gaming:** Sybil detection heuristics, dynamic rate limits (5/10/15 posts per 15min)

**Agent Integration:**
- RING awards only after QA approval (no bypass)
- Posting Agent calculates RING deterministically: `views/100 + likes*5 + retweets*10 + 50*(is_verified)`
- Analytics Agent logs all transactions in audit trail

**Token Safety Contracts:**
- $RING is **not** a cryptocurrency (no blockchain, no trading, no withdrawal to fiat)
- $RING is a gamification mechanic with no real-world value
- Users acknowledge RING is platform-internal only (TOS update required)

**Explicit Non-Goals:**
- Blockchain integration or decentralization
- RING to USD conversion or external exchanges
- Token burning mechanisms (except decay)
- Third-party RING-based applications

**Success Criteria:**
- All RING transactions logged with sub-second latency
- Zero unaccounted RING in circulation (audit queries pass)
- < 1% of users attempt gaming behaviors
- RING staking adoption rate > 20% of active users within 30 days

**See:** [PHASE_10_MASTER_PLAN.md Part C](PHASE_10_MASTER_PLAN.md#part-c-token-loop-activation-design-phase-102) for detailed token economics

---

## Phase 10.3 — Platform / External Surface Area (4-5 weeks)

**Objective:** Expose controlled, versioned APIs for external integrations while preserving architectural decisions and safety guarantees.

**Core Changes:**
- **Public API:** REST API under `/api/v1/external/*` (read-only, OAuth2 authenticated)
- **Webhooks:** Outbound events (draft.published, ring.passed, ring.earned) with HMAC-SHA256 signing
- **Rate Limiting:** 100 req/hour free tier, 1000 req/hour verified users
- **Plugin Architecture:** Sandboxed FastAPI workers, manual approval queue
- **Kill-Switch:** Admin can suspend API keys, block IPs, disable all external traffic

**Posting Agent as ONLY Publish Path:**
- All external integrations trigger OneRing's Posting Agent (no direct platform API access)
- Ensures QA Agent always runs (brand safety, compliance)
- Centralizes RING award calculation (deterministic formula)

**Explicit Non-Goals:**
- GraphQL API (REST only)
- Real-time streaming APIs (WebSockets) for external consumers
- White-label / rebrand support
- Self-hosted OneRing instances
- Plugin marketplace or revenue sharing

**Success Criteria:**
- External API endpoints documented and versioned
- At least 3 external integrations built (Zapier, n8n, custom app)
- Zero security incidents from external API access within 90 days
- Webhook delivery success rate > 95%

**See:** [PHASE_10_MASTER_PLAN.md Part D](PHASE_10_MASTER_PLAN.md#part-d-external-platform-surface-area-phase-103) for platform exposure strategy

---

## Phase 10 Summary & Invariants

**System Invariants After Phase 10:**
1. All content flows through agents (no frontend → Groq direct calls)
2. QA Agent is the only blocker (all other agents are informational or execution)
3. RING transactions are immutable (append-only audit trail)
4. Workflow IDs are unique and traceable (every agent execution logged)
5. Rate limits are deterministic (Redis TTL enforces 5/10/15 posts per 15min)
6. External APIs are read-only (no write access to drafts, segments, ring state)
7. Posting Agent calculates RING (deterministic formula)
8. Webhooks are at-least-once (may retry up to 3 times)
9. Lifetime RING cap is 1,000,000 (no exceptions)
10. Clerk is source of truth for user state (RING balance, verified status, metadata)

**Hard Guarantees:**
- Harmful content is redirected (Writer Agent detects self-harm keywords)
- Agent failures do not block permanently (circuit breakers return degraded content)
- RING balance audit trail always matches Clerk (within ±10 RING tolerance)
- Platform API tokens never exposed to frontend or external APIs
- Webhook signatures prevent spoofing (HMAC-SHA256 verification)

**Explicit Non-Goals:**
- Multi-LLM support, agent marketplace, no-code agent builder
- Blockchain integration, RING to USD conversion, DeFi features
- GraphQL API, WebSockets for external consumers, white-label support
- Mobile native apps, multi-language support, real-time collaborative editing (Yjs/CRDT)

**See:** [PHASE_10_MASTER_PLAN.md Part E](PHASE_10_MASTER_PLAN.md#part-e-invariants-guarantees-and-non-goals) for complete lists

---

## Phase 10 Timeline & Dependencies

| Sub-Phase | Duration | Key Deliverables | Gating Criteria |
|-----------|----------|------------------|-----------------|
| **10.1** | 3-4 weeks | Agent enforcement, telemetry, QA gatekeeper, observability dashboard | Agent failure rate <2%, zero frontend LLM calls |
| **10.2** | 2-3 weeks | RING deductions, decay, lifetime cap, audit trail, sybil detection | Audit trail reconciliation passes, <1% gaming attempts |
| **10.3** | 4-5 weeks | External API, webhooks, plugin sandbox, kill-switch, 3 integrations | Webhook delivery >95%, zero security incidents (90 days) |

**Total Duration:** 9-12 weeks (Q1 2026)

**Critical Path:**
```
Phase 9.6 (complete) → 10.1 (agents) → 10.2 (tokens) → 10.3 (APIs)
```

**Dependencies:**
- Phase 9.6 complete (hooks, safety contracts, governance)
- All 1013 tests passing (GREEN ALWAYS policy maintained)
- Documentation in `.ai/` fully updated
- All P0 open questions resolved before 10.1 starts

**Post-Phase 10 Outcomes:**
- OneRing operates as agent-mandatory system
- $RING token loop active with clear rules and enforcement
- External developers can integrate via public APIs
- Platform extensibility model defined (plugins, webhooks)
- Architectural decisions preserved (Clerk, FastAPI, PostgreSQL, LangGraph, Groq)

**See:** [PHASE_10_MASTER_PLAN.md Part F](PHASE_10_MASTER_PLAN.md#part-f-sub-phase-breakdown--acceptance-criteria) for detailed entry/exit criteria and rollback plans

---

## How to Execute Phase 10

1. **Review Master Plan:** Read [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) in full
2. **Resolve Open Questions:** See [OPEN_QUESTIONS_AND_TODOS.md](OPEN_QUESTIONS_AND_TODOS.md) for P0/P1 items
3. **Get Approvals:** Technical lead, product owner, security, compliance must approve
4. **Break Down 10.1:** Split into one-commit tasks (see master plan agent-by-agent section)
5. **Execute Sub-Phases:** 10.1 → 10.2 → 10.3 with clear gates between each
6. **Update Documentation:** Maintain `.ai/PROJECT_STATE.md` as each sub-phase completes

**Next Steps:** Senior engineering review of master plan, then Phase 10.1 execution begins.
