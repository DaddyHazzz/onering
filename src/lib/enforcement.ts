export type EnforcementReceipt = {
  receipt_id: string;
  expires_at?: string | null;
};

export type EnforcementSummary = {
  status: "PASS" | "FAIL";
  violation_codes?: string[];
  required_edits?: string[];
  risk_score?: number;
};

export type EnforcementPayload = {
  request_id?: string | null;
  mode: "off" | "advisory" | "enforced";
  receipt?: EnforcementReceipt | null;
  qa_summary: EnforcementSummary;
  audit_ok?: boolean;
  warnings?: string[];
};

export type SseEvent = {
  event?: string;
  data: string;
};

export function parseSseEvents(buffer: string): { events: SseEvent[]; rest: string } {
  const chunks = buffer.split("\n\n");
  const rest = chunks.pop() ?? "";
  const events: SseEvent[] = [];

  for (const chunk of chunks) {
    if (!chunk.trim()) continue;
    let eventName: string | undefined;
    const dataLines: string[] = [];
    for (const line of chunk.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(6));
      }
    }
    if (dataLines.length) {
      events.push({ event: eventName, data: dataLines.join("\n") });
    }
  }

  return { events, rest };
}

export function normalizeEnforcementPayload(payload: any): EnforcementPayload | null {
  if (!payload || typeof payload !== "object") return null;
  if (!payload.mode) return null;

  const qaSummary = payload.qa_summary || {};
  const status = qaSummary.status === "FAIL" ? "FAIL" : "PASS";

  return {
    request_id: payload.request_id ?? null,
    mode: payload.mode,
    receipt: payload.receipt ?? null,
    qa_summary: {
      status,
      violation_codes: qaSummary.violation_codes || [],
      required_edits: qaSummary.required_edits || [],
      risk_score: qaSummary.risk_score,
    },
    audit_ok: payload.audit_ok,
    warnings: payload.warnings || [],
  };
}

export function buildEnforcementRequestFields(enforcement?: EnforcementPayload | null) {
  if (!enforcement || enforcement.mode === "off") return {};
  const receiptId = enforcement.receipt?.receipt_id;
  const requestId = enforcement.request_id;
  const fields: Record<string, string> = {};
  if (receiptId) fields.enforcement_receipt_id = receiptId;
  if (requestId) fields.enforcement_request_id = requestId;
  return fields;
}
