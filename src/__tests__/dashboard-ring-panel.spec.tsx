import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Dashboard from "@/app/dashboard/page";

vi.mock("@clerk/nextjs", () => ({
  useUser: () => ({ user: { id: "user-1", publicMetadata: {} }, isLoaded: true }),
  UserButton: () => <div data-testid="user-button" />,
}));

vi.mock("@stripe/stripe-js", () => ({
  loadStripe: () => Promise.resolve(null),
}));

describe("Dashboard RING ledger panel", () => {
  beforeEach(() => {
    global.alert = vi.fn();
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/tokens/summary")) {
        return {
          ok: true,
          json: async () => ({
            balance: 42,
            pending_total: 7,
            effective_balance: 49,
            last_ledger_at: "2025-12-26T00:00:00Z",
            last_pending_at: "2025-12-26T00:00:00Z",
          }),
        } as any;
      }
      if (url.includes("/api/tokens/ledger")) {
        return {
          ok: true,
          json: async () => ({
            entries: [
              {
                id: "l1",
                eventType: "EARN",
                reasonCode: "publish_success",
                amount: 10,
                balanceAfter: 42,
                createdAt: "2025-12-26T00:00:00Z",
              },
            ],
          }),
        } as any;
      }
      if (url.includes("/api/streaks/current")) {
        return { ok: true, json: async () => null } as any;
      }
      if (url.includes("/api/challenges/today")) {
        return { ok: true, json: async () => null } as any;
      }
      if (url.includes("/api/family/list")) {
        return { ok: true, json: async () => ({ familyMembers: [], combinedRingBalance: 0 }) } as any;
      }
      if (url.includes("/api/ring/daily-login")) {
        return { ok: true, json: async () => ({ success: false }) } as any;
      }
      if (url.includes("/api/monitoring/stats")) {
        return { ok: true, json: async () => ({}) } as any;
      }
      return { ok: true, json: async () => ({}) } as any;
    });
  });

  it("renders balance, pending, and ledger entries", async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText("RING Ledger")).toBeInTheDocument();
    });

    expect(screen.getByText("Balance:")).toBeInTheDocument();
    expect(screen.getAllByText("42").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Pending:")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("Effective:")).toBeInTheDocument();
    expect(screen.getByText("49")).toBeInTheDocument();
    expect(screen.getByText("publish_success")).toBeInTheDocument();
  });
});
