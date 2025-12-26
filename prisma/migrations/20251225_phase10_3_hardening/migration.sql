-- Phase 10.3 Hardening: webhook engine + API key controls

-- External API keys: IP allowlist + rotation timestamp
ALTER TABLE external_api_keys
  ADD COLUMN IF NOT EXISTS ip_allowlist TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS rotated_at TIMESTAMPTZ NULL;

-- Webhook events table (durable event log)
CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    user_id TEXT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON webhook_events (event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events (created_at);

-- Webhook deliveries hardening
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'webhook_deliveries' AND column_name = 'next_retry_at'
    ) THEN
        ALTER TABLE webhook_deliveries RENAME COLUMN next_retry_at TO next_attempt_at;
    END IF;
END $$;

ALTER TABLE webhook_deliveries
    ADD COLUMN IF NOT EXISTS last_status_code INTEGER NULL,
    ADD COLUMN IF NOT EXISTS event_timestamp TIMESTAMPTZ NULL;

-- Backfill event_timestamp for existing rows
UPDATE webhook_deliveries
SET event_timestamp = COALESCE(event_timestamp, created_at);

-- Backfill webhook_events for existing deliveries before adding FK
INSERT INTO webhook_events (id, event_type, user_id, payload, created_at)
SELECT DISTINCT d.event_id, d.event_type, NULL, COALESCE(CAST(d.payload AS JSONB), '{}'::JSONB), COALESCE(d.created_at, NOW())
FROM webhook_deliveries d
LEFT JOIN webhook_events e ON e.id = d.event_id
WHERE e.id IS NULL;

-- Add FK to webhook_events
ALTER TABLE webhook_deliveries
    ADD CONSTRAINT webhook_deliveries_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES webhook_events(id)
    ON DELETE CASCADE;

-- Update indexes for next_attempt_at
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'webhook_deliveries_nextretryat_idx'
    ) THEN
        DROP INDEX webhook_deliveries_nextretryat_idx;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS webhook_deliveries_nextattemptat_idx
    ON webhook_deliveries (next_attempt_at)
    WHERE status = 'pending';
