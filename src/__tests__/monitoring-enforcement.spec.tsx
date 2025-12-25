import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import MonitoringPage from "@/app/monitoring/page";

const pushMock = vi.fn();

vi.mock("@clerk/nextjs", () => ({
  useUser: () => ({ user: { id: "user-1" }, isLoaded: true }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe("MonitoringPage enforcement panel", () => {
  const statsResponse = {
    activeUsers: 10,
    totalRingCirculated: 5000,
    postSuccessRate: 0.9,
    totalPostsPublished: 100,
    totalPostsFailed: 5,
    avgPostEarnings: 12.5,
  };

  const recentResponse = {
    items: [
      {
        request_id: "req-1",
        receipt_id: "rec-1",
        mode: "advisory",
        qa_status: "PASS",
        audit_ok: true,
        violation_codes_count: 0,
        created_at: "2025-12-26T00:00:00Z",
        expires_at: "2025-12-26T01:00:00Z",
      },
      {
        request_id: "req-2",
        receipt_id: "rec-2",
        mode: "enforced",
        qa_status: "FAIL",
        audit_ok: false,
        violation_codes_count: 2,
        created_at: "2025-12-26T02:00:00Z",
        expires_at: "2025-12-26T03:00:00Z",
        last_error_code: "QA_BLOCKED",
        last_error_at: "2025-12-26T02:05:00Z",
      },
    ],
  };

  const metricsResponse = {
    window_hours: 24,
    metrics: {
      qa_blocked: 1,
      enforcement_receipt_required: 2,
      enforcement_receipt_expired: 1,
      audit_write_failed: 3,
      policy_error: 4,
      p90_latency_ms: 1200,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/monitoring/stats")) {
        return {
          ok: true,
          json: async () => statsResponse,
        } as any;
      }
      if (url.includes("/api/monitoring/enforcement/recent")) {
        return {
          ok: true,
          json: async () => recentResponse,
        } as any;
      }
      if (url.includes("/api/monitoring/enforcement/metrics")) {
        return {
          ok: true,
          json: async () => metricsResponse,
        } as any;
      }
      return { ok: false, json: async () => ({}) } as any;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders enforcement counters and rows", async () => {
    render(<MonitoringPage />);

    await waitFor(() => expect(screen.getByText("Enforcement Monitoring")).toBeInTheDocument());

    const qaCard = screen.getByText("QA_BLOCKED (24h)").parentElement as HTMLElement;
    expect(within(qaCard).getByText("1")).toBeInTheDocument();
    const receiptCard = screen.getByText("RECEIPT_REQUIRED (24h)").parentElement as HTMLElement;
    expect(within(receiptCard).getByText("2")).toBeInTheDocument();

    expect(await screen.findByText("req-1")).toBeInTheDocument();
    expect(await screen.findByText("req-2")).toBeInTheDocument();
    expect(screen.getAllByTestId("copy-request-id").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByTestId("copy-receipt-id").length).toBeGreaterThanOrEqual(2);
  });

  it("filters by status, mode, and request id", async () => {
    render(<MonitoringPage />);

    await waitFor(() => expect(screen.getByText("Enforcement Monitoring")).toBeInTheDocument());

    const statusSelect = screen.getByTestId("filter-status");
    const modeSelect = screen.getByTestId("filter-mode");
    const searchInput = screen.getByTestId("search-request-id");

    fireEvent.change(statusSelect, { target: { value: "fail" } });
    fireEvent.change(modeSelect, { target: { value: "enforced" } });
    fireEvent.change(searchInput, { target: { value: "req-2" } });

    await waitFor(() => {
      expect(screen.getByText("req-2")).toBeInTheDocument();
      expect(screen.queryByText("req-1")).not.toBeInTheDocument();
    });
  });
});
