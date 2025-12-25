-- Phase 10.3: External Platform Surface Area
-- Tables for external API keys, webhooks, and delivery tracking

-- External API keys for third-party integrations
CREATE TABLE external_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id TEXT NOT NULL UNIQUE,  -- public identifier (e.g., osk_abc123)
    key_hash TEXT NOT NULL,        -- bcrypt hash of full key
    owner_user_id TEXT NOT NULL,   -- Clerk user ID
    scopes TEXT[] NOT NULL DEFAULT '{}',  -- e.g., ['read:rings', 'read:drafts']
    rate_limit_tier TEXT NOT NULL DEFAULT 'free',  -- free, pro, enterprise
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_external_api_keys_key_id ON external_api_keys(key_id) WHERE is_active = true;
CREATE INDEX idx_external_api_keys_owner ON external_api_keys(owner_user_id);

-- Webhook subscriptions
CREATE TABLE external_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id TEXT NOT NULL,
    url TEXT NOT NULL,
    secret TEXT NOT NULL,  -- HMAC secret for signing
    events TEXT[] NOT NULL DEFAULT '{}',  -- e.g., ['draft.published', 'ring.passed']
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_delivered_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_external_webhooks_owner ON external_webhooks(owner_user_id);
CREATE INDEX idx_external_webhooks_active ON external_webhooks(is_active) WHERE is_active = true;

-- Webhook delivery tracking
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES external_webhooks(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,  -- unique event identifier
    event_type TEXT NOT NULL,  -- e.g., draft.published
    status TEXT NOT NULL,  -- pending, succeeded, failed
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ
);

CREATE INDEX idx_webhook_deliveries_webhook_id ON webhook_deliveries(webhook_id);
CREATE INDEX idx_webhook_deliveries_event_id ON webhook_deliveries(event_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX idx_webhook_deliveries_next_retry ON webhook_deliveries(next_retry_at) WHERE status = 'pending' AND next_retry_at IS NOT NULL;

-- Rate limiting tracking (if Redis unavailable)
CREATE TABLE external_api_rate_limits (
    key_id TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    request_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (key_id, window_start)
);

CREATE INDEX idx_external_api_rate_limits_window ON external_api_rate_limits(window_start);

-- IP blocklist for abuse control
CREATE TABLE external_api_blocklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type TEXT NOT NULL,  -- 'key_id' or 'ip_address'
    target_value TEXT NOT NULL UNIQUE,
    reason TEXT,
    blocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    blocked_by TEXT,  -- admin user ID
    expires_at TIMESTAMPTZ
);
CREATE INDEX idx_external_api_blocklist_target ON external_api_blocklist(target_type, target_value);
