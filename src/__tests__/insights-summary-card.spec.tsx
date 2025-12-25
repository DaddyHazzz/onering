/**
 * Phase 8.9: InsightsSummaryCard Tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { InsightsSummaryCard } from "@/components/InsightsSummaryCard";
import * as collabApi from "@/lib/collabApi";

vi.mock("@/lib/collabApi");

describe("InsightsSummaryCard", () => {
  const mockDraftId = "test-draft-123";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state with skeleton", () => {
    vi.mocked(collabApi.getDraftInsights).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<InsightsSummaryCard draftId={mockDraftId} />);
    
    // Should show skeleton
    const skeleton = document.querySelector("[class*='animate-pulse']");
    expect(skeleton).toBeInTheDocument();
  });

  it("renders highest-severity insight (critical > warning > info)", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [
        {
          type: "healthy",
          severity: "info",
          title: "All Good",
          message: "No issues",
          reason: "Multiple contributors",
          metrics_snapshot: {}
        },
        {
          type: "stalled",
          severity: "critical",
          title: "Draft is Stalled",
          message: "No activity in 72 hours",
          reason: "Time-based threshold",
          metrics_snapshot: {}
        }
      ],
      recommendations: [{ action: "invite_user", reason: "Diversify", confidence: 0.8 }],
      alerts: [{ alert_type: "long_ring_hold", reason: "24h hold", threshold: "24h+", current_value: 48, triggered_at: new Date().toISOString() }],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsSummaryCard draftId={mockDraftId} />);

    await waitFor(() => {
      // Should show highest severity (stalled/critical)
      expect(screen.getByText("Draft is Stalled")).toBeInTheDocument();
      expect(screen.getByText(/1 alert/i)).toBeInTheDocument();
      expect(screen.getByText(/1 rec/i)).toBeInTheDocument();
    });
  });

  it("renders healthy state when no issues", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsSummaryCard draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText(/healthy collaboration|all good/i)).toBeInTheDocument();
    });
  });

  it("renders multiple alerts and recommendations counts", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [
        { action: "pass_ring", target_user_id: "user2", reason: "R1", confidence: 0.8 },
        { action: "invite_user", reason: "R2", confidence: 0.8 }
      ],
      alerts: [
        { alert_type: "no_activity", reason: "A1", threshold: "72h+", current_value: 75, triggered_at: new Date().toISOString() },
        { alert_type: "long_ring_hold", reason: "A2", threshold: "24h+", current_value: 30, triggered_at: new Date().toISOString() },
        { alert_type: "single_contributor", reason: "A3", threshold: "1 contrib+", current_value: 1, triggered_at: new Date().toISOString() }
      ],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsSummaryCard draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText(/3 alerts/i)).toBeInTheDocument();
      expect(screen.getByText(/2 recs/i)).toBeInTheDocument();
    });
  });

  it("renders compact version with minimal UI", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [{ action: "pass_ring", target_user_id: "user2", reason: "R", confidence: 0.8 }],
      alerts: [{ alert_type: "long_ring_hold", reason: "A", threshold: "24h+", current_value: 30, triggered_at: new Date().toISOString() }],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsSummaryCard draftId={mockDraftId} compact={true} />);

    await waitFor(() => {
      expect(screen.getByText(/alert/i)).toBeInTheDocument();
      expect(screen.getByText(/rec/i)).toBeInTheDocument();
    });
  });

  it("silently fails on API error (for list context)", async () => {
    vi.mocked(collabApi.getDraftInsights).mockRejectedValue(new Error("API error"));

    const { container } = render(<InsightsSummaryCard draftId={mockDraftId} />);

    await waitFor(() => {
      // Should render nothing on error (silent fail for list views)
      expect(container.firstChild).toBeNull();
    });
  });
});
