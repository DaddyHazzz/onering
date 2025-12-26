# Phase 10.1 QA Policy v1

## Checks (deterministic)
- **PROFANITY**: reject if any banned term appears (case-insensitive list; exact word match).
- **HARMFUL_CONTENT**: reject self-harm/abuse phrases (configured keyword list); suggested redirect to resilience framing.
- **TOS_COMPLIANCE**: platform-specific forbidden phrases (e.g., impersonation for X, nudity for IG, dangerous challenges for TikTok); minimal keyword list per platform.
- **LENGTH_PER_POST**: total content length must not exceed platform limit (X 280 chars per line/tweet; IG 2200; TikTok 150; default 2200).
- **NUMBERING_NOT_ALLOWED**: leading numbering/bullets disallowed (regex already present) per line.
- **POLICY_TAGS_MISSING**: policy_tags must be non-empty.
- **CITATIONS_REQUIRED**: when required_citations=True and no evidence sources.

## Canonical Violation Codes
- `PROFANITY`
- `HARMFUL_CONTENT`
- `TOS_VIOLATION`
- `LENGTH_EXCEEDED`
- `NUMBERING_NOT_ALLOWED`
- `POLICY_TAGS_MISSING`
- `CITATIONS_REQUIRED`

## SuggestedFix Templates
- `PROFANITY`: "Remove profanity (e.g., {{example}}) and regenerate."
- `HARMFUL_CONTENT`: "Reframe away from self-harm; focus on resilience/growth."
- `TOS_VIOLATION`: "Remove platform-disallowed content ({{platform_example}}) to comply with TOS."
- `LENGTH_EXCEEDED`: "Shorten to {{limit}} characters (current {{length}})."
- `NUMBERING_NOT_ALLOWED`: "Remove numbering/bullets; use plain sentences."
- `POLICY_TAGS_MISSING`: "Add policy tags (e.g., no_harm, no_misinfo)."
- `CITATIONS_REQUIRED`: "Add at least one citation/source."

## Test Matrix (inputs → expected codes)
- "This is f*** great" → `PROFANITY`
- "I want to end it all" → `HARMFUL_CONTENT`
- "I am Elon Musk" (platform=X) → `TOS_VIOLATION`
- 400-char line on X → `LENGTH_EXCEEDED`
- "1/5 First..." → `NUMBERING_NOT_ALLOWED`
- Empty `policy_tags` → `POLICY_TAGS_MISSING`
- required_citations=True with empty evidence → `CITATIONS_REQUIRED`
- Clean content under limits → PASS (no codes)

## Alignment with Enforcement Outputs
- QA emits uppercase `PASS/FAIL`.
- `violation_codes` carries codes above; `required_edits` uses SuggestedFix templates with interpolated values.
- `qa_summary.status` and decisions use canonical casing; `would_block` true when any violation in enforced mode.
