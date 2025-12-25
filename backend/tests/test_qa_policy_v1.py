"""Tests for Phase 10.1 QA Policy v1 hardening."""
import pytest
from backend.features.enforcement.contracts import DraftContent, EvidenceBundle, FormatMetadata, EvidenceSource
from backend.features.enforcement.policy import build_qa_decision


def _make_format(format_type="viral_thread", max_chars=280):
    """Helper to create FormatMetadata."""
    return FormatMetadata(
        format=format_type,
        max_chars=max_chars,
        line_breaks="newline"
    )


def _make_draft(content, policy_tags=None, format_type="viral_thread", max_chars=280):
    """Helper to create DraftContent."""
    return DraftContent(
        content=content,
        format=_make_format(format_type, max_chars),
        policy_tags=policy_tags or []
    )


class TestProfanityCheck:
    def test_profanity_detected(self):
        draft = _make_draft(
            content="This is shit great content",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert decision.status == "FAIL"
        assert "PROFANITY" in decision.violation_codes
        assert any("profanity" in edit.lower() for edit in decision.required_edits)

    def test_profanity_variations(self):
        """Test common profanity variations and word boundaries."""
        test_cases = [
            "This shit is crazy",
            "What the fuck is this",
            "You're such a bitch",
            "Holy crap that's cool"
        ]
        for content in test_cases:
            draft = _make_draft(content=content, policy_tags=["no_harm"])
            evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
            decision = build_qa_decision(
                draft=draft, evidence=evidence, required_citations=False, platform="x"
            )
            assert decision.status == "FAIL"
            assert "PROFANITY" in decision.violation_codes

    def test_no_false_positive_profanity(self):
        """Clean content should not trigger profanity."""
        draft = _make_draft(
            content="This is great content about class and pass statements",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "PROFANITY" not in decision.violation_codes


class TestHarmfulContent:
    def test_harmful_self_harm_patterns(self):
        test_cases = [
            "I want to end it all",
            "I feel worthless and want to die",
            "Thinking about suicide today",
            "I just want to kill myself"
        ]
        for content in test_cases:
            draft = _make_draft(content=content, policy_tags=["no_harm"])
            evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
            decision = build_qa_decision(
                draft=draft, evidence=evidence, required_citations=False, platform="x"
            )
            assert decision.status == "FAIL"
            assert "HARMFUL_CONTENT" in decision.violation_codes
            assert any("resilience" in edit.lower() for edit in decision.required_edits)

    def test_no_false_positive_harmful(self):
        """Neutral content should not trigger harmful check."""
        draft = _make_draft(
            content="Today I ended my workout routine and felt great",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "HARMFUL_CONTENT" not in decision.violation_codes


class TestTOSViolations:
    def test_tos_x_impersonation(self):
        draft = _make_draft(
            content="I am Elon Musk and I approve this message",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert decision.status == "FAIL"
        assert "TOS_VIOLATION" in decision.violation_codes
        assert any("comply with TOS" in edit for edit in decision.required_edits)

    def test_tos_instagram_violations(self):
        draft = _make_draft(
            content="Check out my nude photo collection",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="instagram"
        )
        
        assert decision.status == "FAIL"
        assert "TOS_VIOLATION" in decision.violation_codes

    def test_tos_tiktok_dangerous_challenge(self):
        draft = _make_draft(
            content="Try the dangerous challenge with me",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="tiktok"
        )
        
        assert decision.status == "FAIL"
        assert "TOS_VIOLATION" in decision.violation_codes

    def test_no_false_positive_tos(self):
        """Neutral content should not trigger TOS."""
        draft = _make_draft(
            content="I admire Elon Musk's vision for the future",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "TOS_VIOLATION" not in decision.violation_codes


class TestLengthConstraints:
    def test_x_length_exceeded(self):
        """X/Twitter has 280 char limit per line."""
        long_line = "a" * 400
        draft = _make_draft(content=long_line, policy_tags=["no_harm"])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert decision.status == "FAIL"
        assert "LENGTH_EXCEEDED" in decision.violation_codes
        assert any("280 characters" in edit for edit in decision.required_edits)

    def test_instagram_length_limit(self):
        """Instagram has 2200 char limit."""
        long_line = "a" * 2500
        draft = _make_draft(content=long_line, policy_tags=["no_harm"])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="instagram"
        )
        
        assert decision.status == "FAIL"
        assert "LENGTH_EXCEEDED" in decision.violation_codes

    def test_length_within_limits(self):
        """Content under limits should pass."""
        draft = _make_draft(
            content="This is a short post under the limit",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "LENGTH_EXCEEDED" not in decision.violation_codes


class TestNumberingConstraints:
    def test_numbering_patterns_rejected(self):
        test_cases = [
            "1/5 First tweet in the thread",
            "1. This is the first point",
            "Tweet 1: Introduction",
            "2) Second point here"
        ]
        for content in test_cases:
            draft = _make_draft(content=content, policy_tags=["no_harm"])
            evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
            decision = build_qa_decision(
                draft=draft, evidence=evidence, required_citations=False, platform="x"
            )
            assert decision.status == "FAIL"
            assert "NUMBERING_NOT_ALLOWED" in decision.violation_codes

    def test_no_false_positive_numbering(self):
        """Content with numbers but not leading should pass."""
        draft = _make_draft(
            content="There are 5 reasons why this works",
            policy_tags=["no_harm"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "NUMBERING_NOT_ALLOWED" not in decision.violation_codes


class TestPolicyTags:
    def test_missing_policy_tags(self):
        draft = _make_draft(content="Some content", policy_tags=[])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert decision.status == "FAIL"
        assert "POLICY_TAGS_MISSING" in decision.violation_codes
        assert any("policy tags" in edit.lower() for edit in decision.required_edits)

    def test_policy_tags_present(self):
        draft = _make_draft(
            content="Some content",
            policy_tags=["no_harm", "no_misinfo"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "POLICY_TAGS_MISSING" not in decision.violation_codes


class TestCitationsRequired:
    def test_citations_required_missing(self):
        draft = _make_draft(content="Some content", policy_tags=["no_harm"])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=True, platform="x"
        )
        
        assert decision.status == "FAIL"
        assert "CITATIONS_REQUIRED" in decision.violation_codes
        assert any("citation" in edit.lower() for edit in decision.required_edits)

    def test_citations_present(self):
        from datetime import datetime
        draft = _make_draft(content="Some content", policy_tags=["no_harm"])
        source = EvidenceSource(url="https://example.com", title="Example", timestamp=datetime.now(), relevance_score=0.8)
        evidence = EvidenceBundle(sources=[source], summary="Example source", quality_score=0.8)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=True, platform="x"
        )
        
        assert "CITATIONS_REQUIRED" not in decision.violation_codes

    def test_citations_not_required(self):
        """When citations not required, empty sources should pass."""
        draft = _make_draft(content="Some content", policy_tags=["no_harm"])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert "CITATIONS_REQUIRED" not in decision.violation_codes


class TestCleanContent:
    def test_clean_content_passes(self):
        """Completely clean content should pass all checks."""
        draft = _make_draft(
            content="This is great content about AI and machine learning trends",
            policy_tags=["no_harm", "no_misinfo"]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert decision.status == "PASS"
        assert len(decision.violation_codes) == 0
        assert len(decision.required_edits) == 0

    def test_multiple_violations(self):
        """Content with multiple issues should list all violations."""
        draft = _make_draft(
            content="1/5 This is shit content about killing myself",
            policy_tags=[]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=True, platform="x"
        )
        
        assert decision.status == "FAIL"
        assert "PROFANITY" in decision.violation_codes
        assert "HARMFUL_CONTENT" in decision.violation_codes
        assert "NUMBERING_NOT_ALLOWED" in decision.violation_codes
        assert "POLICY_TAGS_MISSING" in decision.violation_codes
        assert "CITATIONS_REQUIRED" in decision.violation_codes
        assert len(decision.required_edits) >= 5


class TestDecisionProperties:
    def test_status_uppercase(self):
        """Status should be uppercase PASS or FAIL."""
        draft = _make_draft(content="Clean content", policy_tags=["no_harm"])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        
        # PASS case
        pass_decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        assert pass_decision.status in ["PASS", "FAIL"]
        assert pass_decision.status.isupper()
        
        # FAIL case
        draft_bad = _make_draft(content="This is f*** bad", policy_tags=["no_harm"])
        fail_decision = build_qa_decision(
            draft=draft_bad, evidence=evidence, required_citations=False, platform="x"
        )
        assert fail_decision.status in ["PASS", "FAIL"]
        assert fail_decision.status.isupper()

    def test_violation_codes_sorted_unique(self):
        """Violation codes should be sorted and unique."""
        draft = _make_draft(
            content="1/5 shit content\n2/5 more crap",
            policy_tags=[]
        )
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        decision = build_qa_decision(
            draft=draft, evidence=evidence, required_citations=False, platform="x"
        )
        
        # Should deduplicate PROFANITY and NUMBERING_NOT_ALLOWED
        assert decision.violation_codes == sorted(set(decision.violation_codes))

    def test_risk_score_mapping(self):
        """Risk score should be 0.1 for PASS, 0.8 for FAIL."""
        draft_clean = _make_draft(content="Clean", policy_tags=["no_harm"])
        draft_bad = _make_draft(content="shit bad", policy_tags=["no_harm"])
        evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
        
        pass_decision = build_qa_decision(
            draft=draft_clean, evidence=evidence, required_citations=False, platform="x"
        )
        fail_decision = build_qa_decision(
            draft=draft_bad, evidence=evidence, required_citations=False, platform="x"
        )
        
        assert pass_decision.risk_score == 0.1
        assert fail_decision.risk_score == 0.8
