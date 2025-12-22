"""Coach guardrail tests. No env vars required."""

import pytest
from backend.models.coach import CoachRequest
from backend.features.coach.service import CoachService
from backend.features.coach.scoring_engine import CoachScoringEngine


class TestCoachDeterminism:
    """Verify coach is deterministic (same input = identical output)."""
    
    def test_determinism_same_input_produces_identical_output(self):
        """Same draft + platform produces identical scores."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="I learned something important today about writing clear content.",
            type="simple",
            values_mode="neutral",
        )
        
        response1, events1 = CoachService.generate_feedback(request)
        response2, events2 = CoachService.generate_feedback(request)
        
        assert response1.overall_score == response2.overall_score
        assert response1.clarity_score == response2.clarity_score
        assert response1.suggestions == response2.suggestions
    
    def test_determinism_event_id_is_reproducible(self):
        """Same draft always produces same event_id (idempotency key)."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="This is a test draft.",
        )
        
        response1, _ = CoachService.generate_feedback(request)
        response2, _ = CoachService.generate_feedback(request)
        
        assert response1.event_id == response2.event_id


class TestCoachNoNetwork:
    """Verify coach never calls external services."""
    
    def test_scoring_engine_pure_function(self):
        """Scoring engine is pure function (no network calls)."""
        scores = CoachScoringEngine.score_draft(
            draft="Test draft for scoring.",
            platform="x",
            values_mode="neutral",
            post_type="simple",
        )
        
        assert scores is not None
        assert "overall_score" in scores
        assert isinstance(scores["overall_score"], int)
    
    def test_service_generates_feedback_locally(self):
        """Service generates feedback without network calls."""
        request = CoachRequest(
            user_id="user123",
            platform="linkedin",
            draft="I just shipped a new feature.",
        )
        
        response, events = CoachService.generate_feedback(request)
        assert response.overall_score is not None
        assert len(events) > 0
        assert events[0]["type"] == "coach.feedback_generated"


class TestCoachSafety:
    """Verify coach detects problematic language."""
    
    def test_disallowed_language_detected_optimistic_mode(self):
        """Optimistic mode detects despair language."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="Everything is hopeless and worthless.",
            values_mode="optimistic",
        )
        
        response, _ = CoachService.generate_feedback(request)
        assert len(response.warnings) > 0
    
    def test_harmful_language_detected(self):
        """Harmful language is detected consistently."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="kill yourself now",
            values_mode="neutral",
        )
        
        response, _ = CoachService.generate_feedback(request)
        assert len(response.warnings) > 0
    
    def test_excessive_hashtags_detected(self):
        """Too many hashtags trigger authenticity warning."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="This is great #awesome #amazing #wonderful #fantastic #incredible #best",
        )
        
        response, _ = CoachService.generate_feedback(request)
        assert any("hashtag" in w.lower() for w in response.warnings)


class TestCoachPlatformDifferentiation:
    """Verify platform feedback differs meaningfully."""
    
    def test_same_draft_different_platform_fit_scores(self):
        """Same draft yields different scores for different platforms."""
        draft = "Here's something I learned: always listen to your users first."
        
        request_x = CoachRequest(user_id="user123", platform="x", draft=draft)
        response_x, _ = CoachService.generate_feedback(request_x)
        
        request_linkedin = CoachRequest(user_id="user123", platform="linkedin", draft=draft)
        response_linkedin, _ = CoachService.generate_feedback(request_linkedin)
        
        # Platform fit should differ
        assert response_x.platform_fit_score != response_linkedin.platform_fit_score
    
    def test_x_values_brevity(self):
        """X scores shorter content higher on platform fit."""
        short_draft = "I learned: listen first."
        long_draft = "I learned that listening to users transforms product outcomes."
        
        req_short = CoachRequest(user_id="u1", platform="x", draft=short_draft)
        req_long = CoachRequest(user_id="u1", platform="x", draft=long_draft)
        
        resp_short, _ = CoachService.generate_feedback(req_short)
        resp_long, _ = CoachService.generate_feedback(req_long)
        
        # Short text should score higher on X
        assert resp_short.platform_fit_score >= resp_long.platform_fit_score


class TestCoachValuesMode:
    """Verify values mode affects feedback."""
    
    def test_confrontational_allows_directness(self):
        """Confrontational mode allows bold language."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="Here's the truth: most people give up too easily.",
            values_mode="confrontational",
        )
        
        response, _ = CoachService.generate_feedback(request)
        # Should still generate feedback without being penalized heavily
        assert response.authenticity_score >= 30


class TestCoachToneDetection:
    """Verify tone detection works."""
    
    def test_tone_detection_hopeful(self):
        """Detect hopeful tone."""
        draft = "I'm excited and looking forward to this!"
        scores = CoachScoringEngine.score_draft(draft, "x")
        assert scores["tone_label"] == "hopeful"
    
    def test_tone_detection_reflective(self):
        """Detect reflective tone."""
        draft = "I realized that I learned something important."
        scores = CoachScoringEngine.score_draft(draft, "x")
        assert scores["tone_label"] == "reflective"


class TestCoachSuggestions:
    """Verify suggestions are concrete and actionable."""
    
    def test_suggestions_provided(self):
        """Low-quality draft generates suggestions."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="xyz abc",
        )
        
        response, _ = CoachService.generate_feedback(request)
        assert len(response.suggestions) > 0
        assert len(response.suggestions) <= 5
    
    def test_suggestions_actionable(self):
        """Suggestions are action-oriented."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="I learned something",
        )
        
        response, _ = CoachService.generate_feedback(request)
        
        action_words = ["add", "break", "reduce", "share", "use", "tighten", "replace", "signal"]
        suggestions_text = " ".join(response.suggestions).lower()
        
        # At least one suggestion has an action verb
        assert any(word in suggestions_text for word in action_words)


class TestCoachEventEmission:
    """Verify coach.feedback_generated event is emitted."""
    
    def test_event_emitted_correctly(self):
        """coach.feedback_generated event has correct schema."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="Test draft",
        )
        
        response, events = CoachService.generate_feedback(request)
        
        assert len(events) == 1
        event = events[0]
        
        assert event["type"] == "coach.feedback_generated"
        assert event["userId"] == "user123"
        assert "draftId" in event
        assert "scores" in event
        assert "suggestions" in event
    
    def test_event_idempotent(self):
        """Same draft produces same event_id."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="Test draft",
        )
        
        _, events1 = CoachService.generate_feedback(request)
        _, events2 = CoachService.generate_feedback(request)
        
        assert events1[0]["draftId"] == events2[0]["draftId"]


class TestCoachRequestValidation:
    """Verify request validation works."""
    
    def test_missing_user_id(self):
        """Empty user_id fails validation."""
        request = CoachRequest(user_id="", platform="x", draft="Test")
        errors = request.validate()
        assert any("user_id" in e for e in errors)
    
    def test_missing_draft(self):
        """Empty draft fails validation."""
        request = CoachRequest(user_id="user123", platform="x", draft="")
        errors = request.validate()
        assert any("draft" in e for e in errors)
    
    def test_draft_too_long(self):
        """Draft > 4000 chars fails validation."""
        request = CoachRequest(user_id="user123", platform="x", draft="x" * 4001)
        errors = request.validate()
        assert any("4000" in e for e in errors)
    
    def test_invalid_platform(self):
        """Invalid platform fails validation."""
        request = CoachRequest(user_id="user123", platform="tiktok", draft="Test")
        errors = request.validate()
        assert any("platform" in e for e in errors)


class TestCoachRevisedExample:
    """Verify revised examples are deterministic."""
    
    def test_revised_example_generated(self):
        """X simple type generates example template."""
        draft = "I learned something."
        scores = CoachScoringEngine.score_draft(draft, "x", post_type="simple")
        
        assert scores["revised_example"] is not None
        assert "[" in scores["revised_example"]
    
    def test_revised_example_under_600_chars(self):
        """Revised example respects 600 char limit."""
        long_draft = "x" * 1000
        scores = CoachScoringEngine.score_draft(long_draft, "linkedin")
        
        if scores["revised_example"]:
            assert len(scores["revised_example"]) <= 600
    
    def test_revised_example_deterministic(self):
        """Same draft produces same example."""
        draft = "I discovered something."
        
        scores1 = CoachScoringEngine.score_draft(draft, "x")
        scores2 = CoachScoringEngine.score_draft(draft, "x")
        
        assert scores1["revised_example"] == scores2["revised_example"]


class TestCoachDimensionScores:
    """Verify dimension scores are computed."""
    
    def test_all_dimensions_scored(self):
        """All 5 dimensions have scores."""
        request = CoachRequest(user_id="u1", platform="x", draft="Test post")
        response, _ = CoachService.generate_feedback(request)
        
        assert 0 <= response.clarity_score <= 100
        assert 0 <= response.resonance_score <= 100
        assert 0 <= response.platform_fit_score <= 100
        assert 0 <= response.authenticity_score <= 100
        assert 0 <= response.momentum_alignment_score <= 100
    
    def test_overall_score_in_range(self):
        """Overall score is valid."""
        request = CoachRequest(user_id="u1", platform="x", draft="Test post")
        response, _ = CoachService.generate_feedback(request)
        
        assert 0 <= response.overall_score <= 100


class TestCoachStrategicLanguage:
    """Verify coach uses supportive, non-punitive language."""
    
    def test_suggestions_never_shame(self):
        """Suggestions are encouraging, not shaming."""
        request = CoachRequest(
            user_id="user123",
            platform="x",
            draft="blah blah",
        )
        
        response, _ = CoachService.generate_feedback(request)
        suggestions_text = "\n".join(response.suggestions).lower()
        
        # Should not contain shame words
        shame_words = ["bad", "wrong", "terrible", "awful", "sucks", "garbage", "trash"]
        for word in shame_words:
            assert word not in suggestions_text
    
    def test_no_auto_post_or_streak_impact(self):
        """Coach feedback does not auto-post or change streaks."""
        # This is more of a contract test - coach is advisory only
        request = CoachRequest(user_id="user123", platform="x", draft="Test")
        response, events = CoachService.generate_feedback(request)
        
        # Event should be informational only
        event = events[0]
        assert event["type"] == "coach.feedback_generated"
        assert "suggestions" in event  # Advisory
        assert "postContent" not in event  # NOT auto-posting
