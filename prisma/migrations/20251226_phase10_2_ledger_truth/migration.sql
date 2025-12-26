-- Phase 10.2 Ledger Truth hardening
-- Indices and sync tracking for canonical balances.

-- Publish events indices (additive)
CREATE INDEX IF NOT EXISTS idx_publish_events_platform ON publish_events(platform);
CREATE INDEX IF NOT EXISTS idx_publish_events_created_at ON publish_events(created_at);
CREATE INDEX IF NOT EXISTS idx_publish_events_platform_post_id ON publish_events(platform_post_id);

-- Ring ledger indices (ensure present)
CREATE INDEX IF NOT EXISTS idx_ring_ledger_user_id ON ring_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_ring_ledger_created_at ON ring_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_ring_ledger_event_type ON ring_ledger(event_type);

-- Ring pending indices
CREATE INDEX IF NOT EXISTS idx_ring_pending_user_id ON ring_pending(user_id);
CREATE INDEX IF NOT EXISTS idx_ring_pending_created_at ON ring_pending(created_at);

-- Clerk sync status table
CREATE TABLE IF NOT EXISTS ring_clerk_sync (
  user_id TEXT PRIMARY KEY,
  last_sync_at TIMESTAMPTZ,
  last_error TEXT,
  last_error_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ring_clerk_sync_error_at ON ring_clerk_sync(last_error_at);

-- Publish event idempotency conflicts (append-only)
CREATE TABLE IF NOT EXISTS publish_event_conflicts (
  id SERIAL PRIMARY KEY,
  event_id TEXT NOT NULL,
  user_id TEXT,
  reason TEXT NOT NULL DEFAULT 'idempotent_replay',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_publish_event_conflicts_event ON publish_event_conflicts(event_id, created_at);
