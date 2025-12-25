"""Minimal deterministic policy checks for Phase 10.1."""
from __future__ import annotations

import re
from typing import List, Tuple

from backend.features.enforcement.contracts import DraftContent, EvidenceBundle, QADecision

POLICY_VERSION = "10.1-min"

_NUMBERING_RE = re.compile(r"^\s*(?:\d+(?:/\d+)?[.):\-\]]*\s*|(?:Tweet\s+)?\d+\s*[-:).]?\s*)", re.IGNORECASE)


def platform_max_chars(platform: str) -> int:
    plat = (platform or "").lower()
    if plat in {"x", "twitter"}:
        return 280
    if plat in {"instagram", "ig"}:
        return 2200
    if plat in {"tiktok"}:
        return 2200
    if plat in {"youtube"}:
        return 5000
    return 2000


def requires_research(required_citations: bool) -> bool:
    return bool(required_citations)


def validate_draft_content(content: DraftContent, platform: str) -> Tuple[List[str], List[str]]:
    violations: List[str] = []
    required_edits: List[str] = []

    if not content.policy_tags:
        violations.append("POLICY_TAGS_MISSING")
        required_edits.append("Add required policy tags to the draft content.")

    max_chars = platform_max_chars(platform)
    lines = [line.strip() for line in content.content.split("\n") if line.strip()]
    for idx, line in enumerate(lines):
        if len(line) > max_chars:
            violations.append("LINE_TOO_LONG")
            required_edits.append(f"Shorten line {idx + 1} to {max_chars} characters or less.")
        if _NUMBERING_RE.match(line):
            violations.append("NUMBERING_NOT_ALLOWED")
            required_edits.append(f"Remove numbering prefixes from line {idx + 1}.")

    return violations, required_edits


def validate_evidence(bundle: EvidenceBundle, required: bool) -> Tuple[List[str], List[str]]:
    if not required:
        return [], []

    if not bundle.sources:
        return ["MISSING_CITATIONS"], ["Provide at least one citation source."]

    return [], []


def build_qa_decision(
    *,
    draft: DraftContent,
    evidence: EvidenceBundle,
    required_citations: bool,
    platform: str,
) -> QADecision:
    violations: List[str] = []
    required_edits: List[str] = []

    content_violations, content_edits = validate_draft_content(draft, platform)
    violations.extend(content_violations)
    required_edits.extend(content_edits)

    evidence_violations, evidence_edits = validate_evidence(evidence, required_citations)
    violations.extend(evidence_violations)
    required_edits.extend(evidence_edits)

    status = "PASS" if not violations else "FAIL"
    risk_score = 0.1 if status == "PASS" else 0.8

    return QADecision(
        status=status,
        violation_codes=sorted(set(violations)),
        required_edits=required_edits,
        risk_score=risk_score,
    )
