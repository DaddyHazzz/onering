# Domain — Events (Analytics & Collaboration)

Canonical append-only event schema for Phase 3.4 analytics. Preserves Phase 1 (streaks/momentum) vocabulary.

## Event Types (Analytics)
- DraftCreated(draft_id: string, creator_id: string, created_at: ISO8601)
- DraftViewed(draft_id: string, user_id: string, viewed_at: ISO8601)
- SegmentAdded(draft_id: string, segment_id: string, contributor_id: string, added_at: ISO8601)
- RingPassed(from_user_id: string, to_user_id: string, draft_id: string, passed_at: ISO8601)
- DraftPublished(draft_id: string, published_at: ISO8601)

## Idempotency Keys
- DraftViewed: (draft_id, user_id, viewed_at_bucket)
- SegmentAdded: segment_id
- RingPassed: (from_user_id, to_user_id, draft_id, passed_at)
- DraftCreated/DraftPublished: draft_id

## Determinism
- Reducers accept `now` (optional ISO). Same events + same `now` → identical read models.
- All timestamps treated as UTC.

## Read Models
- DraftAnalytics: views, shares, segments_count, contributors_count, ring_passes_last_24h, last_activity
- UserAnalytics: drafts_created, drafts_contributed, segments_written, rings_held, avg_hold_minutes
- LeaderboardEntry: position (1..10), user_id, display_name, avatar_url?, metric_value, metric_label, insight
- LeaderboardResponse: metric_type, entries (≤10), computed_at, message

## Safety Constraints
- No sensitive fields (token_hash, emails, secrets) in read models.
- Insights use supportive language; forbid “behind”, “catch up”, “rank shame”.

## Phase 1 Vocabulary (Preserved)
- StreakStarted, StreakContinued, StreakBroken (used by momentum reducers)
