import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AISuggestionsPanel from "../components/AISuggestionsPanel";
import { CollabDraft } from "@/types/collab";
import { aiSuggest } from "@/lib/collabApi";

vi.mock("@/lib/collabApi", () => ({
  aiSuggest: vi.fn(),
}));

const mockDraft: CollabDraft = {
  draft_id: "draft-1",
  creator_id: "user-1",
  title: "Draft Title",
  platform: "x",
  status: "active",
  segments: [
    {
      segment_id: "seg-1",
      draft_id: "draft-1",
      user_id: "user-1",
      content: "First line",
      created_at: new Date().toISOString(),
      segment_order: 0,
    },
  ],
  ring_state: {
    draft_id: "draft-1",
    current_holder_id: "user-1",
    holders_history: ["user-1"],
    passed_at: new Date().toISOString(),
  },
  collaborators: [],
  pending_invites: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const resolvedSuggestion = {
  mode: "next",
  content: "Here is a suggested next line",
  ring_holder: true,
};

describe("AISuggestionsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(aiSuggest).mockResolvedValue(resolvedSuggestion as any);
  });

  it("shows holder actions and allows insert", async () => {
    const onInsertSegment = vi.fn().mockResolvedValue(undefined);

    render(
      <AISuggestionsPanel
        draft={mockDraft}
        isRingHolder={true}
        isAuthenticated={true}
        onInsertSegment={onInsertSegment}
      />
    );

    fireEvent.click(screen.getByText("Suggest Next Segment"));

    await waitFor(() => expect(aiSuggest).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/suggested next line/i)).toBeInTheDocument());

    fireEvent.click(screen.getByText("Insert as Segment"));
    await waitFor(() => expect(onInsertSegment).toHaveBeenCalledWith(resolvedSuggestion.content));
  });

  it("renders commentary-only state for non-holders", () => {
    render(
      <AISuggestionsPanel
        draft={{ ...mockDraft, ring_state: { ...mockDraft.ring_state, current_holder_id: "other" } }}
        isRingHolder={false}
        isAuthenticated={true}
        onInsertSegment={vi.fn()}
      />
    );

    expect(screen.getByText(/When you get the ring/i)).toBeInTheDocument();
    expect(screen.queryByText("Insert as Segment")).not.toBeInTheDocument();
  });

  it("disables controls when unauthenticated", () => {
    render(
      <AISuggestionsPanel
        draft={mockDraft}
        isRingHolder={true}
        isAuthenticated={false}
        onInsertSegment={vi.fn()}
      />
    );

    expect(screen.getByText("Suggest Next Segment")).toBeDisabled();
  });
});
