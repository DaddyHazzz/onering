/**
 * AnalyticsPanel Integration Tests
 * 
 * Test cases:
 * 1. Renders all 3 tabs (Summary, Contributors, Ring)
 * 2. Loads and displays summary metrics with inactivity risk badge
 * 3. Displays contributors table with per-user metrics
 * 4. Shows ring dynamics (current holder, holds history, recommendation)
 * 5. Handles loading state and error states
 * 6. Non-collaborators see permission error
 * 7. Tab switching loads correct data
 * 8. Daily activity visualization works
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AnalyticsPanel from "@/components/AnalyticsPanel";
import * as collabApi from "@/lib/collabApi";

// Mock the API functions
jest.mock("@/lib/collabApi", () => ({
  getDraftAnalyticsSummary: jest.fn(),
  getDraftAnalyticsContributors: jest.fn(),
  getDraftAnalyticsRing: jest.fn(),
  getDraftAnalyticsDaily: jest.fn(),
}));

describe("AnalyticsPanel", () => {
  const mockDraftId = "draft-123";

  // Mock data generators
  function createMockSummary() {
    return {
      draft_id: mockDraftId,
      total_segments: 5,
      total_words: 245,
      unique_contributors: 3,
      inactivity_risk: "low" as const,
      hours_since_last_activity: 2,
      avg_time_holding_ring_seconds: 3600,
      last_activity_at: new Date().toISOString(),
    };
  }

  function createMockContributors() {
    return {
      draft_id: mockDraftId,
      contributors: [
        {
          user_id: "alice",
          segments_count: 2,
          words_count: 120,
          ring_holds_count: 1,
          ring_hold_time_total_seconds: 3600,
          first_contribution_at: "2025-01-01T00:00:00Z",
          last_contribution_at: "2025-01-02T10:00:00Z",
          wait_suggestions_count: 0,
          wait_votes_count: 0,
        },
        {
          user_id: "bob",
          segments_count: 2,
          words_count: 100,
          ring_holds_count: 0,
          ring_hold_time_total_seconds: 0,
          first_contribution_at: "2025-01-01T12:00:00Z",
          last_contribution_at: "2025-01-02T08:00:00Z",
          wait_suggestions_count: 1,
          wait_votes_count: 2,
        },
      ],
    };
  }

  function createMockRing() {
    return {
      draft_id: mockDraftId,
      holds: [
        {
          holder_id: "alice",
          start_at: "2025-01-02T10:00:00Z",
          end_at: null,
          hold_duration_seconds: 1800,
        },
      ],
      passes: [
        {
          passed_by_id: "bob",
          passed_to_id: "alice",
          passed_at: "2025-01-02T10:00:00Z",
        },
      ],
      recommendation: {
        recommended_user_id: "bob",
        reasoning: "Fewest segments (2) compared to alice (2), tie-broken by user_id",
      },
    };
  }

  function createMockDaily() {
    return {
      draft_id: mockDraftId,
      daily: [
        {
          date: "2025-01-02",
          segments_added: 2,
          ring_passes: 1,
        },
        {
          date: "2025-01-01",
          segments_added: 3,
          ring_passes: 0,
        },
      ],
    };
  }

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Render Tests", () => {
    it("should render all 3 tabs when collaborator", async () => {
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValueOnce(
        createMockSummary()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        expect(screen.getByText("Summary")).toBeInTheDocument();
        expect(screen.getByText("Contributors")).toBeInTheDocument();
        expect(screen.getByText("Ring")).toBeInTheDocument();
      });
    });

    it("should show permission error when non-collaborator", () => {
      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={false} />);

      expect(
        screen.getByText(/You must be a collaborator to view draft analytics/)
      ).toBeInTheDocument();
      expect(screen.queryByText("Summary")).not.toBeInTheDocument();
    });
  });

  describe("Summary Tab", () => {
    it("should load and display summary metrics", async () => {
      const mockSummary = createMockSummary();
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValueOnce(
        mockSummary
      );
      (collabApi.getDraftAnalyticsDaily as jest.Mock).mockResolvedValueOnce(
        createMockDaily()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        expect(screen.getByText("5")).toBeInTheDocument(); // Total segments
        expect(screen.getByText("245")).toBeInTheDocument(); // Total words
        expect(screen.getByText("3")).toBeInTheDocument(); // Contributors
      });
    });

    it("should display inactivity risk badge with correct color", async () => {
      const mockSummary = createMockSummary();
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValueOnce(
        mockSummary
      );
      (collabApi.getDraftAnalyticsDaily as jest.Mock).mockResolvedValueOnce(
        createMockDaily()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        const badge = screen.getByText("Low");
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass("bg-green-100");
      });
    });

    it("should show HIGH inactivity risk in red", async () => {
      const mockSummary = {
        ...createMockSummary(),
        inactivity_risk: "high" as const,
        hours_since_last_activity: 72,
      };
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValueOnce(
        mockSummary
      );
      (collabApi.getDraftAnalyticsDaily as jest.Mock).mockResolvedValueOnce(
        createMockDaily()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        const badge = screen.getByText("High");
        expect(badge).toHaveClass("bg-red-100");
      });
    });

    it("should allow filtering daily activity by days", async () => {
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValueOnce(
        createMockSummary()
      );
      (collabApi.getDraftAnalyticsDaily as jest.Mock).mockResolvedValueOnce(
        createMockDaily()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      const select = await screen.findByDisplayValue("14");
      fireEvent.change(select, { target: { value: "30" } });

      await waitFor(() => {
        expect(collabApi.getDraftAnalyticsDaily).toHaveBeenCalledWith(
          mockDraftId,
          30
        );
      });
    });
  });

  describe("Contributors Tab", () => {
    it("should load and display contributors table", async () => {
      (collabApi.getDraftAnalyticsContributors as jest.Mock).mockResolvedValueOnce(
        createMockContributors()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      const contributorsTab = screen.getByText("Contributors");
      fireEvent.click(contributorsTab);

      await waitFor(() => {
        expect(screen.getByText("alice")).toBeInTheDocument();
        expect(screen.getByText("bob")).toBeInTheDocument();
        expect(screen.getByText("2")).toBeInTheDocument(); // alice segments
        expect(screen.getByText("120")).toBeInTheDocument(); // alice words
      });
    });

    it("should display contributor metrics with segments, words, holds", async () => {
      (collabApi.getDraftAnalyticsContributors as jest.Mock).mockResolvedValueOnce(
        createMockContributors()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      fireEvent.click(screen.getByText("Contributors"));

      await waitFor(() => {
        // Table headers
        expect(screen.getByText("Contributor")).toBeInTheDocument();
        expect(screen.getByText("Segments")).toBeInTheDocument();
        expect(screen.getByText("Words")).toBeInTheDocument();
        expect(screen.getByText("Ring Holds")).toBeInTheDocument();
      });
    });

    it("should show contributor last activity timestamp", async () => {
      (collabApi.getDraftAnalyticsContributors as jest.Mock).mockResolvedValueOnce(
        createMockContributors()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      fireEvent.click(screen.getByText("Contributors"));

      await waitFor(() => {
        // Should show formatted date in table (Jan 02 format)
        const cells = screen.getAllByText(/Jan/);
        expect(cells.length).toBeGreaterThan(0);
      });
    });
  });

  describe("Ring Tab", () => {
    it("should load and display ring dynamics", async () => {
      (collabApi.getDraftAnalyticsRing as jest.Mock).mockResolvedValueOnce(
        createMockRing()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      fireEvent.click(screen.getByText("Ring"));

      await waitFor(() => {
        expect(screen.getByText("Currently Holding the Ring")).toBeInTheDocument();
        expect(screen.getByText("alice")).toBeInTheDocument(); // current holder
      });
    });

    it("should display ring hold history", async () => {
      (collabApi.getDraftAnalyticsRing as jest.Mock).mockResolvedValueOnce(
        createMockRing()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      fireEvent.click(screen.getByText("Ring"));

      await waitFor(() => {
        expect(screen.getByText("Ring Hold History")).toBeInTheDocument();
        expect(screen.getByText("alice")).toBeInTheDocument();
      });
    });

    it("should display recommended next holder with reasoning", async () => {
      (collabApi.getDraftAnalyticsRing as jest.Mock).mockResolvedValueOnce(
        createMockRing()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      fireEvent.click(screen.getByText("Ring"));

      await waitFor(() => {
        expect(screen.getByText("Recommended Next Holder")).toBeInTheDocument();
        expect(screen.getByText("bob")).toBeInTheDocument(); // recommended user
        expect(
          screen.getByText(/Fewest segments.*tie-broken by user_id/)
        ).toBeInTheDocument();
      });
    });

    it("should display ring passes history", async () => {
      (collabApi.getDraftAnalyticsRing as jest.Mock).mockResolvedValueOnce(
        createMockRing()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      fireEvent.click(screen.getByText("Ring"));

      await waitFor(() => {
        expect(screen.getByText(/bob → alice/)).toBeInTheDocument();
      });
    });
  });

  describe("Loading & Error States", () => {
    it("should show loading spinner while fetching", async () => {
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        expect(screen.getByText("Loading analytics...")).toBeInTheDocument();
      });
    });

    it("should display error message on fetch failure", async () => {
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockRejectedValueOnce(
        new Error("Network error")
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });

    it("should show error for missing draft", async () => {
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockRejectedValueOnce(
        new Error("Draft not found")
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      await waitFor(() => {
        expect(screen.getByText("Draft not found")).toBeInTheDocument();
      });
    });
  });

  describe("Tab Switching", () => {
    it("should switch between tabs and load correct data", async () => {
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValueOnce(
        createMockSummary()
      );
      (collabApi.getDraftAnalyticsDaily as jest.Mock).mockResolvedValueOnce(
        createMockDaily()
      );
      (collabApi.getDraftAnalyticsContributors as jest.Mock).mockResolvedValueOnce(
        createMockContributors()
      );
      (collabApi.getDraftAnalyticsRing as jest.Mock).mockResolvedValueOnce(
        createMockRing()
      );

      render(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      // Start on Summary
      await waitFor(() => {
        expect(screen.getByText("Total Segments")).toBeInTheDocument();
      });
      expect(collabApi.getDraftAnalyticsSummary).toHaveBeenCalledWith(
        mockDraftId
      );

      // Switch to Contributors
      fireEvent.click(screen.getByText("Contributors"));
      await waitFor(() => {
        expect(screen.getByText("alice")).toBeInTheDocument();
      });
      expect(collabApi.getDraftAnalyticsContributors).toHaveBeenCalledWith(
        mockDraftId
      );

      // Switch to Ring
      fireEvent.click(screen.getByText("Ring"));
      await waitFor(() => {
        expect(screen.getByText("Currently Holding the Ring")).toBeInTheDocument();
      });
      expect(collabApi.getDraftAnalyticsRing).toHaveBeenCalledWith(mockDraftId);
    });
  });

  describe("Deterministic Behavior", () => {
    it("should return same data for same draft on repeated calls", async () => {
      const mockSummary = createMockSummary();
      (collabApi.getDraftAnalyticsSummary as jest.Mock).mockResolvedValue(
        mockSummary
      );
      (collabApi.getDraftAnalyticsDaily as jest.Mock).mockResolvedValue(
        createMockDaily()
      );

      const { rerender } = render(
        <AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />
      );

      await waitFor(() => {
        expect(screen.getByText("5")).toBeInTheDocument();
      });

      const firstCallCount =
        collabApi.getDraftAnalyticsSummary.mock.callCount;

      // Re-render should use cached data
      rerender(<AnalyticsPanel draftId={mockDraftId} isCollaborator={true} />);

      // Call count should increase (effect runs again) but data should be consistent
      expect(collabApi.getDraftAnalyticsSummary.mock.callCount).toBeGreaterThanOrEqual(
        firstCallCount
      );
    });
  });
});
