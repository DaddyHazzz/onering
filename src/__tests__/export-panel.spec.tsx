/**
 * Tests for ExportPanel component (Phase 8.3)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ExportPanel from "@/components/ExportPanel";
import * as collabApi from "@/lib/collabApi";

// Mock the API
vi.mock("@/lib/collabApi");

// Mock URL.createObjectURL and revokeObjectURL
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
global.URL.revokeObjectURL = vi.fn();

describe("ExportPanel", () => {
  const mockAttribution = {
    draft_id: "draft1",
    contributors: [
      {
        user_id: "user123456",
        segment_count: 3,
        segment_ids: ["seg1", "seg2", "seg3"],
        first_ts: "2024-01-01T00:00:00Z",
        last_ts: "2024-01-03T00:00:00Z",
      },
      {
        user_id: "user789012",
        segment_count: 2,
        segment_ids: ["seg4", "seg5"],
        first_ts: "2024-01-02T00:00:00Z",
        last_ts: "2024-01-04T00:00:00Z",
      },
    ],
  };

  const mockExportResponse = {
    draft_id: "draft1",
    format: "markdown",
    filename: "draft_draft1.md",
    content_type: "text/markdown",
    content: "# Test Draft\n\nContent here",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset DOM
    document.body.innerHTML = "";
  });

  it("renders sign-in message when not authenticated", () => {
    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={false}
      />
    );

    expect(screen.getByText(/sign in to export/i)).toBeInTheDocument();
  });

  it("loads and displays top contributors", async () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/top contributors/i)).toBeInTheDocument();
    });

    // Check contributors displayed (showing last 6 chars of user_id)
    expect(screen.getByText(/@123456/)).toBeInTheDocument();
    expect(screen.getByText(/3 segments/)).toBeInTheDocument();
    expect(screen.getByText(/@789012/)).toBeInTheDocument();
    expect(screen.getByText(/2 segments/)).toBeInTheDocument();
  });

  it("displays export buttons", () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    expect(screen.getByText(/export as markdown/i)).toBeInTheDocument();
    expect(screen.getByText(/export as json/i)).toBeInTheDocument();
  });

  it("has include credits checkbox", () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    const checkbox = screen.getByRole("checkbox", { name: /include credits/i });
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).toBeChecked(); // Default true
  });

  it("toggles include credits checkbox", () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    const checkbox = screen.getByRole("checkbox", { name: /include credits/i });
    expect(checkbox).toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
  });

  it("exports markdown when markdown button clicked", async () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);
    vi.mocked(collabApi.exportDraft).mockResolvedValue(mockExportResponse);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    const mdButton = screen.getByText(/export as markdown/i);
    fireEvent.click(mdButton);

    await waitFor(() => {
      expect(collabApi.exportDraft).toHaveBeenCalledWith("draft1", {
        format: "markdown",
        include_credits: true,
      });
    });

    // Check file download was triggered
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("exports JSON when JSON button clicked", async () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);
    vi.mocked(collabApi.exportDraft).mockResolvedValue({
      ...mockExportResponse,
      format: "json",
      filename: "draft_draft1.json",
      content_type: "application/json",
      content: '{"draft_id":"draft1"}',
    });

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    const jsonButton = screen.getByText(/export as json/i);
    fireEvent.click(jsonButton);

    await waitFor(() => {
      expect(collabApi.exportDraft).toHaveBeenCalledWith("draft1", {
        format: "json",
        include_credits: true,
      });
    });

    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("respects include_credits checkbox in export request", async () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);
    vi.mocked(collabApi.exportDraft).mockResolvedValue(mockExportResponse);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    // Uncheck credits
    const checkbox = screen.getByRole("checkbox", { name: /include credits/i });
    fireEvent.click(checkbox);

    const mdButton = screen.getByText(/export as markdown/i);
    fireEvent.click(mdButton);

    await waitFor(() => {
      expect(collabApi.exportDraft).toHaveBeenCalledWith("draft1", {
        format: "markdown",
        include_credits: false,
      });
    });
  });

  it("shows loading state during export", async () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);
    vi.mocked(collabApi.exportDraft).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    const mdButton = screen.getByText(/export as markdown/i);
    fireEvent.click(mdButton);

    await waitFor(() => {
      expect(screen.getByText(/exporting/i)).toBeInTheDocument();
    });

    // Buttons should be disabled
    expect(mdButton).toBeDisabled();
  });

  it("calls onError callback when export fails", async () => {
    const onError = vi.fn();
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);
    vi.mocked(collabApi.exportDraft).mockRejectedValue(new Error("Export failed"));

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
        onError={onError}
      />
    );

    const mdButton = screen.getByText(/export as markdown/i);
    fireEvent.click(mdButton);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("Export failed");
    });
  });

  it("triggers file download with correct filename", async () => {
    vi.mocked(collabApi.getAttribution).mockResolvedValue(mockAttribution);
    vi.mocked(collabApi.exportDraft).mockResolvedValue(mockExportResponse);

    // Mock document.createElement and appendChild/removeChild
    const mockLink = {
      href: "",
      download: "",
      click: vi.fn(),
    };
    const originalCreateElement = document.createElement.bind(document);
    const originalAppendChild = document.body.appendChild.bind(document.body);
    const originalRemoveChild = document.body.removeChild.bind(document.body);

    const createElementSpy = vi
      .spyOn(document, "createElement")
      .mockImplementation(((tagName: any) => {
        return tagName === "a" ? (mockLink as any) : originalCreateElement(tagName);
      }) as any);

    const appendChildSpy = vi
      .spyOn(document.body, "appendChild")
      .mockImplementation(((node: any) => {
        if (node === (mockLink as any)) return node as any;
        return originalAppendChild(node);
      }) as any);

    const removeChildSpy = vi
      .spyOn(document.body, "removeChild")
      .mockImplementation(((node: any) => {
        if (node === (mockLink as any)) return node as any;
        return originalRemoveChild(node);
      }) as any);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    const mdButton = screen.getByText(/export as markdown/i);
    fireEvent.click(mdButton);

    await waitFor(() => {
      expect(mockLink.download).toBe("draft_draft1.md");
      expect(mockLink.click).toHaveBeenCalled();
    });

    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalled();

    createElementSpy.mockRestore();
    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
  });

  it("shows only top 3 contributors in summary", async () => {
    const manyContributors = {
      draft_id: "draft1",
      contributors: [
        { user_id: "user1", segment_count: 5, segment_ids: [], first_ts: "2024-01-01T00:00:00Z", last_ts: "2024-01-01T00:00:00Z" },
        { user_id: "user2", segment_count: 4, segment_ids: [], first_ts: "2024-01-01T00:00:00Z", last_ts: "2024-01-01T00:00:00Z" },
        { user_id: "user3", segment_count: 3, segment_ids: [], first_ts: "2024-01-01T00:00:00Z", last_ts: "2024-01-01T00:00:00Z" },
        { user_id: "user4", segment_count: 2, segment_ids: [], first_ts: "2024-01-01T00:00:00Z", last_ts: "2024-01-01T00:00:00Z" },
      ],
    };

    vi.mocked(collabApi.getAttribution).mockResolvedValue(manyContributors);

    render(
      <ExportPanel
        draftId="draft1"
        isAuthenticated={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/top contributors/i)).toBeInTheDocument();
    });

    // Should show user1, user2, user3 but not user4
    expect(screen.getByText(/@user1/)).toBeInTheDocument();
    expect(screen.getByText(/@user2/)).toBeInTheDocument();
    expect(screen.getByText(/@user3/)).toBeInTheDocument();
    expect(screen.queryByText(/@user4/)).not.toBeInTheDocument();
  });
});
