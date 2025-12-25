/**
 * Tests for CollabTimeline component (Phase 8.3)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CollabTimeline from "@/components/CollabTimeline";
import * as collabApi from "@/lib/collabApi";

// Mock the API
vi.mock("@/lib/collabApi");

describe("CollabTimeline", () => {
  const mockTimeline = {
    draft_id: "draft1",
    events: [
      {
        event_id: "1",
        ts: new Date().toISOString(),
        type: "draft_created" as const,
        actor_user_id: "user123",
        draft_id: "draft1",
        summary: "@user1 created draft 'Test Draft'",
        meta: {},
      },
      {
        event_id: "2",
        ts: new Date(Date.now() - 3600000).toISOString(),
        type: "segment_added" as const,
        actor_user_id: "user456",
        draft_id: "draft1",
        summary: "@user2 added segment: Hello world...",
        meta: { segment_id: "seg1" },
      },
    ],
    next_cursor: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders sign-in message when not authenticated", () => {
    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={false}
      />
    );

    expect(screen.getByText(/sign in to view timeline/i)).toBeInTheDocument();
  });

  it("loads and displays timeline events", async () => {
    vi.mocked(collabApi.getTimeline).mockResolvedValue(mockTimeline);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText(/loading timeline/i)).not.toBeInTheDocument();
    });

    // Check events are displayed
    expect(screen.getByText(/@user1 created draft 'Test Draft'/)).toBeInTheDocument();
    expect(screen.getByText(/@user2 added segment: Hello world.../)).toBeInTheDocument();
  });

  it("displays correct icons for event types", async () => {
    vi.mocked(collabApi.getTimeline).mockResolvedValue(mockTimeline);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });

    // Icons should be visible (emojis in text content)
    const eventContainers = screen.getAllByText(/✨|🧑|👑|➕|🤖|📋|📌/);
    expect(eventContainers.length).toBeGreaterThan(0);
  });

  it("shows loading state", () => {
    vi.mocked(collabApi.getTimeline).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    expect(screen.getByText(/loading timeline/i)).toBeInTheDocument();
  });

  it("shows error state and retry button", async () => {
    const mockError = new Error("Network error");
    vi.mocked(collabApi.getTimeline).mockRejectedValue(mockError);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/retry/i)).toBeInTheDocument();
  });

  it("calls refresh when refresh button clicked", async () => {
    vi.mocked(collabApi.getTimeline).mockResolvedValue(mockTimeline);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });

    const refreshButton = screen.getByText(/refresh/i);
    fireEvent.click(refreshButton);

    // getTimeline should be called twice: initial load + refresh
    await waitFor(() => {
      expect(collabApi.getTimeline).toHaveBeenCalledTimes(2);
    });
  });

  it("shows 'Load More' button when next_cursor exists", async () => {
    const timelineWithCursor = {
      ...mockTimeline,
      next_cursor: "cursor123",
    };

    vi.mocked(collabApi.getTimeline).mockResolvedValue(timelineWithCursor);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/load more/i)).toBeInTheDocument();
    });
  });

  it("loads more events when 'Load More' clicked", async () => {
    const timelineWithCursor = {
      ...mockTimeline,
      next_cursor: "cursor123",
    };

    const moreEvents = {
      draft_id: "draft1",
      events: [
        {
          event_id: "3",
          ts: new Date(Date.now() - 7200000).toISOString(),
          type: "ring_passed" as const,
          actor_user_id: "user123",
          draft_id: "draft1",
          summary: "@user1 passed ring to @user2",
          meta: {},
        },
      ],
      next_cursor: null,
    };

    vi.mocked(collabApi.getTimeline)
      .mockResolvedValueOnce(timelineWithCursor)
      .mockResolvedValueOnce(moreEvents);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/load more/i)).toBeInTheDocument();
    });

    const loadMoreButton = screen.getByText(/load more/i);
    fireEvent.click(loadMoreButton);

    await waitFor(() => {
      expect(screen.getByText(/@user1 passed ring to @user2/)).toBeInTheDocument();
    });

    // Should call with cursor
    expect(collabApi.getTimeline).toHaveBeenCalledWith("draft1", {
      limit: 50,
      asc: false,
      cursor: "cursor123",
    });
  });

  it("shows empty state when no events", async () => {
    vi.mocked(collabApi.getTimeline).mockResolvedValue({
      draft_id: "draft1",
      events: [],
      next_cursor: null,
    });

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/no events yet/i)).toBeInTheDocument();
    });
  });

  it("calls onError callback when error occurs", async () => {
    const mockError = new Error("API Error");
    const onError = vi.fn();
    vi.mocked(collabApi.getTimeline).mockRejectedValue(mockError);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
        onError={onError}
      />
    );

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("API Error");
    });
  });

  it("displays relative time (e.g., '2h ago')", async () => {
    vi.mocked(collabApi.getTimeline).mockResolvedValue(mockTimeline);

    render(
      <CollabTimeline
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });

    // Should show relative times like "just now", "1h ago", etc.
    const relativeTimeElements = screen.getAllByText(/ago|just now/i);
    expect(relativeTimeElements.length).toBeGreaterThan(0);
  });
});
