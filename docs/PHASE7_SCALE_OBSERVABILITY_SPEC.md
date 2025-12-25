## Phase 7 — Scale, Observability, Cost Control (Spec)

### Metrics Strategy
- **Backend surface:** Prometheus text format via `/metrics` (no auth).
- **Cardinality rules:**
  - Fixed label sets only; no user_id or request_id in metrics.
  - Paths normalized to route patterns (e.g., `/v1/collab/drafts/{id}` → `/v1/collab/drafts/:id`).
- **Counters:** `http_requests_total{method,path,status}`, `ws_connections_total`, `ws_messages_sent_total{event_type}`, `collab_mutations_total{type}`, `ratelimit_block_total{scope}`.
- **Gauges:** `ws_active_connections`, `drafts_active_rooms`.
- **Emit points:** HTTP middleware, WS connect/disconnect, collab emit_event broadcast, rate limit block paths.

### Tracing Strategy
- Optional OpenTelemetry, gated by `OTEL_ENABLED` (default false).
- Minimal setup: in-process tracer provider + stdout exporter when enabled; no vendor lock.
- Spans: HTTP lifecycle, collab mutations, WS connection lifetime, emit_event broadcast; propagate `request_id` as span attribute.

### Logging Levels & Structure
- JSON logs in prod, pretty in dev (existing). Enforce structured fields on every log:
  - `request_id` (always), `user_id` when known, `draft_id` when applicable, `event_type` for WS emits, `error_code` on failures.
- Levels: INFO for normal ops, WARN for soft limit warnings (e.g., soft caps), ERROR for failures/exceptions.
- Keep audit log schema unchanged.

### Cost Controls
- New caps: `MAX_WS_CONNECTIONS_PER_DRAFT`, `MAX_COLLABORATORS_PER_DRAFT`, `MAX_SEGMENTS_PER_DRAFT` (soft warn).
- Configurable via env; all default OFF/None for tests/dev.
- Rate-limit block counter for visibility; WS fanout counters for sizing.

### Horizontal Scaling Constraints
- Current in-memory WS hub is single-process only; does not replicate across instances.
- Metrics will expose WS active counts to detect saturation.
- Phase 8 decision: Redis pub/sub vs NATS vs managed WS gateway; see decision tree below (also in MIGRATIONS/Phase 8 notes).

### Out of Scope (Phase 7)
- No Redis/NATS WS fanout implementation.
- No paid APM/exporter integrations.
- No DB schema changes beyond existing tables.
- No breaking API/WS protocol changes.

### Decision Tree for Scale (Preview for Phase 8)
- If single-node suffices: keep in-memory hub.
- If multi-instance with shared state needed and infra has Redis: use Redis pub/sub for room fanout.
- If needing high fanout/low latency or multi-region: evaluate NATS JetStream or managed WS gateway (Ably/Pusher) with cost analysis.
