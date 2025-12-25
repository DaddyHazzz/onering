import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import EnforcementBadge from "@/components/EnforcementBadge";

describe("EnforcementBadge", () => {
  it("renders mode, QA status, and copy buttons", () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn() },
    });

    render(
      <EnforcementBadge
        enforcement={{
          request_id: "req-1",
          mode: "enforced",
          receipt: { receipt_id: "rcpt-1" },
          qa_summary: { status: "PASS" },
        }}
      />
    );

    expect(screen.getByText(/Enforcement: ENFORCED/i)).toBeInTheDocument();
    expect(screen.getByText(/QA: PASS/i)).toBeInTheDocument();
    expect(screen.getByTestId("copy-request-id")).toBeInTheDocument();
    expect(screen.getByTestId("copy-receipt-id")).toBeInTheDocument();
  });
});
