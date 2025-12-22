/**
 * src/__tests__/draft-analytics-modal.spec.tsx
 * Phase 3.4 DraftAnalyticsModal component tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DraftAnalyticsModal from "../components/analytics/DraftAnalyticsModal";

describe("DraftAnalyticsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it("should not render when isOpen is false", () => {
    const { container } = render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={false} onClose={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("should render when isOpen is true", async () => {
    const mockResponse = {
      success: true,
      data: {
        draft_id: "draft-123",
        views: 10,
        shares: 5,
        segments_count: 3,
        contributors_count: 2,
        ring_passes_count: 4,
        last_activity_at: "2025-12-21T15:00:00Z",
        computed_at: "2025-12-21T15:30:00Z",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={() => {}} />
    );

    expect(screen.getByText("Momentum Snapshot")).toBeInTheDocument();
  });

  it("should fetch correct URL with draftId", async () => {
    const mockResponse = {
      success: true,
      data: {
        draft_id: "draft-xyz",
        views: 0,
        shares: 0,
        segments_count: 1,
        contributors_count: 1,
        ring_passes_count: 0,
        last_activity_at: null,
        computed_at: "2025-12-21T15:30:00Z",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(
      <DraftAnalyticsModal draftId="draft-xyz" isOpen={true} onClose={() => {}} />
    );

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/collab/drafts/draft-xyz/analytics")
      )
    );
  });

  it("should display all metrics with correct labels", async () => {
    const mockResponse = {
      success: true,
      data: {
        draft_id: "draft-123",
        views: 42,
        shares: 7,
        segments_count: 5,
        contributors_count: 3,
        ring_passes_count: 12,
        last_activity_at: "2025-12-21T15:00:00Z",
        computed_at: "2025-12-21T15:30:00Z",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={() => {}} />
    );

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument(); // views
      expect(screen.getByText("Views")).toBeInTheDocument();
      expect(screen.getByText("7")).toBeInTheDocument(); // shares
      expect(screen.getByText("Shares")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument(); // segments
      expect(screen.getByText("Segments")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument(); // contributors
      expect(screen.getByText("Contributors")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument(); // ring passes
      expect(screen.getByText("RING Passes")).toBeInTheDocument();
    });
  });

  it("should display loading state", () => {
    vi.mocked(global.fetch).mockImplementation(
      () =>
        new Promise(() => {
          /* never resolves */
        })
    );

    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={() => {}} />
    );

    expect(screen.getByText("Loading analytics...")).toBeInTheDocument();
  });

  it("should display error state", async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      json: async () => ({ error: "Draft not found" }),
    } as any);

    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={() => {}} />
    );

    await waitFor(() => {
      expect(screen.getByText("Draft not found")).toBeInTheDocument();
    });
  });

  it("should call onClose when close button is clicked", async () => {
    const mockResponse = {
      success: true,
      data: {
        draft_id: "draft-123",
        views: 0,
        shares: 0,
        segments_count: 1,
        contributors_count: 1,
        ring_passes_count: 0,
        last_activity_at: null,
        computed_at: "2025-12-21T15:30:00Z",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    const onCloseMock = vi.fn();
    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={onCloseMock} />
    );

    const closeButton = screen.getByLabelText("Close");
    fireEvent.click(closeButton);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it("should refresh data on refresh button click", async () => {
    const mockResponse = {
      success: true,
      data: {
        draft_id: "draft-123",
        views: 0,
        shares: 0,
        segments_count: 1,
        contributors_count: 1,
        ring_passes_count: 0,
        last_activity_at: null,
        computed_at: "2025-12-21T15:30:00Z",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={() => {}} />
    );

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));

    const refreshButton = screen.getByText("Refresh");
    fireEvent.click(refreshButton);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  });

  it("should not contain forbidden comparative language in UI copy", () => {
    const forbiddenPhrases = [
      "behind",
      "catch up",
      "falling",
      "ahead of",
      "better than",
      "worse than",
      "last place",
      "you lost",
      "rank shame",
    ];

    render(
      <DraftAnalyticsModal draftId="draft-123" isOpen={true} onClose={() => {}} />
    );

    const modalText = screen.getByText("Momentum Snapshot").closest("div")?.textContent || "";

    forbiddenPhrases.forEach((phrase) => {
      expect(modalText.toLowerCase()).not.toContain(phrase);
    });
  });
});
