# Open Questions & TODOs

**Last Updated:** December 25, 2025 @ 15:30 UTC  
**Source:** .ai/PHASE_10_MASTER_PLAN.md, .ai/PROJECT_STATE.md, .ai/ROADMAP.md, .ai/DECISIONS.md

**⚠️ Phase 10 Planning Complete:** See [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) for comprehensive execution plan.

This document tracks unresolved questions, pending decisions, and technical debt across all phases.

---

## Phase 10 Open Questions (Prioritized)

### P0 (Blocking Phase 10 Start)

**Status:** ✅ All P0 items resolved (Phase 10 can proceed)

- None currently

---

### P1 (High — Resolve During Phase 10 Execution)

#### Phase 10.1 — Agent-First Productization

**Q1: Agent Latency SLA**
- **Question:** Is p90 <2 seconds acceptable for end-to-end agent workflows, or target <1 second?
- **Context:** Current viral thread agent averages ~3-5s (research + writer + optimizer). Enforced agents may feel slow to power users.
- **Options:**
  - Option A: Target p90 <2s (requires optimization but achievable)
  - Option B: Target p90 <1s (may require caching, LLM model switching)
- **Decision Deadline:** Before 10.1 execution starts
- **Impact:** High (affects user perception, may require architecture changes if <1s)

**Q2: Circuit Breaker Thresholds**
- **Question:** Should circuit breaker trigger after 3 failures in a row, or 3 failures in 10 attempts?
- **Context:** If optimizer agent fails 3 times, return writer draft with warning. Too sensitive = users see degraded content often; too lenient = failures not caught.
- **Options:**
  - Option A: 3 in a row (sensitive, fast response)
  - Option B: 3 in 10 attempts (tolerates transient failures)
- **Decision Deadline:** Before 10.1 implementation (writer/optimizer integration)
- **Impact:** Medium (affects reliability vs false positives trade-off)

**Q3: Telemetry Retention Policy**
- **Question:** How long to retain agent workflow logs (workflow IDs, timing, failures)?
- **Context:** Full state logging creates storage bloat. Insufficient logging hinders debugging.
- **Options:**
  - Option A: 7 days (minimal storage, debugging recent issues only)
  - Option B: 30 days (moderate storage, can track trends)
  - Option C: 90 days (high storage, comprehensive historical analysis)
- **Decision Deadline:** Before 10.1 telemetry implementation
- **Impact:** High (storage cost vs observability trade-off)

**Q4: Agent Observability UX**
- **Question:** Should agent traces be user-facing (in dashboard) or admin-only (in monitoring page)?
- **Context:** Users may want to see why content was generated a certain way (transparency). But internal agent logic may confuse users.
- **Options:**
  - Option A: User-facing (transparency, trust-building)
  - Option B: Admin-only (avoid confusion, debug tool)
  - Option C: Hybrid (summary for users, full trace for admins)
- **Decision Deadline:** Before 10.1 UI implementation
- **Impact:** Medium (UX complexity vs transparency trade-off)

---

#### Phase 10.2 — Token Loop Activation

**Q5: RING Deduction Amounts**
- **Question:** Is -10 RING for failed post too harsh, too lenient, or appropriate?
- **Context:** Failed posts (QA rejected, platform API error) should disincentivize spam but not punish legitimate users.
- **Options:**
  - Option A: -10 RING (current plan, moderate penalty)
  - Option B: -5 RING (lighter penalty, encourages experimentation)
  - Option C: -20 RING (harsh penalty, strong anti-spam)
- **Decision Deadline:** Before 10.2 deduction logic implementation
- **Impact:** Medium (user behavior, gaming incentives)

**Q6: RING Decay Rate**
- **Question:** Is 1% monthly decay on >10K holdings appropriate, or adjust to 0.5% or 2%?
- **Context:** Decay encourages circulation, prevents hoarding. Too aggressive = users feel punished; too lenient = hoarding still happens.
- **Options:**
  - Option A: 1% monthly (current plan, moderate)
  - Option B: 0.5% monthly (gentler, less punishment feel)
  - Option C: 2% monthly (aggressive, strong circulation incentive)
- **Decision Deadline:** Before 10.2 decay cron job implementation
- **Impact:** High (user retention, RING circulation patterns)

**Q7: Sybil Clawback Policy**
- **Question:** Should RING clawbacks for detected sybil attacks be manual review only, or automated after X detections?
- **Context:** False positives harm innocent users. No clawback incentivizes "get away with it" behavior.
- **Options:**
  - Option A: Manual review only (Phase 10.2 scope, safe)
  - Option B: Automated after 3 detections (Phase 11, requires confidence in heuristics)
- **Decision Deadline:** Before 10.2 sybil detection implementation
- **Impact:** High (trust, false positive risk)

**Q8: Premium Agent Features for RING Spending**
- **Question:** What premium agent features should require RING spending?
- **Context:** RING utility expansion beyond staking. Risk of pay-to-win perception.
- **Options:**
  - Option A: Faster generation (priority queue, skip wait times)
  - Option B: Custom agent personalities (archetype variants)
  - Option C: Advanced analytics (cohort analysis, predictive alerts)
- **Decision Deadline:** Before 10.2 RING utility implementation
- **Impact:** Medium (monetization strategy, user fairness perception)

---

#### Phase 10.3 — Platform / External Surface Area

**Q9: API Rate Limit Thresholds**
- **Question:** Are 100 req/hour (free) and 1000 req/hour (paid) appropriate, or adjust based on infra cost?
- **Context:** Too lenient = abuse/DDoS risk; too strict = developer frustration.
- **Options:**
  - Option A: 100/1000 (current plan)
  - Option B: 50/500 (conservative, lower infra cost)
  - Option C: 200/2000 (generous, better developer experience)
- **Decision Deadline:** Before 10.3 rate limiting implementation
- **Impact:** High (infra cost vs developer adoption trade-off)

**Q10: Webhook Retry Window**
- **Question:** Should webhooks retry 3 times over 2 minutes (5s, 25s, 125s), or adjust to 5 retries over 10 minutes?
- **Context:** Unresponsive endpoints clog retry queues. Longer retry = better delivery but slower failure detection.
- **Options:**
  - Option A: 3 retries / 2 min (current plan, fast failure detection)
  - Option B: 5 retries / 10 min (better delivery, slower failure)
- **Decision Deadline:** Before 10.3 webhook implementation
- **Impact:** Medium (webhook reliability vs queue congestion)

**Q11: Plugin Approval Criteria**
- **Question:** What criteria determine plugin activation (security audit, code review, sandbox escape attempts)?
- **Context:** Manual review bottleneck slows adoption. Automated approval allows malicious plugins.
- **Options:**
  - Option A: Manual review + security audit (Phase 10.3 scope, safe)
  - Option B: Automated static analysis + sandbox tests (Phase 11, requires tooling)
- **Decision Deadline:** Before 10.3 plugin architecture implementation
- **Impact:** High (security vs adoption speed trade-off)

---

### P2 (Medium — Defer to Phase 11 if Not Critical Path)

**Q12: Should harmful content detection be configurable per user?**
- **Context:** Overly aggressive filtering frustrates users; opt-out allows harmful content through.
- **Options:** Global only (Phase 10), per-user settings (Phase 11)
- **Impact:** Medium (user experience vs safety)

**Q13: Should we expose write access to any core data via external APIs?**
- **Current Scope:** Read-only (profiles, leaderboard, published posts)
- **Risk:** Write access creates data corruption vectors
- **Decision:** If write access, what data and under what constraints? (Deferred to Phase 11)

**Q14: Should RING tipping be anonymous or public?**
- **Context:** Public tipping = status signaling (potentially toxic); anonymous = exploitation risk
- **Decision:** Transparency vs privacy trade-off (Deferred to Phase 11)

**Q15: Should we support webhook payload customization (e.g., templating)?**
- **Context:** Generic payloads may not fit all integrations; templating adds complexity
- **Decision:** Fixed schema (Phase 10) vs templating (Phase 11)

---

### P3 (Low — Track for Future Consideration, No Near-Term Action)

**Q16: Temporal.io activation timeline and prerequisites?**
- **Status:** Stubs in place, no active workflows
- **Decision:** Phase 11 or later

**Q17: Analytics storage migration (in-memory → PostgreSQL)?**
- **Status:** Phase 3.5 planned but postponed
- **Decision:** Phase 10.2 or Phase 11

**Q18: Rate-limiting tuning beyond 5 posts/15min?**
- **Status:** Dynamic limits based on user tier planned for Phase 10.2
- **Decision:** Sufficient or further tuning in Phase 11?

**Q19: Streaming UX improvements (token rendering, loading states)?**
- **Status:** Works but could be smoother
- **Decision:** Acceptable or requires polish in Phase 11?

**Q20: Where to add more integration tests vs unit tests?**
- **Status:** 1013 tests passing, coverage sufficient
- **Decision:** Expand coverage (Phase 11) or maintain current level?

---

## Technical Debt (Not Blocking Phase 10)

- **Insights query performance:** Slow at 100+ segments (cache results in Phase 11)
- **Video support:** Auto-generate in Phase 11 (Video Agent stub only in Phase 10)
- **WebSocket support:** Polling acceptable for MVP, revisit if latency issues arise (Phase 10.3 uses polling for external consumers)
- **Handoff Pack automation:** Manual sync required, automate in Phase 11
- **Real-time collaborative editing:** Yjs/CRDT deferred to Phase 11 (polling-based updates in Phase 10)
- **Machine learning recommendations:** Rule-based insights only in Phase 10, ML in Phase 11

---

## Decision-Making Framework

**Priority Levels:**
- **P0 (Blocking):** Must resolve before Phase 10 execution begins — ✅ All resolved
- **P1 (High):** Resolve during Phase 10 execution (sub-phase specific) — 11 items (Q1-Q11)
- **P2 (Medium):** Defer to Phase 11 if not critical path — 4 items (Q12-Q15)
- **P3 (Low):** Track for future consideration, no near-term action — 5 items (Q16-Q20)

**Current P1 Items (Must Resolve During Phase 10):**

**Phase 10.1 (Resolve Before Execution):**
- Q1: Agent latency SLA (p90 <2s or <1s?)
- Q2: Circuit breaker thresholds (3 in a row or 3 in 10?)
- Q3: Telemetry retention policy (7, 30, or 90 days?)
- Q4: Agent observability UX (user-facing, admin-only, or hybrid?)

**Phase 10.2 (Resolve Before Execution):**
- Q5: RING deduction amounts (-5, -10, or -20?)
- Q6: RING decay rate (0.5%, 1%, or 2% monthly?)
- Q7: Sybil clawback policy (manual only or automated?)
- Q8: Premium agent features for RING spending (faster gen, custom personalities, advanced analytics?)

**Phase 10.3 (Resolve Before Execution):**
- Q9: API rate limit thresholds (100/1000, 50/500, or 200/2000?)
- Q10: Webhook retry window (3/2min or 5/10min?)
- Q11: Plugin approval criteria (manual + audit or automated?)

**Process:**
1. Questions raised in this document
2. Discussion in planning sessions or PRs
3. Decisions recorded in `.ai/DECISIONS.md` (if architectural) or `.ai/PHASE_10_MASTER_PLAN.md` (if execution-specific)
4. Questions removed from this file once resolved

---

## Execution Pre-Flight Checklist

### Before Phase 10.1 Starts

- [ ] Resolve Q1: Agent latency SLA
- [ ] Resolve Q2: Circuit breaker thresholds
- [ ] Resolve Q3: Telemetry retention policy
- [ ] Resolve Q4: Agent observability UX
- [ ] Senior engineering review of [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) complete
- [ ] Security review of QA blocking logic complete
- [ ] All 1013 tests passing (618 backend + 395 frontend)

### Before Phase 10.2 Starts

- [ ] Resolve Q5: RING deduction amounts
- [ ] Resolve Q6: RING decay rate
- [ ] Resolve Q7: Sybil clawback policy
- [ ] Resolve Q8: Premium agent features for RING spending
- [ ] Phase 10.1 complete (agent enforcement live, telemetry operational)
- [ ] Agent failure rate <2% (measured over 7 days from 10.1)

### Before Phase 10.3 Starts

- [ ] Resolve Q9: API rate limit thresholds
- [ ] Resolve Q10: Webhook retry window
- [ ] Resolve Q11: Plugin approval criteria
- [ ] Phase 10.2 complete (token loop active, audit trail operational)
- [ ] Token economy stable (no major exploits, <1% gaming attempts)

---

## How to Use This Document

- **For contributors:** Review Phase 10 P1 questions before starting work on related tasks
- **For decision-makers:** Prioritize P1 items, schedule resolution sessions before each sub-phase
- **For reviewers:** Check if PRs address or introduce new open questions
- **For agents:** Reference this file when planning or making recommendations

---

## Next Review

- **Target:** Before Phase 10.1 execution begins (after senior engineering approves master plan)
- **Participants:** Technical lead, product owner, security reviewer, compliance
- **Goal:** Resolve all P1 questions for Phase 10.1, update `.ai/DECISIONS.md` with outcomes
- **Output:** Updated [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) with resolved questions, execution can begin

---

## References

- **Master Plan:** [PHASE_10_MASTER_PLAN.md](PHASE_10_MASTER_PLAN.md) — Comprehensive execution plan
- **Current Status:** [PROJECT_STATE.md](PROJECT_STATE.md) — Phase 9.6 complete, Phase 10 planning complete
- **Roadmap:** [ROADMAP.md](ROADMAP.md) — Phase 10 overview and timeline
- **Decisions:** [DECISIONS.md](DECISIONS.md) — Architectural choices preserved in Phase 10

---

## Technical Debt (Not Blocking Phase 10)

- **Insights query performance:** Slow at 100+ segments (cache results in Phase 11)
- **Video support:** Auto-generate in Phase 11 (not Phase 10)
- **WebSocket support:** Polling acceptable for MVP, revisit if latency issues arise
- **Handoff Pack automation:** Manual sync required, automate in Phase 11

---

## Decision-Making Framework

**Priority Levels:**
- **P0 (Blocking):** Must resolve before Phase 10 execution begins
- **P1 (High):** Resolve during Phase 10 execution (sub-phase specific)
- **P2 (Medium):** Defer to Phase 11 if not critical path
- **P3 (Low):** Track for future consideration, no near-term action

**Current P0 Items (Blocking Phase 10 Start):**
- None (Phase 10 can proceed with current questions tracked)

**Current P1 Items (Resolve During Phase 10):**
- Agent enforcement boundary criteria (Phase 10.1)
- RING gaming detection heuristics (Phase 10.2)
- API security layers beyond OAuth2 (Phase 10.3)

**Process:**
1. Questions raised in this document
2. Discussion in planning sessions or PRs
3. Decisions recorded in `.ai/DECISIONS.md` (if architectural)
4. Questions removed from this file once resolved

---

## How to Use This Document

- **For contributors:** Review Phase 10 questions before starting work on related tasks
- **For decision-makers:** Prioritize unresolved questions based on blocking status
- **For reviewers:** Check if PRs address or introduce new open questions
- **For agents:** Reference this file when planning or making recommendations

---

## Next Review

- **Target:** Before Phase 10.1 execution begins
- **Participants:** Technical lead, product owner, security reviewer
- **Goal:** Resolve all P0 and P1 questions, update `.ai/DECISIONS.md` with outcomes
