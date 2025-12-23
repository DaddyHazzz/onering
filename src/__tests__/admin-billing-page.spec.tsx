import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AdminBillingPage from "../app/admin/billing/page";

describe("AdminBillingPage", () => {
  it("renders input and buttons", () => {
    render(<AdminBillingPage />);
    expect(screen.getByText(/Admin Billing/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/Enter admin key/i)).toBeDefined();
    expect(screen.getByText(/List Retries/i)).toBeDefined();
    expect(screen.getByText(/List Subscriptions/i)).toBeDefined();
  });
});
