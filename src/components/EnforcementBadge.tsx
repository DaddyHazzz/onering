import { EnforcementPayload } from "@/lib/enforcement";

type Props = {
  enforcement: EnforcementPayload | null;
};

export default function EnforcementBadge({ enforcement }: Props) {
  if (!enforcement) return null;

  const mode = enforcement.mode.toUpperCase();
  const qaStatus = enforcement.qa_summary?.status || "PASS";
  const receiptId = enforcement.receipt?.receipt_id || "n/a";
  const requestId = enforcement.request_id || "n/a";
  const requiredEdits = enforcement.qa_summary?.required_edits || [];
  const violations = enforcement.qa_summary?.violation_codes || [];

  return (
    <div className="mt-4 flex flex-col gap-2 rounded-xl border border-white/10 bg-white/5 p-4 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full bg-white/10 px-3 py-1 font-semibold">
          Enforcement: {mode}
        </span>
        <span className={`rounded-full px-3 py-1 font-semibold ${qaStatus === "PASS" ? "bg-green-500/20 text-green-200" : "bg-red-500/20 text-red-200"}`}>
          QA: {qaStatus}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-white/70">
        <div>
          Request: <span className="font-mono">{requestId}</span>
          <button
            type="button"
            data-testid="copy-request-id"
            onClick={() => navigator.clipboard.writeText(requestId)}
            className="ml-2 rounded bg-white/10 px-2 py-0.5 text-xs"
          >
            Copy
          </button>
        </div>
        <div>
          Receipt: <span className="font-mono">{receiptId}</span>
          <button
            type="button"
            data-testid="copy-receipt-id"
            onClick={() => navigator.clipboard.writeText(receiptId)}
            className="ml-2 rounded bg-white/10 px-2 py-0.5 text-xs"
          >
            Copy
          </button>
        </div>
      </div>

      {qaStatus === "FAIL" && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs">
          {requiredEdits.length > 0 && (
            <div>
              <div className="font-semibold text-red-200">Required edits</div>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-red-100">
                {requiredEdits.map((edit, idx) => (
                  <li key={idx}>{edit}</li>
                ))}
              </ul>
            </div>
          )}
          {violations.length > 0 && (
            <div className="mt-2 text-red-100">
              Violations: {violations.join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
