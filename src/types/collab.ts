/**
 * Collaboration types for frontend.
 * Mirrors backend models in backend/models/collab.py
 */

export type DraftStatus = "active" | "locked" | "completed";

export interface DraftSegment {
  segment_id: string;
  draft_id: string;
  user_id: string;
  content: string;
  created_at: string;
  segment_order: number;
  idempotency_key?: string;
  author_user_id?: string;
  author_display?: string;
  ring_holder_user_id_at_write?: string;
  ring_holder_display_at_write?: string;
}

export interface RingState {
  draft_id: string;
  current_holder_id: string;
  holders_history: string[];
  passed_at: string;
  last_passed_at?: string;
  idempotency_key?: string;
}

export interface CollabDraft {
  draft_id: string;
  creator_id: string;
  title: string;
  platform: string;
  status: DraftStatus;
  segments: DraftSegment[];
  ring_state: RingState;
  collaborators: string[];
  pending_invites: string[];
  created_at: string;
  updated_at: string;
  target_publish_at?: string;
  metrics?: {
    contributorsCount?: number;
    ringPassesLast24h?: number;
    avgMinutesBetweenPasses?: number;
    lastActivityAt?: string;
  };
}

export interface CollabDraftRequest {
  title: string;
  platform: string;
  initial_segment?: string;
}

export interface SegmentAppendRequest {
  content: string;
  idempotency_key: string;
}

export interface RingPassRequest {
  to_user_id: string;
  idempotency_key: string;
}

export interface AISuggestion {
  mode: "next" | "rewrite" | "summary" | "commentary";
  content: string;
  ring_holder: boolean;
  platform?: string;
  generated_at?: string;
}

export type FormatPlatform = "x" | "youtube" | "instagram" | "blog";

export interface FormatBlock {
  type: "heading" | "text" | "hashtag" | "cta" | "media_note";
  text: string;
  heading?: string;
}

export interface PlatformOutput {
  platform: FormatPlatform;
  blocks: FormatBlock[];
  plain_text: string;
  character_count: number;
  block_count: number;
  warnings: string[];
}

export interface FormatOptions {
  tone?: "professional" | "casual" | "witty" | "motivational" | "technical";
  include_hashtags?: boolean;
  include_cta?: boolean;
  hashtag_count?: number;
  hashtag_suggestions?: string[];
  cta_text?: string;
  cta_suggestions?: string[];
}

export interface FormatGenerateRequest {
  draft_id: string;
  platforms?: FormatPlatform[];
  options?: FormatOptions;
}

export interface FormatGenerateResponse {
  draft_id: string;
  outputs: Record<FormatPlatform, PlatformOutput>;
}

// Timeline types (Phase 8.3)
export type TimelineEventType = 
  | "draft_created"
  | "segment_added"
  | "ring_passed"
  | "collaborator_added"
  | "ai_suggested"
  | "format_generated"
  | "other";

export interface TimelineEvent {
  event_id: string;
  ts: string;  // ISO datetime
  type: TimelineEventType;
  actor_user_id: string | null;
  draft_id: string;
  summary: string;
  meta: Record<string, any>;
}

export interface TimelineResponse {
  draft_id: string;
  events: TimelineEvent[];
  next_cursor?: string;
}

export interface ContributorStats {
  user_id: string;
  segment_count: number;
  segment_ids: string[];
  first_ts: string;
  last_ts: string;
}

export interface AttributionResponse {
  draft_id: string;
  contributors: ContributorStats[];
}

export interface ExportRequest {
  format: "markdown" | "json";
  include_credits?: boolean;
}

export interface ExportResponse {
  draft_id: string;
  format: string;
  filename: string;
  content_type: string;
  content: string;
}

export type ErrorCode = 
  | "ring_required"
  | "rate_limited"
  | "permission_denied"
  | "not_found"
  | "validation_error"
  | "unknown_error";

export interface APIError {
  code: ErrorCode;
  message: string;
  status: number;
}
