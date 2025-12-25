import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TokenResultCallout from "@/components/TokenResultCallout";

describe("TokenResultCallout", () => {
  it("renders pending message in shadow mode", () => {
    render(
      <TokenResultCallout
        tokenResult={{ mode: "shadow", pending_amount: 12, reason_code: "PENDING" }}
      />
    );

    expect(screen.getByText("Earned +12 RING (pending)")).toBeInTheDocument();
    expect(screen.getByText("Reason: PENDING")).toBeInTheDocument();
  });

  it("renders issued message in live mode", () => {
    render(
      <TokenResultCallout tokenResult={{ mode: "live", issued_amount: 10, reason_code: "ISSUED" }} />
    );

    expect(screen.getByText("Earned +10 RING")).toBeInTheDocument();
    expect(screen.getByText("Reason: ISSUED")).toBeInTheDocument();
  });
});
