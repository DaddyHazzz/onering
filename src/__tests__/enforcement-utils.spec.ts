import { describe, it, expect } from "vitest";
import { buildEnforcementRequestFields, normalizeEnforcementPayload, parseSseEvents } from "@/lib/enforcement";

describe("enforcement utils", () => {
  it("parses enforcement SSE events and tokens", () => {
    const payload = JSON.stringify({
      request_id: "req-1",
      mode: "enforced",
      receipt: { receipt_id: "rcpt-1", expires_at: "2025-01-01T00:00:00Z" },
      qa_summary: { status: "PASS", violation_codes: [], required_edits: [] },
    });
    const buffer = `data: hello\n\nevent: enforcement\ndata: ${payload}\n\n`;
    const parsed = parseSseEvents(buffer);
    expect(parsed.events.length).toBe(2);
    expect(parsed.events[0].data.trim()).toBe("hello");
    expect(parsed.events[1].event).toBe("enforcement");
  });

  it("normalizes enforcement payload defaults", () => {
    const normalized = normalizeEnforcementPayload({
      request_id: "req-2",
      mode: "advisory",
      qa_summary: { status: "FAIL" },
    });
    expect(normalized?.qa_summary.status).toBe("FAIL");
    expect(normalized?.qa_summary.violation_codes).toEqual([]);
    expect(normalized?.qa_summary.required_edits).toEqual([]);
  });

  it("builds enforcement request fields from receipt or request id", () => {
    const fields = buildEnforcementRequestFields({
      request_id: "req-3",
      mode: "enforced",
      receipt: { receipt_id: "rcpt-3" },
      qa_summary: { status: "PASS" },
    });
    expect(fields.enforcement_request_id).toBe("req-3");
    expect(fields.enforcement_receipt_id).toBe("rcpt-3");
  });
});
