"""Minimal deterministic policy checks for Phase 10.1."""
from __future__ import annotations

import re
from typing import List, Tuple

from backend.features.enforcement.contracts import DraftContent, EvidenceBundle, QADecision

POLICY_VERSION = "10.1-v1"

_NUMBERING_RE = re.compile(r"^\s*(?:\d+(?:/\d+)?[.):\-\]]*\s*|(?:Tweet\s+)?\d+\s*[-:).]?\s*)", re.IGNORECASE)

# Profanity word list (simple, case-insensitive exact match)
_PROFANITY_WORDS = {
    "fuck", "shit", "bitch", "asshole", "damn", "crap", "bastard", "piss", "dick", "cock",
    "pussy", "cunt", "motherfucker", "fck", "fuk", "wtf", "bullshit", "nigga", "nigger",
    "faggot", "retard", "whore", "slut"
}

# Harmful content patterns (self-harm, abuse)
_HARMFUL_PATTERNS = [
    "kill myself", "killing myself", "end it all", "worthless", "piece of shit", "hate myself",
    "want to die", "suicide", "self harm", "cut myself", "hurt myself"
]

# Platform TOS patterns (conservative list)
_TOS_PATTERNS = {
    "x": ["i am elon musk", "i am donald trump", "official account", "verified by twitter"],
    "twitter": ["i am elon musk", "i am donald trump", "official account", "verified by twitter"],
    "instagram": ["nude photo", "explicit content", "buy followers"],
    "ig": ["nude photo", "explicit content", "buy followers"],
    "tiktok": ["dangerous challenge", "self harm challenge", "blackout challenge"],
    "youtube": ["clickbait thumbnail", "copyright infringement"]
}

def _contains_profanity(text: str) -> Tuple[bool, str]:
    """Check for profanity using word boundary matching."""
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    for word in words:
        if word in _PROFANITY_WORDS:
            return True, word
    return False, ""

def _contains_harmful_content(text: str) -> bool:
    """Check for harmful/self-harm patterns."""
    text_lower = text.lower()
    for pattern in _HARMFUL_PATTERNS:
        if pattern in text_lower:
            return True
    return False

def _violates_tos(text: str, platform: str) -> Tuple[bool, str]:
    """Check platform-specific TOS violations."""
    text_lower = text.lower()
    plat = (platform or "").lower()
    patterns = _TOS_PATTERNS.get(plat, [])
    for pattern in patterns:
        if pattern in text_lower:
            return True, pattern
    return False, ""


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

    # Check profanity
    has_profanity, example_word = _contains_profanity(content.content)
    if has_profanity:
        violations.append("PROFANITY")
        required_edits.append(f"Remove profanity (e.g., {example_word}) and regenerate.")

    # Check harmful content
    if _contains_harmful_content(content.content):
        violations.append("HARMFUL_CONTENT")
        required_edits.append("Reframe away from self-harm; focus on resilience/growth.")

    # Check TOS compliance
    violates_tos, tos_example = _violates_tos(content.content, platform)
    if violates_tos:
        violations.append("TOS_VIOLATION")
        required_edits.append(f"Remove platform-disallowed content ({tos_example}) to comply with TOS.")

    # Check policy tags
    if not content.policy_tags:
        violations.append("POLICY_TAGS_MISSING")
        required_edits.append("Add policy tags (e.g., no_harm, no_misinfo).")

    # Check lengtCITATIONS_REQUIRED"], ["Add at least one citation/
    max_chars = platform_max_chars(platform)
    lines = [line.strip() for line in content.content.split("\n") if line.strip()]
    for idx, line in enumerate(lines):
        if len(line) > max_chars:
            violations.append("LENGTH_EXCEEDED")
            required_edits.append(f"Shorten to {max_chars} characters (current {len(line)}).")
        if _NUMBERING_RE.match(line):
            violations.append("NUMBERING_NOT_ALLOWED")
            required_edits.append("Remove numbering/bullets; use plain sentences.")

    return violations, required_edits


def validate_evidence(bundle: EvidenceBundle, required: bool) -> Tuple[List[str], List[str]]:
    if not required:
        return [], []

    if not bundle.sources:
        return ["CITATIONS_REQUIRED"], ["Add at least one citation/source."]

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
