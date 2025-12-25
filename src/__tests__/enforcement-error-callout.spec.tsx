import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import EnforcementErrorCallout from "@/components/EnforcementErrorCallout";

describe("EnforcementErrorCallout", () => {
  it("renders suggested fix", () => {
    render(<EnforcementErrorCallout message="Post failed" suggestedFix="Regenerate content" />);
    expect(screen.getByText(/Post failed/)).toBeInTheDocument();
    expect(screen.getByText(/Suggested fix:/)).toBeInTheDocument();
    expect(screen.getByText(/Regenerate content/)).toBeInTheDocument();
  });
});
