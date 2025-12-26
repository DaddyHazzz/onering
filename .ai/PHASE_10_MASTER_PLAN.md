# Phase 10 Master Plan

**Status:** Planning complete, awaiting execution approval  
**Created:** December 25, 2025  
**Owners:** Principal Engineer + Technical Program Manager  
**Review Required:** Senior engineering team, security, compliance

---

## Phase 10 Objective

**Make OneRing defensible by enforcing agent workflows, activating minimal token economics with audit trails, and exposing controlled external APIs—without blockchain, speculation, or architectural drift.**

---

## Phase 10 Philosophy

### Why Agents Must Become Enforceable

Currently, agents are optional suggestions that users can bypass. This creates:
- **Quality variance:** Direct LLM calls lack safety filters (harmful content detection, brand safety, rate limiting)
- **Observability gaps:** Bypassed agents leave no telemetry (no workflow IDs, no timing, no failure modes)
- **Security exposure:** Frontend can call Groq API directly, bypassing backend enforcement

Phase 10.1 makes agents **mandatory gates** for all outbound content. Users interact with agent outputs, never raw LLM responses. This enables:
- **Deterministic safety:** All content flows through QA agent (brand checks, harmful content filters)
- **Audit trails:** Every generation has workflow ID, agent chain trace, timing metrics
- **Centralized control:** Backend owns all LLM access; frontend becomes presentation layer only

### Why Tokens Require Governance First

$RING exists today but lacks enforcement mechanisms. Users can farm RING via gaming behaviors (bot posting, fake engagement, coordinated networks). Phase 10.2 prerequisites:
- **Agent enforcement from 10.1** ensures only vetted content earns RING
- **Audit trails** enable retroactive detection of gaming patterns
- **Rate limiting** prevents bulk farming via automation

Without agent gates, token economics are unenforceable. With them, $RING becomes a reliable signal of verified creative behavior.

### Why Platform Exposure Comes LAST

External APIs increase attack surface. Phase 10.3 prerequisites:
- **Agent enforcement (10.1)** ensures external consumers cannot bypass safety filters
- **Token loop (10.2)** provides economic disincentives for abuse (RING deductions for failed posts)
- **Observability infrastructure** from 10.1 enables real-time abuse detection

Exposing APIs before these foundations invites:
- **Unvetted content** published via external integrations
- **RING farming** via API endpoints
- **Data corruption** from malformed external writes

Platform extensibility is the final layer, built on hardened internals.

---

## Part B: Agent Enforcement Deep Dive (Phase 10.1)

### Current Agent Inventory

| Agent | File | Status | Role Today |
|-------|------|--------|------------|
| **Research Agent** | `backend/agents/research_agent.py` | Stub (empty) | Planned: pull trends, keywords, references |
| **Strategy Agent** | `backend/agents/strategy_agent.py` | Stub (empty) | Planned: create content strategy + angle |
| **Writer Agent** | `backend/agents/writer_agent.py` | Stub (empty) | Planned: generate scripts, threads, captions |
| **Viral Thread Agent** | `backend/agents/viral_thread.py` | Active | Researcher → Writer → Optimizer chain for X threads |
| **QA Agent** | `backend/agents/qa_agent.py` | Stub (empty) | Planned: brand safety, compliance checks |
| **Posting Agent** | `backend/agents/posting_agent.py` | Stub (empty) | Planned: publish to X / IG / YT |
| **Analytics Agent** | `backend/agents/analytics_agent.py` | Stub (empty) | Planned: collect metrics → TimescaleDB |
| **Visual Agent** | `backend/agents/visual_agent.py` | Stub (empty) | Planned: generate images (OpenAI, SD, GroqVision) |
| **Video Agent** | `backend/agents/video_agent.py` | Stub (empty) | Planned: edit clips automatically |

**Reality Check:**
- Only **Viral Thread Agent** is production-ready (Researcher → Writer → Optimizer chain)
- All other agents are empty stubs or planned features
- No agent enforcement exists today (users can bypass all agents via frontend)

---

### Agent-by-Agent Phase 10 Upgrade Plan

#### 1. Research Agent

**Current Role:** Stub (empty file)

**Gaps:**
- No trend retrieval logic
- No pgvector integration for similar past content
- No keyword extraction

**Phase 10 Upgrade:**
- **Mandatory inputs:** Topic, user_id, platform (X/IG/TikTok)
- **Deterministic outputs:** List of 2-3 viral angles, key insight (string), similar past threads (IDs)
- **Data sources:** pgvector similarity search (user's past posts), mock trend API for Phase 10 (real trends in Phase 11)
- **Allowed to block:** None (research is informational, never blocking)
- **NOT allowed to decide:** Whether content ships (that's QA agent's role)
- **Audit artifacts:** Research workflow ID, query time, similarity scores, angles generated

**Implementation:**
```python
class ResearchOutput(BaseModel):
    angles: List[str]  # 2-3 viral angles
    key_insight: str
    similar_thread_ids: List[str]
    workflow_id: str
    query_duration_ms: int
```

---

#### 2. Strategy Agent

**Current Role:** Stub (empty file)

**Gaps:**
- No content strategy logic
- No archetype integration (creator personas)
- No goal alignment checks

**Phase 10 Upgrade:**
- **Mandatory inputs:** Topic, research output, user archetype (from Clerk metadata)
- **Deterministic outputs:** Content strategy (dict), recommended tone, platform-specific angles
- **Data sources:** User archetype, momentum score, past post performance
- **Allowed to block:** None (strategy is advisory)
- **NOT allowed to decide:** Final content (Writer agent owns that)
- **Audit artifacts:** Strategy workflow ID, archetype used, tone rationale

**Implementation:**
```python
class StrategyOutput(BaseModel):
    content_strategy: Dict[str, str]  # {"hook": "...", "value": "...", "cta": "..."}
    recommended_tone: str  # "contrarian" | "personal" | "educational"
    platform_angles: Dict[str, str]  # {"X": "...", "IG": "..."}
    workflow_id: str
```

---

#### 3. Writer Agent

**Current Role:** Stub (empty file) — but Viral Thread Writer is active

**Gaps:**
- No standalone Writer agent (viral thread is specialized)
- No multi-platform support (viral thread is X-only)
- No length constraints by platform

**Phase 10 Upgrade:**
- **Mandatory inputs:** Strategy output, platform, user_id, harmful content flag
- **Deterministic outputs:** Content draft (string), character count, estimated engagement score
- **Data sources:** LLM (Groq), similar past threads (pgvector), user archetype
- **Allowed to block:** Harmful content (redirects to motivational topics)
- **NOT allowed to decide:** Whether content ships (QA agent decides), whether to post (user confirms)
- **Audit artifacts:** Writer workflow ID, LLM prompt, LLM response, token count, generation time

**Implementation:**
```python
class WriterOutput(BaseModel):
    content_draft: str
    character_count: int
    estimated_engagement_score: float  # 0.0-1.0
    harmful_content_detected: bool
    redirection_applied: Optional[str]
    workflow_id: str
    token_count: int
    generation_time_ms: int
```

**Harmful Content Detection (Expanded from Viral Thread):**
```python
HARMFUL_KEYWORDS = [
    "worthless", "piece of shit", "kill myself", "useless", 
    "hate myself", "fuck up", "loser", "stupid", "end it all",
    "no point", "give up", "failure", "waste of space"
]

def detect_harmful_content(topic: str) -> bool:
    return any(keyword in topic.lower() for keyword in HARMFUL_KEYWORDS)

def redirect_harmful_topic(original_topic: str) -> str:
    return f"Turning self-doubt into fuel: {original_topic}. Let's create content about growth, resilience, and finding strength."
```

---

#### 4. Viral Thread Agent (Existing, Production-Ready)

**Current Role:** Active (Researcher → Writer → Optimizer chain for X threads)

**Gaps:**
- No enforcement (can be bypassed)
- No workflow ID logging
- No failure retry logic
- No agent observability dashboard integration

**Phase 10 Upgrade:**
- **Make MANDATORY:** All X thread generation MUST route through viral_thread.py
- **Add workflow ID:** UUID assigned at entry, logged in all agent steps
- **Add telemetry:** Log entry/exit times for researcher, writer, optimizer
- **Add circuit breaker:** If optimizer fails 3 times, return writer draft with warning
- **Audit artifacts:** Workflow ID, researcher_duration_ms, writer_duration_ms, optimizer_duration_ms, final_tweet_count

**Implementation:**
```python
@dataclass
class ViralThreadWorkflow:
    workflow_id: str
    user_id: str
    topic: str
    created_at: datetime
    researcher_duration_ms: int
    writer_duration_ms: int
    optimizer_duration_ms: int
    final_tweet_count: int
    success: bool
    failure_reason: Optional[str]
```

---

#### 5. QA Agent (Gatekeeper)

**Current Role:** Stub (empty file)

**Gaps:**
- No brand safety checks
- No compliance validation (GDPR, COPPA, platform TOS)
- No profanity filtering (beyond harmful content detection)

**Phase 10 Upgrade:**
- **Mandatory inputs:** Writer output, platform, user_id
- **Deterministic outputs:** Approval (bool), rejection reasons (list), sanitized content (string)
- **Data sources:** Banned word lists, platform TOS rules, user verified status
- **Allowed to block:** Yes (this is the ONLY agent that can reject content before posting)
- **NOT allowed to decide:** Content strategy (Strategy agent), content wording (Writer agent)
- **Audit artifacts:** QA workflow ID, checks performed, rejection reasons, approval decision

**Blocking Criteria:**
- Contains banned words (profanity, slurs, spam keywords)
- Violates platform TOS (X: no impersonation; IG: no nudity; TikTok: no dangerous challenges)
- User not verified AND content mentions payments/money (anti-scam)
- Content length exceeds platform limits (X: 280 chars/tweet; IG: 2200 chars)

**Implementation:**
```python
class QAOutput(BaseModel):
    approved: bool
    rejection_reasons: List[str]  # [] if approved
    sanitized_content: Optional[str]  # with banned words replaced
    checks_performed: List[str]  # ["profanity", "tos_compliance", "length"]
    workflow_id: str
```

**Deterministic Check Logic:**
```python
def check_profanity(content: str) -> bool:
    banned_words = ["fuck", "shit", "damn", ...]  # Load from config
    return not any(word in content.lower() for word in banned_words)

def check_platform_tos(content: str, platform: str) -> bool:
    if platform == "X":
        return "impersonat" not in content.lower()
    elif platform == "IG":
        return "nudity" not in content.lower()
    return True

def check_length(content: str, platform: str) -> bool:
    limits = {"X": 280, "IG": 2200, "TikTok": 150}
    return len(content) <= limits.get(platform, 2200)
```

---

#### 6. Posting Agent

**Current Role:** Stub (empty file)

**Gaps:**
- No platform routing logic
- No retry on transient failures
- No RING award calculation

**Phase 10 Upgrade:**
- **Mandatory inputs:** QA-approved content, platform, user_id, auth tokens
- **Deterministic outputs:** Post URL, post ID, platform response, RING earned (int)
- **Data sources:** Twitter API v2, Instagram Graph API, TikTok API, user verified status
- **Allowed to block:** None (if QA approved, posting agent attempts delivery; failures logged, not blocking)
- **NOT allowed to decide:** Content quality (QA decided), RING amount (formula is deterministic)
- **Audit artifacts:** Posting workflow ID, platform, post_id, url, engagement metrics (initial), RING earned, failure reason (if any)

**Implementation:**
```python
class PostingOutput(BaseModel):
    success: bool
    post_url: Optional[str]
    post_id: Optional[str]
    platform: str
    ring_earned: int  # Calculated: views/100 + likes*5 + retweets*10 + 50*(is_verified)
    failure_reason: Optional[str]
    workflow_id: str
    posted_at: datetime
```

**RING Calculation (Deterministic):**
```python
def calculate_ring_award(platform_response: dict, user_verified: bool) -> int:
    views = platform_response.get("views", 0)
    likes = platform_response.get("likes", 0)
    retweets = platform_response.get("retweets", 0)
    
    ring = (views // 100) + (likes * 5) + (retweets * 10)
    if user_verified:
        ring += 50
    
    return max(0, ring)  # Never negative
```

---

#### 7. Analytics Agent

**Current Role:** Stub (empty file)

**Gaps:**
- No metrics collection
- No event stream integration (DraftCreated, SegmentAdded, RingPassed)
- No leaderboard computation

**Phase 10 Upgrade:**
- **Mandatory inputs:** Post ID, platform response, user_id, workflow_id
- **Deterministic outputs:** Analytics event (dict), leaderboard delta (int), user rank change (int)
- **Data sources:** Platform APIs (engagement metrics), PostgreSQL (event store), Redis (leaderboard cache)
- **Allowed to block:** None (analytics never blocks content flow)
- **NOT allowed to decide:** RING amounts (Posting agent calculates)
- **Audit artifacts:** Analytics workflow ID, events emitted, leaderboard updated (bool)

**Implementation:**
```python
class AnalyticsOutput(BaseModel):
    event_type: str  # "DraftPublished", "RingPassed", "SegmentAdded"
    event_data: Dict[str, Any]
    leaderboard_delta: int  # RING change for user
    user_rank_change: int  # +5 means moved up 5 positions
    workflow_id: str
    emitted_at: datetime
```

---

#### 8. Visual Agent

**Current Role:** Stub (empty file)

**Gaps:**
- No image generation logic
- No platform-specific image sizing (X: 1200x675, IG: 1080x1080, TikTok: 1080x1920)

**Phase 10 Upgrade:**
- **Mandatory inputs:** Content draft, platform, visual style (from archetype)
- **Deterministic outputs:** Image URL (S3), image dimensions, generation prompt used
- **Data sources:** OpenAI DALL·E 3, Stable Diffusion, GroqVision (mock for Phase 10)
- **Allowed to block:** None (if image generation fails, post ships text-only)
- **NOT allowed to decide:** Content strategy (Strategy agent)
- **Audit artifacts:** Visual workflow ID, generation_time_ms, prompt, model used, image_url

**Phase 10 Scope:**
- Stub implementation only (mock image URLs)
- Real image generation deferred to Phase 11

---

#### 9. Video Agent

**Current Role:** Stub (empty file)

**Gaps:**
- No video editing logic
- No clip assembly

**Phase 10 Upgrade:**
- **Phase 10 Scope:** Stub only (not implemented)
- **Phase 11 Target:** Automated video editing (FFmpeg-based clip assembly)

---

### Agent Enforcement Summary

| Agent | Phase 10 Status | Mandatory? | Can Block? | Audit Required? |
|-------|----------------|------------|-----------|----------------|
| Research | Implement | No (advisory) | No | Yes (workflow ID, query time) |
| Strategy | Implement | No (advisory) | No | Yes (workflow ID, archetype) |
| Writer | Implement | **Yes** | Yes (harmful content) | Yes (workflow ID, token count) |
| Viral Thread | Harden | **Yes** | Yes (harmful content) | Yes (workflow ID, all agent times) |
| QA | Implement | **Yes** | **Yes** (only blocking agent) | Yes (workflow ID, rejection reasons) |
| Posting | Implement | **Yes** | No (logs failures) | Yes (workflow ID, RING earned) |
| Analytics | Implement | **Yes** | No | Yes (workflow ID, events emitted) |
| Visual | Stub only | No | No | Yes (mock workflow ID) |
| Video | Stub only | No | No | No (deferred to Phase 11) |

**Human Override Policy:**
- QA agent rejections can be overridden by user clicking "Post Anyway" button
- Override logged: `{"user_id": "...", "override_reason": "user_confirmed", "original_rejection": [...], "timestamp": "..."}`
- Override increments risk score: 3 overrides in 7 days → temporary shadow ban (posts require manual review)

---

## Part C: Token Loop Activation Design (Phase 10.2)

### Current Token State (Phase 9.6)

**What Exists:**
- RING balance stored in Clerk `publicMetadata.ring`
- Staking system: lock RING for 30-180 days, earn 10-25% APR
- Award formula: `views/100 + likes*5 + retweets*10 + 50*(is_verified)`
- Rate limiting: 5 posts per 15 minutes (Redis TTL)

**What's Missing:**
- No deductions for failed posts
- No decay mechanism (RING accumulates forever)
- No lifetime cap (unbounded inflation)
- No audit trail (transactions not logged immutably)
- No gaming detection (sybil attacks, bot farms)

---

### Phase 10.2 Token Loop Rules

#### Eligible Events for RING Accrual

| Event | RING Award | Conditions |
|-------|-----------|-----------|
| **Post Published** | `views/100 + likes*5 + retweets*10 + 50*(is_verified)` | QA approved, no blocks |
| **Ring Passed** | +10 RING | To collaborator, draft has ≥2 segments |
| **Referral Signup** | +50 RING (both) | Referee makes first purchase |
| **Streak Milestone** | +100 RING | 7-day, 30-day, 90-day streaks |
| **Challenge Completed** | +25 RING | Daily challenge (post 1 insight in 4 lines) |

#### Explicitly NOT Eligible Events

| Event | RING Award | Rationale |
|-------|-----------|-----------|
| Draft Created | 0 | No proof of work (can spam drafts) |
| Segment Added | 0 | Gameable (add many 1-char segments) |
| Profile Viewed | 0 | Passive, no effort |
| Login | 0 | Trivial to automate |
| Content Liked by User | 0 | Not creator action |

---

#### RING Deductions (New)

| Event | RING Deduction | Conditions |
|-------|---------------|-----------|
| **Post Failed** | -10 RING | QA rejected, platform API error |
| **Abandoned Draft** | -5 RING/day | Ring held >7 days, no activity |
| **QA Override 3x** | -50 RING | User overrides QA rejection 3x in 7 days |
| **Detected Bot Activity** | -500 RING | Rate limit exceeded, coordinated posting |
| **Referral Fraud** | -200 RING | Self-referrals, fake accounts |

---

#### RING Decay Mechanism

**Formula:**
```python
def apply_monthly_decay(current_balance: int) -> int:
    """
    Apply 1% monthly decay on holdings > 10,000 RING.
    Encourages circulation and prevents hoarding.
    """
    if current_balance <= 10_000:
        return current_balance
    
    excess = current_balance - 10_000
    decay = int(excess * 0.01)
    return current_balance - decay
```

**Example:**
- User has 50,000 RING
- Excess: 50,000 - 10,000 = 40,000
- Decay: 40,000 × 1% = 400 RING
- New balance: 50,000 - 400 = 49,600 RING

**Cron Job:**
- Runs monthly (1st of each month, 00:00 UTC)
- Queries: `SELECT id, publicMetadata FROM users WHERE publicMetadata.ring > 10000`
- Updates: `UPDATE users SET publicMetadata.ring = new_balance WHERE id = user_id`
- Logs: `{"event": "RingDecay", "user_id": "...", "old_balance": 50000, "new_balance": 49600, "decay_amount": 400}`

---

#### Lifetime RING Cap

**Cap:** 1,000,000 RING per user (lifetime earnings)

**Enforcement:**
```python
def award_ring(user_id: str, amount: int) -> bool:
    """
    Award RING, respecting lifetime cap.
    Returns True if awarded, False if cap reached.
    """
    user = get_user(user_id)
    lifetime_earnings = user.publicMetadata.get("lifetime_ring_earned", 0)
    
    if lifetime_earnings >= 1_000_000:
        logger.warning(f"User {user_id} reached lifetime RING cap")
        return False
    
    remaining_capacity = 1_000_000 - lifetime_earnings
    actual_award = min(amount, remaining_capacity)
    
    update_user_metadata(user_id, {
        "ring": user.publicMetadata.ring + actual_award,
        "lifetime_ring_earned": lifetime_earnings + actual_award
    })
    
    log_ring_transaction(user_id, "award", actual_award, "post_published")
    return True
```

---

### Agent Enforcement Gates Token Issuance

**Flow:**
```
User writes content
  → Writer Agent (generates draft)
    → QA Agent (approves/rejects)
      → Posting Agent (publishes + calculates RING)
        → Analytics Agent (logs transaction)
```

**RING Award Prerequisites:**
1. QA Agent approved (no blocks)
2. Platform API returned success (post published)
3. User below lifetime cap (< 1M RING)
4. No rate limit exceeded (< 5 posts in 15min)

**If any prerequisite fails:**
- No RING awarded
- Event logged: `{"event": "RingAwardFailed", "user_id": "...", "reason": "qa_rejected", "post_id": "..."}`

---

### Anti-Gaming Principles

#### Rate Limiting

**Current:** 5 posts per 15 minutes (Redis TTL)

**Phase 10.2 Enhancement:**
- Dynamic limits based on verified status:
  - Unverified: 5 posts / 15min
  - Verified (Stripe): 10 posts / 15min
  - Verified + 90-day streak: 15 posts / 15min

**Implementation:**
```python
def get_rate_limit(user_id: str) -> int:
    """Return posts per 15min limit for user."""
    user = get_user(user_id)
    is_verified = user.publicMetadata.get("verified", False)
    streak_days = user.publicMetadata.get("streak_days", 0)
    
    if is_verified and streak_days >= 90:
        return 15
    elif is_verified:
        return 10
    else:
        return 5
```

---

#### Sybil Resistance

**Assumptions:**
- One person controls multiple accounts
- Coordinates referrals to farm +50 RING bonuses
- Uses same payment method across accounts

**Detection Heuristics:**
```python
def detect_sybil_network(user_id: str) -> bool:
    """
    Detect if user is part of sybil attack network.
    Returns True if suspicious patterns detected.
    """
    user = get_user(user_id)
    
    # Check 1: Self-referrals (referrer_id == user_id)
    referrals = get_referrals(user_id)
    if any(r.referrer_id == user_id for r in referrals):
        return True
    
    # Check 2: Same payment method (Stripe) across >3 accounts
    stripe_customer_id = user.publicMetadata.get("stripe_customer_id")
    if stripe_customer_id:
        accounts_with_same_payment = query_stripe_accounts(stripe_customer_id)
        if len(accounts_with_same_payment) > 3:
            return True
    
    # Check 3: Coordinated posting (same IP, same timestamps)
    recent_posts = get_recent_posts(user_id, limit=10)
    if detect_coordinated_pattern(recent_posts):
        return True
    
    return False
```

**Phase 10.2 Scope:** Detection only (log warnings)  
**Phase 11:** Automated bans + RING clawbacks

---

#### Dispute Resolution

**User Reports Incorrect RING Deduction:**
1. User submits support ticket with post_id, expected RING, actual RING
2. Admin queries audit trail: `SELECT * FROM ring_transactions WHERE post_id = ?`
3. If bug found (formula error), manual credit issued
4. If abuse found (QA override spam), deduction stands

**No Automated Clawbacks in Phase 10.2:**
- All clawbacks require manual review
- Prevents false positive damage
- Phase 11 may add automated clawbacks for egregious abuse (>10x rate limit exceeded)

---

### Shadow Accounting vs Live Accounting

**Phase 10.2 Approach:**
- **Live accounting:** RING balance updated in Clerk immediately after post published
- **Audit trail:** All transactions logged in PostgreSQL (append-only table)

**Schema:**
```sql
CREATE TABLE ring_transactions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,  -- 'award', 'deduction', 'decay', 'stake', 'unstake'
    amount INT NOT NULL,
    reason TEXT NOT NULL,  -- 'post_published', 'qa_rejected', 'monthly_decay', etc.
    post_id TEXT,
    workflow_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ring_tx_user ON ring_transactions(user_id, created_at DESC);
CREATE INDEX idx_ring_tx_post ON ring_transactions(post_id);
```

**Audit Query (Verify Balance):**
```sql
SELECT 
    user_id,
    SUM(CASE WHEN transaction_type IN ('award', 'stake', 'unstake') THEN amount ELSE -amount END) AS computed_balance
FROM ring_transactions
WHERE user_id = 'user_xyz'
GROUP BY user_id;
```

**Reconciliation Job (Daily):**
- Query computed balance from audit trail
- Compare with Clerk `publicMetadata.ring`
- If mismatch > 10 RING, log alert for manual review

---

## Part D: External Platform Surface Area (Phase 10.3)

### Public API Layer

**Scope:** Read-only data access, no writes to core data (drafts, segments, ring state)

**API Structure:**
```
/api/v1/external/
├── /users/{user_id}/profile          GET  — Public profile data
├── /users/{user_id}/posts            GET  — Published posts only
├── /users/{user_id}/ring             GET  — RING balance, lifetime earnings
├── /leaderboard                      GET  — Top 100 by RING, momentum, streaks
├── /posts/{post_id}                  GET  — Single post detail
└── /health                           GET  — API status
```

**Authentication:** OAuth2 (Clerk-managed)
- API key issuance via Clerk dashboard
- Scoped permissions: `read:profile`, `read:posts`, `read:leaderboard`
- No write permissions in Phase 10.3

**Rate Limiting:**
- Free tier: 100 requests / hour
- Verified users: 1,000 requests / hour
- Exceeded: HTTP 429 with `Retry-After` header

---

### Webhook System

**Scope:** Outbound webhooks for key events

**Supported Events:**
| Event | Payload | Trigger |
|-------|---------|---------|
| `draft.published` | `{draft_id, user_id, platform, url, ring_earned}` | Post successfully published |
| `ring.passed` | `{draft_id, from_user_id, to_user_id, ring_holder_duration_ms}` | Ring passed to collaborator |
| `ring.earned` | `{user_id, amount, reason, post_id}` | RING awarded (post engagement) |
| `streak.milestone` | `{user_id, streak_days, milestone}` | 7/30/90-day streak achieved |

**Webhook Registration:**
- User settings → "Webhooks" tab
- Add endpoint URL (HTTPS only)
- Select events to subscribe
- Webhook secret auto-generated (HMAC-SHA256 signing)

**Delivery Guarantees:**
- **At-least-once delivery** (may retry on transient failures)
- **Retry logic:** 3 retries with exponential backoff (5s, 25s, 125s)
- **Timeout:** 10 seconds per attempt
- **Dead letter queue:** After 3 failures, event stored in DLQ (manual replay)

**Webhook Signing (HMAC-SHA256):**
```python
import hmac
import hashlib

def generate_webhook_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

# Example request
headers = {
    "Content-Type": "application/json",
    "X-OneRing-Signature": generate_webhook_signature(payload, webhook_secret),
    "X-OneRing-Event": "draft.published",
    "X-OneRing-Delivery-ID": "uuid-12345"
}
```

**Consumer Validation:**
```python
def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature matches payload."""
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)
```

---

### Posting Agent as ONLY Publish Path

**Invariant:** All content publishing MUST route through Posting Agent (no external direct writes)

**Enforcement:**
- Platform API tokens (X, IG, TikTok) stored server-side only (never exposed to clients)
- External API has no `POST /posts` endpoint (read-only)
- Plugins must trigger OneRing's Posting Agent (cannot post directly)

**Plugin Publishing Flow:**
```
External Plugin
  → POST /api/v1/external/trigger-publish (authenticated, scoped)
    → Backend validates API key + permissions
      → Backend enqueues posting job (RQ worker)
        → Posting Agent executes (QA already passed at draft creation)
          → Webhook fires: draft.published
```

**Why This Matters:**
- Ensures QA agent always runs (brand safety, compliance)
- Centralizes RING award calculation (deterministic formula)
- Prevents platform API abuse (rate limits enforced in Posting Agent)

---

### Abuse Prevention & Kill-Switches

**API Abuse Detection:**
```python
def check_api_abuse(api_key: str) -> bool:
    """
    Detect API abuse patterns.
    Returns True if abuse detected.
    """
    rate_limit_exceeded = redis.get(f"api_key:{api_key}:requests") > 1000  # 1000/hour
    
    # Check for suspicious patterns
    recent_requests = get_recent_requests(api_key, limit=100)
    
    # Pattern 1: Same endpoint hit >50% of time (scraping)
    endpoint_distribution = Counter(r.endpoint for r in recent_requests)
    if max(endpoint_distribution.values()) > 50:
        return True
    
    # Pattern 2: Requests from >10 IPs in 1 hour (distributed attack)
    ip_distribution = Counter(r.ip for r in recent_requests)
    if len(ip_distribution) > 10:
        return True
    
    return False
```

**Kill-Switch Levels:**
| Level | Trigger | Action | Recovery |
|-------|---------|--------|----------|
| **Level 1** | Rate limit exceeded | HTTP 429, retry after 1 hour | Automatic |
| **Level 2** | Abuse pattern detected | API key suspended, requires email verification | Manual unblock |
| **Level 3** | Security incident (leaked keys, DDoS) | All external API traffic blocked | Engineering review |

**Admin Dashboard:**
- Real-time API usage metrics (requests/hour by key)
- Abuse alerts (flagged patterns)
- Kill-switch controls (suspend key, block IP, global disable)

---

### Versioning Strategy

**API Versioning:** URL-based (`/api/v1/external/*`, `/api/v2/external/*`)

**Deprecation Policy:**
- Major versions supported for 12 months after new version released
- Breaking changes require new major version (v2, v3)
- Non-breaking additions (new fields, new endpoints) allowed in minor versions (v1.1, v1.2)

**Example Breaking Change (Requires v2):**
- Renaming `ring` field to `ring_balance`
- Changing date format from Unix timestamp to ISO 8601
- Removing endpoint entirely

**Example Non-Breaking Change (Allowed in v1):**
- Adding new field `archetype` to user profile response
- Adding new endpoint `/api/v1/external/users/{user_id}/momentum`
- Adding optional query parameter `?include_archived=true`

---

### What is Internal-Only vs External

| Resource | Internal Route | External Route | Exposed? |
|----------|---------------|---------------|----------|
| **User Profile (Public)** | `/api/users/{id}` | `/api/v1/external/users/{id}/profile` | ✅ Yes |
| **User Profile (Private)** | `/api/users/{id}/settings` | N/A | ❌ No |
| **Published Posts** | `/api/posts/{id}` | `/api/v1/external/posts/{id}` | ✅ Yes |
| **Draft Posts** | `/api/collab/drafts/{id}` | N/A | ❌ No |
| **Ring Transactions** | `/api/ring/transactions` | `/api/v1/external/users/{id}/ring` | ✅ Partial (balance only) |
| **Leaderboard** | `/api/analytics/leaderboard` | `/api/v1/external/leaderboard` | ✅ Yes |
| **Agent Workflows** | `/api/monitoring/workflows` | N/A | ❌ No |
| **Clerk User Metadata** | Internal Clerk API | N/A | ❌ No |

---

### Platform Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **API Key Leakage** | High | Short-lived tokens (1 week), key rotation enforced |
| **DDoS Attack** | High | Cloudflare rate limiting, kill-switch |
| **Data Scraping** | Medium | Aggressive rate limits (100/hour free, 1000/hour paid) |
| **Webhook Spam** | Medium | Retry limits (3 attempts), dead letter queue |
| **Plugin Malware** | High | Sandboxed execution, manual approval queue |

---

### Reputational Risks

| Risk | Scenario | Mitigation |
|------|----------|-----------|
| **Harmful Content via API** | External app posts offensive content via OneRing | Posting Agent QA checks apply to all sources |
| **RING Farming via API** | Bot farms use external API to game RING awards | Rate limits, sybil detection, Stripe verification |
| **Data Breach** | Leaked API keys expose user data | Read-only permissions, no PII in external API |

---

### Compliance Risks

| Risk | Regulation | Mitigation |
|------|-----------|-----------|
| **GDPR (User Data Export)** | Users can request data export | External API exposes user's own data only (no cross-user access) |
| **COPPA (Minors)** | Users <13 cannot use platform | Age verification in Clerk signup, no external bypass |
| **Platform TOS Violations** | External apps violate X/IG/TikTok TOS | QA Agent checks TOS compliance for all posts |

---

## Part E: Invariants, Guarantees, and Non-Goals

### System Invariants (After Phase 10)

1. **All content flows through agents** — No frontend → Groq direct calls. Backend owns all LLM access.

2. **QA Agent is the only blocker** — Research, Strategy, Writer, Posting, Analytics agents are informational or execution; only QA can reject content.

3. **RING transactions are immutable** — Once logged in `ring_transactions` table, never deleted or modified (append-only).

4. **Workflow IDs are unique and traceable** — Every agent execution has UUID, logged in all artifacts.

5. **Rate limits are deterministic** — Redis TTL enforces 5/10/15 posts per 15min based on user verified status.

6. **External APIs are read-only** — No write access to drafts, segments, ring state via `/api/v1/external/*`.

7. **Posting Agent calculates RING** — Award formula is deterministic: `views/100 + likes*5 + retweets*10 + 50*(is_verified)`.

8. **Webhooks are at-least-once** — May retry up to 3 times; consumer must handle duplicates.

9. **Lifetime RING cap is 1,000,000** — No user can earn more than 1M RING (total, including decays).

10. **Clerk is source of truth for user state** — RING balance, verified status, metadata stored in Clerk `publicMetadata`.

---

### Hard Guarantees Provided by System

1. **Harmful content is redirected** — Writer Agent detects self-harm keywords, redirects to motivational topics.

2. **Agent failures do not block users permanently** — Circuit breaker returns degraded content (writer draft without optimizer).

3. **RING balance audit trail exists** — `SELECT SUM(amount) FROM ring_transactions WHERE user_id = ?` always matches Clerk metadata (within ±10 RING tolerance).

4. **QA rejections are logged and reviewable** — Admin dashboard shows all rejection reasons, user can dispute.

5. **Platform API tokens never exposed** — X/IG/TikTok auth stored server-side, never sent to frontend or external APIs.

6. **Webhook signatures prevent spoofing** — HMAC-SHA256 ensures payloads are authentic.

7. **API rate limits prevent runaway costs** — 100/hour free, 1000/hour paid, enforced via Redis.

8. **Plugin sandboxing prevents DB access** — Plugins run in isolated workers, no direct PostgreSQL/Redis access.

9. **All tests pass (GREEN ALWAYS)** — 1013 tests (618 backend + 395 frontend), zero skipped, no `--no-verify` bypasses.

10. **Deprecation warnings precede breaking changes** — External API v1 supported for 12 months after v2 released.

---

### Explicit Non-Goals (Phase 10 Refuses to Solve)

#### Agent-Related Non-Goals

1. **Multi-LLM support** — Groq (llama-3.1-8b-instant) remains sole provider. No OpenAI/Anthropic/Gemini switching.

2. **Agent marketplace** — Users cannot author custom agents or share agent configs.

3. **No-code agent builder** — Users cannot modify agent prompts or workflows via UI.

4. **Autonomous posting** — Agents never post without explicit user confirmation (no "auto-pilot mode").

5. **Agent A/B testing UI** — Prompt tuning happens via code, not user-facing experiments.

---

#### Token-Related Non-Goals

1. **Blockchain integration** — $RING remains PostgreSQL-backed. No Ethereum, Solana, or any blockchain.

2. **RING to USD conversion** — $RING has no real-world value, no cash-out, no exchanges.

3. **Cross-platform RING** — $RING is OneRing-only, not portable to other apps.

4. **Token burning** — Only decay exists (1% monthly for >10K holdings). No burn mechanism.

5. **DeFi features** — No liquidity pools, no lending, no yield farming beyond staking.

6. **NFT integration** — No NFT minting, no token-gated content.

---

#### Platform-Related Non-Goals

1. **GraphQL API** — REST only. Simpler to version, secure, and document.

2. **WebSockets for external consumers** — Polling only (external APIs). Internal WebSockets remain for real-time collab.

3. **White-label / rebrand** — OneRing branding required. No self-hosted instances.

4. **Plugin revenue sharing** — Plugins are internal-only for now. No marketplace, no commissions.

5. **Real-time streaming to external** — External consumers poll. No SSE/WebSocket streams.

6. **Write access via external API** — Read-only. Drafts, segments, ring state remain internal.

---

#### General Non-Goals

1. **Mobile app (native)** — Web-first. PWA acceptable, no iOS/Android native apps in Phase 10.

2. **Multi-language support** — English only. i18n deferred to Phase 11+.

3. **Video generation (real)** — Video Agent is stub. Real video editing in Phase 11.

4. **Live collaboration (simultaneous editing)** — Polling-based updates. No Yjs/CRDT in Phase 10.

5. **Machine learning recommendations** — Rule-based insights only. ML deferred to Phase 11.

---

## Part F: Sub-Phase Breakdown & Acceptance Criteria

### Phase 10.1 — Agent-First Productization

#### Entry Criteria

- [ ] Phase 9.6 complete (hooks, safety contracts, documentation locked)
- [ ] All 1013 tests passing (618 backend + 395 frontend)
- [ ] Viral Thread Agent operational (Researcher → Writer → Optimizer)
- [ ] PostgreSQL + pgvector operational (user embeddings working)
- [ ] Redis operational (rate limiting functional)

#### Exit Criteria

- [ ] **Zero frontend → Groq direct calls** — All content generation routes through backend agents
- [ ] **Agent telemetry live** — Workflow IDs, timing metrics, failure reasons logged in PostgreSQL
- [ ] **Agent observability dashboard shipped** — `/monitoring` page shows agent execution traces
- [ ] **QA Agent blocks harmful content** — Test cases for profanity, TOS violations, length limits (all passing)
- [ ] **Circuit breaker functional** — 3 optimizer failures return writer draft with warning (tested)
- [ ] **Tests pass: 618 → 680+ backend** — New agent tests added (Research, Strategy, Writer, QA, Posting, Analytics)

#### Success Signals

- User generates content → sees agent workflow ID in UI
- Admin reviews `/monitoring` → sees real-time agent traces (Researcher → Writer → QA → Posting)
- QA Agent rejects profanity → user sees rejection reason, sanitized version offered
- Agent failure → circuit breaker returns degraded content, user notified
- No direct LLM calls in frontend codebase (grep search confirms)

#### Failure Signals

- Agent failures block users >2% of the time (exceeds target)
- Agent latency p90 >2 seconds (too slow, users frustrated)
- Agent telemetry gaps >5% (missing workflow IDs)
- Frontend still contains Groq API calls (bypass paths exist)

#### Rollback Plan

- Revert backend changes, restore frontend → backend proxy (direct LLM calls allowed temporarily)
- Disable agent enforcement flag: `AGENT_ENFORCEMENT_ENABLED=false`
- Investigate failures, fix agent logic, re-deploy with tests passing

#### Decisions Required BEFORE Execution

1. **Agent latency SLA** — Is p90 <2s acceptable? Or target <1s?
2. **Circuit breaker thresholds** — 3 failures in a row? Or 3 failures in 10 attempts?
3. **Telemetry retention** — 7 days? 30 days? Or 90 days?
4. **Agent observability UX** — User-facing traces or admin-only?

---

### Phase 10.2 — Token Loop Activation

#### Entry Criteria

- [ ] Phase 10.1 complete (agent enforcement live)
- [ ] Agent telemetry logging RING awards (Posting Agent logs transactions)
- [ ] PostgreSQL table `ring_transactions` created (append-only audit trail)
- [ ] Clerk `publicMetadata.ring` and `.lifetime_ring_earned` fields exist

#### Exit Criteria

- [ ] **RING deductions active** — Failed posts deduct -10 RING (tested)
- [ ] **RING decay cron job deployed** — Runs monthly, applies 1% decay to >10K holdings
- [ ] **Lifetime cap enforced** — Users hitting 1M RING cannot earn more (tested)
- [ ] **Audit trail reconciliation job live** — Daily job compares Clerk balance vs audit trail (alerts on mismatch)
- [ ] **Sybil detection heuristics deployed** — Logs warnings for suspicious patterns (no auto-bans yet)
- [ ] **Tests pass: 680 → 720+ backend** — New tests for deductions, decay, cap, audit trail

#### Success Signals

- User fails post → sees -10 RING deduction in transaction history
- Admin runs audit query → computed balance matches Clerk balance
- Monthly decay job runs → users >10K RING see 1% reduction
- User hits 1M lifetime cap → sees "Congratulations! You've reached the RING cap" message
- Sybil detection logs warnings → admin reviews, confirms false positives low (<5%)

#### Failure Signals

- Audit trail mismatches exceed 10 RING (indicates transaction bug)
- Users complain about incorrect deductions (>1% of transactions disputed)
- Decay job fails or skips users (cron reliability issue)
- Lifetime cap not enforced (users exceed 1M RING)

#### Rollback Plan

- Disable deductions: Set `RING_DEDUCTIONS_ENABLED=false`
- Disable decay: Skip cron job for 1 month while investigating
- Manual RING credits for incorrect deductions (admin script)
- Hotfix bugs, re-deploy with tests passing

#### Decisions Required BEFORE Execution

1. **Deduction amounts** — Is -10 RING for failed post too harsh? Or too lenient?
2. **Decay rate** — 1% monthly? Or 0.5%? Or 2%?
3. **Lifetime cap** — 1M RING? Or 500K? Or 2M?
4. **Sybil clawback policy** — Manual review only? Or automated after X detections?

---

### Phase 10.3 — Platform / External Surface Area

#### Entry Criteria

- [ ] Phase 10.2 complete (token loop active, audit trail functional)
- [ ] Agent enforcement stable (failure rate <2%)
- [ ] RING economy stable (no major exploits found)
- [ ] OAuth2 scopes defined (`read:profile`, `read:posts`, `read:leaderboard`)

#### Exit Criteria

- [ ] **External API live** — `/api/v1/external/*` endpoints documented, versioned
- [ ] **Webhooks functional** — 3 retries with exponential backoff, HMAC-SHA256 signing
- [ ] **Rate limiting enforced** — 100/hour free, 1000/hour paid (tested)
- [ ] **Plugin sandbox operational** — Isolated FastAPI workers, no DB access (tested)
- [ ] **Kill-switch implemented** — Admin can suspend API keys, block IPs, disable all external traffic
- [ ] **3 external integrations built** — Zapier, n8n, custom user app (demos working)
- [ ] **Tests pass: 720 → 780+ backend** — New tests for external API, webhooks, rate limits, sandboxing

#### Success Signals

- External developer integrates via Zapier → receives `draft.published` webhook
- API rate limit exceeded → HTTP 429 returned with `Retry-After` header
- Malicious API key detected → suspended within 5 minutes (kill-switch functional)
- Webhook delivery success rate >95% (measured over 7 days)
- Zero security incidents from external API (90 days)

#### Failure Signals

- Webhook delivery success rate <90% (retry logic insufficient)
- API abuse detected, but kill-switch not used (admin unaware or slow to react)
- Plugin escapes sandbox, accesses PostgreSQL directly (sandbox broken)
- External API breaks internal routes (routing conflict)

#### Rollback Plan

- Disable external API: Set `EXTERNAL_API_ENABLED=false`
- Suspend all API keys: Bulk revoke, notify users via email
- Disable webhooks: Stop retry queue processing
- Fix security issues, re-deploy with pen test passing

#### Decisions Required BEFORE Execution

1. **Rate limit thresholds** — 100/hour free, 1000/hour paid? Or adjust based on infra cost?
2. **Webhook retry window** — 3 retries over 2 minutes? Or 5 retries over 10 minutes?
3. **Plugin approval criteria** — Security audit? Code review? Sandbox escape attempts?
4. **API versioning cadence** — Support v1 for 12 months? Or 6 months?

---

## Execution Readiness Checklist

### Prerequisites (Blocking Phase 10 Start)

- [ ] **All open P0 questions resolved** — Currently none; confirm before starting 10.1
- [ ] **Senior engineering review complete** — This master plan approved by technical lead
- [ ] **Security review complete** — QA blocking logic, RING deduction logic, external API security reviewed
- [ ] **Compliance review complete** — GDPR, COPPA, platform TOS compliance confirmed
- [ ] **Test infrastructure ready** — Backend at 618 tests, frontend at 395 tests, all green
- [ ] **Monitoring infrastructure ready** — `/monitoring` dashboard operational, agent traces viewable

### Phase 10.1 Pre-Execution

- [ ] Resolve agent latency SLA decision
- [ ] Resolve circuit breaker threshold decision
- [ ] Resolve telemetry retention policy
- [ ] Resolve agent observability UX (user-facing or admin-only)

### Phase 10.2 Pre-Execution

- [ ] Resolve deduction amounts (-10 RING for failed post confirmed?)
- [ ] Resolve decay rate (1% monthly confirmed?)
- [ ] Resolve lifetime cap (1M RING confirmed?)
- [ ] Resolve sybil clawback policy (manual review only?)

### Phase 10.3 Pre-Execution

- [ ] Resolve rate limit thresholds (100/hour free, 1000/hour paid confirmed?)
- [ ] Resolve webhook retry window (3 retries over 2min confirmed?)
- [ ] Resolve plugin approval criteria (manual review required?)
- [ ] Resolve API versioning cadence (12 months support confirmed?)

---

## Timeline & Dependencies

| Sub-Phase | Duration | Start Date | Dependencies |
|-----------|----------|-----------|--------------|
| **Phase 10.1** | 3-4 weeks | TBD | Phase 9.6 complete, all tests green |
| **Phase 10.2** | 2-3 weeks | 10.1 complete | Agent telemetry logging RING awards |
| **Phase 10.3** | 4-5 weeks | 10.2 complete | Token loop stable, no major exploits |

**Total Phase 10 Duration:** 9-12 weeks (Q1 2026 estimate)

**Critical Path:**
```
Phase 9.6 (complete)
  → Phase 10.1 (agent enforcement)
    → Phase 10.2 (token loop)
      → Phase 10.3 (external APIs)
```

**Parallelization Opportunities:**
- During 10.1: Begin 10.2 schema design (ring_transactions table)
- During 10.2: Begin 10.3 API documentation (OpenAPI spec)
- During 10.3: Begin Phase 11 planning (ML recommendations, video generation)

---

## Post-Phase 10 Outcomes

### System State After Phase 10

1. **Agent-First Architecture** — All content generation routes through LangGraph agents. No frontend bypasses.

2. **Token Economy Active** — $RING accrual, deductions, decay, lifetime cap all enforced. Audit trail complete.

3. **Platform Extensibility Defined** — External API live, webhooks functional, plugin architecture operational.

4. **Quality Bar Raised** — QA Agent blocks harmful content, profanity, TOS violations. Zero tolerance for unsafe posts.

5. **Observability Complete** — Agent traces, RING transaction history, API usage metrics all visible in `/monitoring` dashboard.

6. **Security Hardened** — Platform API tokens server-side only, webhook signing enforced, rate limits prevent abuse.

7. **Compliance Ready** — GDPR data export via external API, COPPA age verification, platform TOS compliance checked by QA Agent.

8. **Test Coverage Maintained** — 780+ backend tests, 395+ frontend tests, zero skipped, GREEN ALWAYS policy intact.

9. **Documentation Current** — `.ai/ROADMAP.md`, `.ai/PROJECT_STATE.md`, `.ai/OPEN_QUESTIONS_AND_TODOS.md` all reflect Phase 10 reality.

10. **Architectural Decisions Preserved** — Clerk, FastAPI, PostgreSQL, LangGraph, Groq all unchanged. No drift.

---

## Risks & Mitigations Summary

| Risk Category | Top Risk | Mitigation |
|--------------|----------|-----------|
| **Agent Complexity** | Debugging agent chains is hard | Comprehensive telemetry (workflow IDs, timing, failures) |
| **Token Gaming** | Bot farms exploit RING awards | Rate limits, sybil detection, Stripe verification gates |
| **API Abuse** | DDoS or scraping via external API | Aggressive rate limits, kill-switch, OAuth2 scoping |
| **Platform Reputation** | Harmful content published via external integrations | QA Agent applies to all sources (internal + external) |
| **Regulatory Scrutiny** | RING perceived as security | Explicit disclaimers, TOS updates, no USD conversion |
| **Scope Creep** | Phase 10.3 becomes full marketplace | Strict non-goals list, timeline boundaries enforced |

---

## Next Steps

1. **Senior engineering review** — Approve or request revisions to this master plan
2. **Resolve all pre-execution decisions** — Latency SLA, decay rate, rate limits, etc.
3. **Update `.ai/DECISIONS.md`** — Record decisions made during planning
4. **Create Phase 10.1 task breakdown** — Split into one-commit tasks for execution
5. **Assign owners** — Backend lead, frontend lead, security reviewer
6. **Kick off Phase 10.1** — Agent-First Productization begins

---

**Document Status:** Planning complete, ready for stakeholder approval.  
**Next Review:** Before Phase 10.1 execution begins.  
**Approvals Required:** Technical lead, product owner, security, compliance.
