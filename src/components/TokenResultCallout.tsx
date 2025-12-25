type TokenResult = {
  mode: string;
  issued_amount?: number;
  pending_amount?: number;
  reason_code?: string;
  guardrails_applied?: string[];
};

export default function TokenResultCallout({ tokenResult }: { tokenResult: TokenResult | null }) {
  if (!tokenResult) return null;

  const headline =
    tokenResult.mode === "shadow"
      ? `Earned +${tokenResult.pending_amount || 0} RING (pending)`
      : tokenResult.mode === "live"
      ? `Earned +${tokenResult.issued_amount || 0} RING`
      : "Token issuance disabled";

  return (
    <div className="mb-6 rounded-2xl border border-white/10 bg-black/40 p-5 text-sm">
      <div className="text-lg font-semibold">{headline}</div>
      {tokenResult.reason_code && (
        <div className="text-gray-300 mt-1">Reason: {tokenResult.reason_code}</div>
      )}
      {tokenResult.guardrails_applied && tokenResult.guardrails_applied.length > 0 && (
        <div className="text-gray-400 mt-1">
          Guardrails: {tokenResult.guardrails_applied.join(", ")}
        </div>
      )}
    </div>
  );
}
