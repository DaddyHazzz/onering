type Props = {
  message?: string | null;
  suggestedFix?: string | null;
};

export default function EnforcementErrorCallout({ message, suggestedFix }: Props) {
  if (!message && !suggestedFix) return null;
  return (
    <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
      {message && <div className="font-semibold">{message}</div>}
      {suggestedFix && (
        <div className="mt-2 text-xs text-red-200">
          Suggested fix: {suggestedFix}
        </div>
      )}
    </div>
  );
}
