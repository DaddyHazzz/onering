/**
 * Frontend tests for PlatformVersionsPanel component (Phase 8.2).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PlatformVersionsPanel from "@/components/PlatformVersionsPanel";
import * as collabApi from "@/lib/collabApi";

// Mock the API client
vi.mock("@/lib/collabApi");

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

describe("PlatformVersionsPanel", () => {
  const mockFormatResponse = {
    draft_id: "draft-123",
    outputs: {
      x: {
        platform: "x",
        blocks: [
          { type: "text", text: "Tweet text here" },
          { type: "hashtag", text: "#growth" },
          { type: "cta", text: "Join now" },
        ],
        plain_text: "Tweet text here\n---\n#growth\n---\nJoin now",
        character_count: 45,
        block_count: 3,
        warnings: [],
      },
      youtube: {
        platform: "youtube",
        blocks: [
          { type: "heading", text: "## Video Title" },
          { type: "text", text: "Full description here" },
        ],
        plain_text: "## Video Title\n\nFull description here",
        character_count: 42,
        block_count: 2,
        warnings: [],
      },
      instagram: {
        platform: "instagram",
        blocks: [
          { type: "text", text: "Caption text" },
          { type: "cta", text: "→ Follow for more" },
        ],
        plain_text: "Caption text\n\n→ Follow for more",
        character_count: 33,
        block_count: 2,
        warnings: [],
      },
      blog: {
        platform: "blog",
        blocks: [
          { type: "heading", text: "## Blog Post Title" },
          { type: "text", text: "Long form content" },
        ],
        plain_text: "## Blog Post Title\n\nLong form content",
        character_count: 38,
        block_count: 2,
        warnings: [],
      },
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (collabApi.formatGenerate as any).mockResolvedValue(mockFormatResponse);
  });

  describe("Rendering", () => {
    it("should render the panel with title and generate button", () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      expect(screen.getByText("Platform Versions")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Generate All Platforms/i })).toBeInTheDocument();
    });

    it("should show empty state when no results", () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      expect(screen.getByText(/Click "Generate All Platforms"/)).toBeInTheDocument();
    });

    it("should show options toggle button", () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      const toggleButton = screen.getByText("Show Formatting Options");
      expect(toggleButton).toBeInTheDocument();
    });
  });

  describe("Generation", () => {
    it("should call formatGenerate API when button clicked", async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      const generateButton = screen.getByRole("button", { name: /Generate All Platforms/i });
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(collabApi.formatGenerate).toHaveBeenCalledWith({
          draft_id: "draft-123",
          platforms: undefined,
          options: undefined,
        });
      });
    });

    it("should display results after generation", async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(screen.getByText("X (Twitter)")).toBeInTheDocument();
        expect(screen.getByText("Youtube")).toBeInTheDocument();
        expect(screen.getByText("Instagram")).toBeInTheDocument();
        expect(screen.getByText("Blog")).toBeInTheDocument();
      });
    });

    it("should show loading state during generation", async () => {
      (collabApi.formatGenerate as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockFormatResponse), 100))
      );

      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      expect(screen.getByRole("button", { name: /Generating/i })).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /Generate All Platforms/i })).toBeInTheDocument();
      });
    });

    it("should handle API errors gracefully", async () => {
      const errorCallback = vi.fn();
      (collabApi.formatGenerate as any).mockRejectedValue(
        new Error("API error")
      );

      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
          onError={errorCallback}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(errorCallback).toHaveBeenCalledWith(expect.stringContaining("API error"));
      });
    });

    it("should require authentication", async () => {
      const errorCallback = vi.fn();

      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={false}
          onError={errorCallback}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      expect(errorCallback).toHaveBeenCalledWith(expect.stringContaining("must be signed in"));
      expect(collabApi.formatGenerate).not.toHaveBeenCalled();
    });
  });

  describe("Platform Tabs", () => {
    beforeEach(async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(screen.getByText("X (Twitter)")).toBeInTheDocument();
      });
    });

    it("should display X platform by default", () => {
      expect(screen.getByText("Tweet text here")).toBeInTheDocument();
      expect(screen.getByText("#growth")).toBeInTheDocument();
    });

    it("should switch tabs when clicked", async () => {
      const youtubeTab = screen.getByRole("button", { name: "Youtube" });
      fireEvent.click(youtubeTab);

      await waitFor(() => {
        expect(screen.getByText("## Video Title")).toBeInTheDocument();
        expect(screen.getByText("Full description here")).toBeInTheDocument();
      });
    });

    it("should display correct metadata for selected platform", async () => {
      fireEvent.click(screen.getByRole("button", { name: "Youtube" }));

      await waitFor(() => {
        expect(screen.getByText("2 blocks")).toBeInTheDocument();
        expect(screen.getByText("42 characters")).toBeInTheDocument();
      });
    });
  });

  describe("Formatting Options", () => {
    it("should toggle options panel visibility", async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      let toggleButton = screen.getByText("Show Formatting Options");
      fireEvent.click(toggleButton);

      expect(screen.getByText("Hide Formatting Options")).toBeInTheDocument();
      expect(screen.getByLabelText("Tone")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Hide Formatting Options"));
      expect(screen.getByText("Show Formatting Options")).toBeInTheDocument();
    });

    it("should apply tone selection to API call", async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByText("Show Formatting Options"));

      const toneSelect = screen.getByDisplayValue("");
      fireEvent.change(toneSelect, { target: { value: "professional" } });

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(collabApi.formatGenerate).toHaveBeenCalledWith({
          draft_id: "draft-123",
          platforms: undefined,
          options: { tone: "professional", include_hashtags: true, include_cta: true },
        });
      });
    });

    it("should handle hashtag and CTA toggles", async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByText("Show Formatting Options"));

      const hashtagCheckbox = screen.getByRole("checkbox", { name: /Include Hashtags/i });
      fireEvent.click(hashtagCheckbox);

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(collabApi.formatGenerate).toHaveBeenCalledWith({
          draft_id: "draft-123",
          platforms: undefined,
          options: {
            tone: undefined,
            include_hashtags: false,
            include_cta: true,
          },
        });
      });
    });

    it("should apply custom CTA text", async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByText("Show Formatting Options"));

      const ctaInput = screen.getByPlaceholderText("e.g., Join my community");
      fireEvent.change(ctaInput, { target: { value: "Subscribe now" } });

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(collabApi.formatGenerate).toHaveBeenCalledWith({
          draft_id: "draft-123",
          platforms: undefined,
          options: {
            tone: undefined,
            include_hashtags: true,
            include_cta: true,
            cta_text: "Subscribe now",
          },
        });
      });
    });
  });

  describe("Block Rendering", () => {
    beforeEach(async () => {
      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(screen.getByText("Tweet text here")).toBeInTheDocument();
      });
    });

    it("should render all block types with correct styling", () => {
      expect(screen.getByText("TEXT")).toBeInTheDocument();
      expect(screen.getByText("HASHTAG")).toBeInTheDocument();
      expect(screen.getByText("CTA")).toBeInTheDocument();
    });

    it("should show copy button for each block", () => {
      const copyButtons = screen.getAllByText("Copy");
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it("should copy block text to clipboard", async () => {
      const copyButtons = screen.getAllByText("Copy");
      fireEvent.click(copyButtons[0]);

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith("Tweet text here");
      });

      expect(screen.getByText("✓")).toBeInTheDocument();
    });
  });

  describe("Export Functionality", () => {
    beforeEach(async () => {
      // Mock blob and URL creation
      global.URL.createObjectURL = vi.fn(() => "blob:mock");
      global.URL.revokeObjectURL = vi.fn();

      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(screen.getByText("Tweet text here")).toBeInTheDocument();
      });
    });

    it("should have export buttons", () => {
      expect(screen.getByRole("button", { name: "Export TXT" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Export MD" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Export CSV" })).toBeInTheDocument();
    });

    it("should export TXT format", () => {
      const txt Button = screen.getByRole("button", { name: "Export TXT" });
      fireEvent.click(txtButton);

      // Verify export was initiated (would need to check if file download was triggered)
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  describe("Warnings Display", () => {
    it("should display warnings if present", async () => {
      const responseWithWarnings = {
        ...mockFormatResponse,
        outputs: {
          ...mockFormatResponse.outputs,
          x: {
            ...mockFormatResponse.outputs.x,
            warnings: ["Text too long for platform"],
          },
        },
      };

      (collabApi.formatGenerate as any).mockResolvedValue(responseWithWarnings);

      render(
        <PlatformVersionsPanel
          draftId="draft-123"
          isAuthenticated={true}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /Generate All Platforms/i }));

      await waitFor(() => {
        expect(screen.getByText("Warnings:")).toBeInTheDocument();
        expect(screen.getByText("Text too long for platform")).toBeInTheDocument();
      });
    });
  });
});
