-- Phase 10.2: Add RING ledger table for append-only accounting
-- Migration created: 2025-12-25

-- Ledger table (append-only)
CREATE TABLE IF NOT EXISTS ring_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    draft_id UUID NULL,
    request_id VARCHAR(255) NULL,
    receipt_id VARCHAR(255) NULL,
    event_type VARCHAR(50) NOT NULL,  -- EARN, SPEND, PENALTY, ADJUSTMENT
    reason_code VARCHAR(100) NOT NULL,  -- publish_success, qa_bonus, rate_limit_penalty, etc.
    amount INT NOT NULL,
    balance_after INT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for querying
CREATE INDEX IF NOT EXISTS idx_ring_ledger_user_id ON ring_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_ring_ledger_created_at ON ring_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_ring_ledger_event_type ON ring_ledger(event_type);
CREATE INDEX IF NOT EXISTS idx_ring_ledger_request_id ON ring_ledger(request_id);

-- Pending rewards table (shadow mode)
CREATE TABLE IF NOT EXISTS ring_pending (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    draft_id UUID NULL,
    request_id VARCHAR(255) NULL,
    amount INT NOT NULL,
    reason_code VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    would_issue_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, issued, expired
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ring_pending_user_id ON ring_pending(user_id);
CREATE INDEX IF NOT EXISTS idx_ring_pending_status ON ring_pending(status);

-- Guardrails state table (for anti-gaming tracking)
CREATE TABLE IF NOT EXISTS ring_guardrails_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL UNIQUE,
    daily_earn_count INT DEFAULT 0,
    daily_earn_total INT DEFAULT 0,
    last_earn_at TIMESTAMP NULL,
    anomaly_flags JSONB DEFAULT '{}',
    reset_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ring_guardrails_user_id ON ring_guardrails_state(user_id);

-- Invariants and constraints
ALTER TABLE ring_ledger ADD CONSTRAINT chk_ledger_earn_positive 
    CHECK (event_type != 'EARN' OR amount > 0);

ALTER TABLE ring_ledger ADD CONSTRAINT chk_ledger_penalty_negative 
    CHECK (event_type NOT IN ('PENALTY', 'SPEND') OR amount < 0 OR event_type = 'ADJUSTMENT');

COMMENT ON TABLE ring_ledger IS 'Append-only ledger for RING token accounting (Phase 10.2)';
COMMENT ON TABLE ring_pending IS 'Shadow-mode pending rewards before live issuance';
COMMENT ON TABLE ring_guardrails_state IS 'Anti-gaming state tracking per user';
