/**
 * src/__tests__/leaderboard-panel.spec.tsx
 * Phase 3.4 LeaderboardPanel component tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LeaderboardPanel from "../components/analytics/LeaderboardPanel";

describe("LeaderboardPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it("should render with default metric (collaboration)", async () => {
    const mockResponse = {
      success: true,
      data: {
        metric_type: "collaboration",
        entries: [],
        computed_at: "2025-12-21T15:30:00Z",
        message: "Community highlights: creators shaping work together",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(<LeaderboardPanel />);

    expect(screen.getByText("Community Highlights")).toBeInTheDocument();
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("metric=collaboration")
      )
    );
  });

  it("should display top 10 entries max (defensive cap)", async () => {
    const mockEntries = Array.from({ length: 15 }, (_, i) => ({
      position: i + 1,
      user_id: `user-${i}`,
      display_name: `User ${i}`,
      avatar_url: null,
      metric_value: 100 - i,
      metric_label: `${i} segments`,
      insight: "Great work!",
    }));

    const mockResponse = {
      success: true,
      data: {
        metric_type: "collaboration",
        entries: mockEntries,
        computed_at: "2025-12-21T15:30:00Z",
        message: "Test message",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(<LeaderboardPanel />);

    await waitFor(() => {
      const displayedEntries = screen.getAllByRole("heading", { level: 3 });
      expect(displayedEntries.length).toBe(10); // Capped at 10
    });
  });

  it("should display loading state", () => {
    vi.mocked(global.fetch).mockImplementation(
      () =>
        new Promise(() => {
          /* never resolves */
        })
    );

    render(<LeaderboardPanel />);

    expect(screen.getByText("Loading highlights...")).toBeInTheDocument();
  });

  it("should display error state", async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      json: async () => ({ error: "Backend unavailable" }),
    } as any);

    render(<LeaderboardPanel />);

    await waitFor(() => {
      expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
    });
  });

  it("should allow metric selection change", async () => {
    const mockResponse = {
      success: true,
      data: {
        metric_type: "momentum",
        entries: [],
        computed_at: "2025-12-21T15:30:00Z",
        message: "Test message",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(<LeaderboardPanel />);

    const select = screen.getByLabelText("Highlight Type");
    fireEvent.change(select, { target: { value: "momentum" } });

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("metric=momentum")
      )
    );
  });

  it("should refresh data on button click", async () => {
    const mockResponse = {
      success: true,
      data: {
        metric_type: "collaboration",
        entries: [],
        computed_at: "2025-12-21T15:30:00Z",
        message: "Test message",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(<LeaderboardPanel />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));

    const refreshButton = screen.getByText("Refresh");
    fireEvent.click(refreshButton);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  });

  it("should display empty state when no entries", async () => {
    const mockResponse = {
      success: true,
      data: {
        metric_type: "collaboration",
        entries: [],
        computed_at: "2025-12-21T15:30:00Z",
        message: "Test message",
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    render(<LeaderboardPanel />);

    await waitFor(() => {
      expect(screen.getByText("No highlights yet")).toBeInTheDocument();
    });
  });

  it("should not contain forbidden comparative language", async () => {
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

    render(<LeaderboardPanel />);

    const componentText = screen.getByText("Community Highlights").closest("div")?.textContent || "";

    forbiddenPhrases.forEach((phrase) => {
      expect(componentText.toLowerCase()).not.toContain(phrase);
    });
  });
});
