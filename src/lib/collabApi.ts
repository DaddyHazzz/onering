/**
 * Frontend API client for collaboration endpoints.
 * 
 * Strongly typed wrapper around /v1/collab/* endpoints.
 * 
 * Phase 6.1: Now uses Clerk JWT for real auth.
 * Falls back to X-User-Id header for backward compatibility (tests).
 * Handles error normalization and ring-required detection.
 */

import { 
  CollabDraft, 
  DraftSegment, 
  CollabDraftRequest, 
  SegmentAppendRequest, 
  RingPassRequest,
  APIError 
} from "@/types/collab";

const BASE_URL = "/v1/collab";

/**
 * Get auth headers for API requests.
 * 
 * Priority:
 * 1. Clerk JWT from localStorage (set by useAuth hook)
 * 2. X-User-Id fallback (for tests/backward compatibility)
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  // Try Clerk JWT first
  const clerkToken = typeof window !== "undefined" 
    ? localStorage.getItem("clerk_token") 
    : null;
  
  if (clerkToken) {
    return {
      "Authorization": `Bearer ${clerkToken}`,
    };
  }

  // Fallback to X-User-Id for backward compatibility
  const testUserId = typeof window !== "undefined"
    ? localStorage.getItem("test_user_id")
    : null;
  
  if (testUserId) {
    return {
      "X-User-Id": testUserId,
    };
  }

  // No auth available (read-only mode)
  return {};
}

/**
 * Fetch with auth headers automatically injected.
 * 
 * Tries Clerk JWT first, falls back to X-User-Id.
 */
async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const url = `${BASE_URL}${endpoint}`;
  const authHeaders = await getAuthHeaders();
  
  const headers = {
    "Content-Type": "application/json",
    ...authHeaders,
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const body = await response.json();

  // Normalize error responses
  if (!response.ok) {
    const error: APIError = {
      code: body.error?.code || "unknown_error",
      message: body.error?.message || "An error occurred",
      status: response.status,
    };
    throw error;
  }

  return body;
}

/**
 * List all drafts involving the current user.
 */
export async function listDrafts(): Promise<CollabDraft[]> {
  const response = await apiFetch("/drafts");
  return response.data || [];
}

/**
 * Create a new draft.
 */
export async function createDraft(
  request: CollabDraftRequest
): Promise<CollabDraft> {
  const response = await apiFetch("/drafts", {
    method: "POST",
    body: JSON.stringify(request),
  });
  return response.data;
}

/**
 * Get draft detail by ID.
 */
export async function getDraft(draftId: string): Promise<CollabDraft> {
  const response = await apiFetch(`/drafts/${draftId}`);
  return response.data;
}

/**
 * Append segment to draft (idempotent).
 * 
 * Throws APIError with code="ring_required" if user is not ring holder.
 */
export async function appendSegment(
  draftId: string,
  request: SegmentAppendRequest
): Promise<CollabDraft> {
  try {
    const response = await apiFetch(`/drafts/${draftId}/segments`, {
      method: "POST",
      body: JSON.stringify(request),
    });
    return response.data;
  } catch (error: any) {
    // Re-throw with code preserved for ring_required detection
    if (error.code === "ring_required") {
      throw error;
    }
    throw error;
  }
}

/**
 * Pass ring to another user (idempotent).
 */
export async function passRing(
  draftId: string,
  request: RingPassRequest
): Promise<CollabDraft> {
  const response = await apiFetch(`/drafts/${draftId}/pass-ring`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  return response.data;
}

/**
 * Add collaborator to draft (creator only).
 */
export async function addCollaborator(
  draftId: string,
  collaboratorId: string,
  role: string = "contributor"
): Promise<CollabDraft> {
  const response = await apiFetch(`/drafts/${draftId}/collaborators`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  return response.data;
}

/**
 * Check if error is a ring_required error.
 */
export function isRingRequiredError(error: unknown): error is APIError {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as any).code === "ring_required"
  );
}
