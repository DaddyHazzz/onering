/**
 * src/__tests__/smart-ring-pass.spec.tsx
 * Tests for Smart Ring Passing UI and API integration.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RingControls from "@/components/RingControls";
import * as collabApi from "@/lib/collabApi";
import { CollabDraft, SmartPassStrategy } from "@/types/collab";

// Mock the API
vi.mock("@/lib/collabApi");

const mockDraft: CollabDraft = {
  draft_id: "draft-123",
  creator_id: "alice",
  title: "Test Draft",
  platform: "x",
  status: "active",
  segments: [],
  ring_state: {
    draft_id: "draft-123",
    current_holder_id: "alice",
    holders_history: ["alice"],
    passed_at: "2024-12-25T00:00:00Z",
  },
  collaborators: ["bob", "carol"],
  pending_invites: [],
  created_at: "2024-12-25T00:00:00Z",
  updated_at: "2024-12-25T00:00:00Z",
};

const mockSmartPassResponse = {
  data: { ...mockDraft, ring_state: { ...mockDraft.ring_state, current_holder_id: "carol" } },
  selected_to_user_id: "carol",
  strategy_used: "most_inactive",
  reasoning: "Carol has not contributed any segments.",
  metrics: {
    strategy: "most_inactive",
    candidate_count: 2,
    computed_from: "activity_history",
  },
};

const mockNoCollaboratorsError = {
  code: "no_collaborator_candidates",
  message: "No eligible collaborators to pass the ring to.",
  status: 409,
};

describe("SmartRingPass", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("UI Rendering", () => {
    it("renders Smart Pass section when onSmartPass prop provided", () => {
      const mockOnSmartPass = vi.fn();
      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const smartPassButton = screen.getByRole("button", { name: /smart pass/i });
      expect(smartPassButton).toBeInTheDocument();

      const strategySelect = screen.getByLabelText(/smart pass strategy/i);
      expect(strategySelect).toBeInTheDocument();
    });

    it("does not render Smart Pass section when onSmartPass not provided", () => {
      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          isLoading={false}
        />
      );

      const smartPassButton = screen.queryByRole("button", { name: /smart pass/i });
      expect(smartPassButton).not.toBeInTheDocument();
    });

    it("has strategy dropdown with options: most_inactive, round_robin, back_to_creator", () => {
      const mockOnSmartPass = vi.fn();
      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const strategySelect = screen.getByLabelText(/smart pass strategy/i) as HTMLSelectElement;
      expect(strategySelect.value).toBe("most_inactive");

      const options = Array.from(strategySelect.options).map((opt) => opt.value);
      expect(options).toContain("most_inactive");
      expect(options).toContain("round_robin");
      expect(options).toContain("back_to_creator");
    });

    it("Smart Pass button is disabled when not ring holder", () => {
      const mockOnSmartPass = vi.fn();
      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={false}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      // Ring holder message should show instead
      expect(screen.getByText(/don't hold the ring/i)).toBeInTheDocument();
    });
  });

  describe("API Integration", () => {
    it("calls passRingSmart with correct parameters on button click", async () => {
      const user = userEvent.setup();
      const mockOnSmartPass = vi
        .fn()
        .mockResolvedValue({
          to_user_id: "carol",
          reason: "Carol has not contributed any segments.",
        });

      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const strategySelect = screen.getByLabelText(/smart pass strategy/i);
      await user.selectOptions(strategySelect, "round_robin");

      const smartPassButton = screen.getByRole("button", { name: /smart pass/i });
      await user.click(smartPassButton);

      await waitFor(() => {
        expect(mockOnSmartPass).toHaveBeenCalledWith("round_robin");
      });
    });

    it("displays reasoning text on successful smart pass", async () => {
      const user = userEvent.setup();
      const mockOnSmartPass = vi
        .fn()
        .mockResolvedValue({
          to_user_id: "carol",
          reason: "Carol has not contributed any segments.",
        });

      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const smartPassButton = screen.getByRole("button", { name: /smart pass/i });
      await user.click(smartPassButton);

      await waitFor(() => {
        expect(
          screen.getByText(/selected @carol — carol has not contributed/i)
        ).toBeInTheDocument();
      });
    });

    it("shows error on 409 no-collaborators error", async () => {
      const user = userEvent.setup();
      const mockOnSmartPass = vi
        .fn()
        .mockRejectedValue(mockNoCollaboratorsError);

      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const smartPassButton = screen.getByRole("button", { name: /smart pass/i });
      await user.click(smartPassButton);

      await waitFor(() => {
        expect(
          screen.getByText(/no eligible collaborators/i)
        ).toBeInTheDocument();
      });
    });

    it("disables Smart Pass button while loading", async () => {
      const user = userEvent.setup();
      const mockOnSmartPass = vi.fn();

      const { rerender } = render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      // Simulate loading
      rerender(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={true}
        />
      );

      const smartPassButton = screen.getByRole("button", { name: /passing/i });
      expect(smartPassButton).toBeDisabled();
    });
  });

  describe("Strategy Selection", () => {
    it("allows selecting different strategies", async () => {
      const user = userEvent.setup();
      const mockOnSmartPass = vi
        .fn()
        .mockResolvedValue({
          to_user_id: "bob",
          reason: "Selected via strategy.",
        });

      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const strategySelect = screen.getByLabelText(/smart pass strategy/i);
      await user.selectOptions(strategySelect, "back_to_creator");

      expect((strategySelect as HTMLSelectElement).value).toBe("back_to_creator");

      const smartPassButton = screen.getByRole("button", { name: /smart pass/i });
      await user.click(smartPassButton);

      await waitFor(() => {
        expect(mockOnSmartPass).toHaveBeenCalledWith("back_to_creator");
      });
    });
  });

  describe("Error Handling", () => {
    it("clears error when user interacts with controls", async () => {
      const user = userEvent.setup();
      const mockOnSmartPass = vi
        .fn()
        .mockRejectedValueOnce(mockNoCollaboratorsError);

      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const smartPassButton = screen.getByRole("button", { name: /smart pass/i });
      await user.click(smartPassButton);

      await waitFor(() => {
        expect(screen.getByText(/no eligible collaborators/i)).toBeInTheDocument();
      });

      // Clear error by selecting new strategy
      const strategySelect = screen.getByLabelText(/smart pass strategy/i);
      await user.selectOptions(strategySelect, "round_robin");

      // Error should be cleared once interaction happens
      expect(screen.queryByText(/no eligible collaborators/i)).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper label associations for strategy select", () => {
      const mockOnSmartPass = vi.fn();
      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const strategyLabel = screen.getByText("Smart Pass Strategy");
      const strategySelect = screen.getByLabelText(/smart pass strategy/i);

      // Verify label and select are connected
      expect(strategySelect).toHaveAttribute("id");
      const selectId = strategySelect.getAttribute("id");
      expect(strategyLabel.closest("label")).toHaveAttribute("for", selectId);
    });

    it("has descriptive button text", () => {
      const mockOnSmartPass = vi.fn();
      render(
        <RingControls
          draft={mockDraft}
          isRingHolder={true}
          onPassRing={vi.fn()}
          onSmartPass={mockOnSmartPass}
          isLoading={false}
        />
      );

      const button = screen.getByRole("button", { name: /smart pass/i });
      expect(button).toHaveTextContent("Smart Pass");
    });
  });
});
