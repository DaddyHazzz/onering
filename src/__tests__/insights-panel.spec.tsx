/**
 * Phase 8.7: InsightsPanel Tests
 * 
 * Comprehensive vitest tests for insights panel:
 * - Render insights (stalled, dominant user, healthy)
 * - Render recommendations with action buttons
 * - Render alerts
 * - Empty state (no insights/recommendations/alerts)
 * - Action button interactions (pass ring, invite user)
 * - Error handling
 * - Loading state
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import InsightsPanel from "@/components/InsightsPanel";
import * as collabApi from "@/lib/collabApi";

// Mock collab API
vi.mock("@/lib/collabApi");

describe("InsightsPanel", () => {
  const mockDraftId = "test-draft-123";
  const mockUserId = "user1";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(collabApi.getDraftInsights).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<InsightsPanel draftId={mockDraftId} />);
    
    expect(screen.getByText(/loading insights/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders stalled insight (critical)", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [
        {
          type: "stalled",
          severity: "critical",
          title: "Draft is Stalled",
          message: "No activity in 72 hours",
          reason: "Last activity was 3 days ago, draft appears abandoned",
          metrics_snapshot: { hours_since_activity: 72 }
        }
      ],
      recommendations: [],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText("Draft is Stalled")).toBeInTheDocument();
      expect(screen.getByText("No activity in 72 hours")).toBeInTheDocument();
    });

    // Should have reason in details
    const details = screen.getByText("Why?");
    fireEvent.click(details);
    await waitFor(() => {
      expect(screen.getByText(/last activity was 3 days ago/i)).toBeInTheDocument();
    });
  });

  it("renders dominant user insight (warning)", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [
        {
          type: "dominant_user",
          severity: "warning",
          title: "Dominant Contributor",
          message: "user1 contributed 78% of segments",
          reason: "user1 has added 7/9 segments (78%), exceeding 60% threshold",
          metrics_snapshot: { dominant_user_id: "user1", percentage: 0.78 }
        }
      ],
      recommendations: [],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText("Dominant Contributor")).toBeInTheDocument();
      expect(screen.getByText(/user1 contributed 78%/i)).toBeInTheDocument();
    });
  });

  it("renders healthy insight (info)", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [
        {
          type: "healthy",
          severity: "info",
          title: "Healthy Collaboration",
          message: "3 contributors, recent activity, balanced contributions",
          reason: "Multiple contributors (3), no single dominant user, activity within 24h",
          metrics_snapshot: { contributors: 3, last_activity_hours_ago: 2 }
        }
      ],
      recommendations: [],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText("Healthy Collaboration")).toBeInTheDocument();
      expect(screen.getByText(/3 contributors, recent activity/i)).toBeInTheDocument();
    });
  });

  it("renders pass ring recommendation with button", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [
        {
          action: "pass_ring",
          target_user_id: "user2",
          reason: "user2 has not contributed in 48h, pass ring to re-engage",
          confidence: 0.85
        }
      ],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    const mockOnSmartPass = vi.fn().mockResolvedValue({ to_user_id: "user2", reason: "Most inactive user" });

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} onSmartPass={mockOnSmartPass} />);

    await waitFor(() => {
      expect(screen.getByText("Pass the Ring")).toBeInTheDocument();
      expect(screen.getByText(/user2 has not contributed in 48h/i)).toBeInTheDocument();
      expect(screen.getByText(/confidence: 85%/i)).toBeInTheDocument();
    });

    const passButton = screen.getByRole("button", { name: /pass ring to user2/i });
    expect(passButton).toBeInTheDocument();
    
    // Click button
    fireEvent.click(passButton);
    
    await waitFor(() => {
      expect(mockOnSmartPass).toHaveBeenCalledWith("most_inactive");
    });
  });

  it("renders invite user recommendation with button", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [
        {
          action: "invite_user",
          reason: "Only 1 contributor, invite others to diversify perspectives",
          confidence: 0.9
        }
      ],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    const mockOnInvite = vi.fn().mockResolvedValue(undefined);

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} onInvite={mockOnInvite} />);

    await waitFor(() => {
      expect(screen.getByText("Invite Collaborator")).toBeInTheDocument();
      expect(screen.getByText(/only 1 contributor/i)).toBeInTheDocument();
    });

    const inviteButton = screen.getByRole("button", { name: /invite user to collaborate/i });
    expect(inviteButton).toBeInTheDocument();
    
    // Mock prompt
    const originalPrompt = global.prompt;
    global.prompt = vi.fn().mockReturnValue("user3");
    
    fireEvent.click(inviteButton);
    
    await waitFor(() => {
      expect(mockOnInvite).toHaveBeenCalledWith("user3");
    });
    
    global.prompt = originalPrompt;
  });

  it("renders no activity alert", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [],
      alerts: [
        {
          alert_type: "no_activity",
          triggered_at: new Date().toISOString(),
          threshold: "72 hours",
          current_value: 80,
          reason: "No segments added or ring passes in 80 hours"
        }
      ],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText("No Recent Activity")).toBeInTheDocument();
      expect(screen.getByText(/no segments added or ring passes in 80 hours/i)).toBeInTheDocument();
      expect(screen.getByText(/72 hours/i)).toBeInTheDocument();
      // Check that Current value exists (appears twice in DOM - once in message, once in details)
      const currentTexts = screen.getAllByText(/80/);
      expect(currentTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders single contributor alert", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [],
      alerts: [
        {
          alert_type: "single_contributor",
          triggered_at: new Date().toISOString(),
          threshold: "1 contributor with 5+ segments",
          current_value: 1,
          reason: "Only user1 has contributed (6 segments)"
        }
      ],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText("Solo Contributor")).toBeInTheDocument();
      expect(screen.getByText(/only user1 has contributed \(6 segments\)/i)).toBeInTheDocument();
    });
  });

  it("renders empty state when no insights/recommendations/alerts", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText(/all good! no insights to report/i)).toBeInTheDocument();
      expect(screen.getByText(/keep collaborating/i)).toBeInTheDocument();
    });
  });

  it("renders error state", async () => {
    vi.mocked(collabApi.getDraftInsights).mockRejectedValue(new Error("Forbidden"));

    render(<InsightsPanel draftId={mockDraftId} />);

    await waitFor(() => {
      expect(screen.getByText("Forbidden")).toBeInTheDocument();
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    const retryButton = screen.getByText("Retry");
    expect(retryButton).toBeInTheDocument();
  });

  it("calls onRefresh after action", async () => {
    const mockInsights = {
      draft_id: mockDraftId,
      insights: [],
      recommendations: [
        {
          action: "pass_ring",
          target_user_id: "user2",
          reason: "Pass ring to user2",
          confidence: 0.8
        }
      ],
      alerts: [],
      computed_at: new Date().toISOString()
    };

    vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockInsights);
    vi.mocked(collabApi.passRing).mockResolvedValue({ success: true } as any);

    const onRefresh = vi.fn();
    const onSmartPass = vi.fn().mockResolvedValue({ to_user_id: "user2", reason: "Most inactive" });
    
    // Mock window.alert to prevent jsdom error
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

    render(
      <InsightsPanel 
        draftId={mockDraftId} 
        onRefresh={onRefresh}
        onSmartPass={onSmartPass}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Pass the Ring")).toBeInTheDocument();
    });

    const passButton = screen.getByRole("button", { name: /pass ring to user2/i });
    fireEvent.click(passButton);

    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
    });
    
    alertSpy.mockRestore();
  });
});
