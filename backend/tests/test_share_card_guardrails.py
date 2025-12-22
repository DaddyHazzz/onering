"""
backend/tests/test_share_card_guardrails.py
Determinism, safe fields, metric ranges, no shame language.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# Prohibited shame words
SHAME_WORDS = {
    "worthless",
    "piece of shit",
    "kill",
    "suicide",
    "useless",
    "loser",
    "fail",
    "stupid",
    "pathetic",
}


class TestShareCardDeterminism:
    """Same input → identical response (except timestamp)."""

    def test_share_card_determinism(self):
        """Calling twice with same handle returns same data."""
        # First call
        res1 = client.get("/v1/profile/share-card?handle=testuser&style=default")
        assert res1.status_code == 200
        data1 = res1.json()

        # Second call
        res2 = client.get("/v1/profile/share-card?handle=testuser&style=default")
        assert res2.status_code == 200
        data2 = res2.json()

        # Compare (ignoring timestamp)
        assert data1["title"] == data2["title"]
        assert data1["subtitle"] == data2["subtitle"]
        assert data1["metrics"] == data2["metrics"]
        assert data1["tagline"] == data2["tagline"]
        assert data1["theme"] == data2["theme"]

    def test_share_card_case_insensitive(self):
        """handle normalization: TestUser == testuser."""
        res1 = client.get("/v1/profile/share-card?handle=TestUser&style=default")
        res2 = client.get("/v1/profile/share-card?handle=testuser&style=default")

        if res1.status_code == 200 and res2.status_code == 200:
            assert res1.json()["title"] == res2.json()["title"]

    def test_share_card_consistent_tagline(self):
        """Same handle always gets same tagline (deterministic pool)."""
        res1 = client.get("/v1/profile/share-card?handle=alice&style=default")
        res2 = client.get("/v1/profile/share-card?handle=alice&style=default")

        if res1.status_code == 200 and res2.status_code == 200:
            assert res1.json()["tagline"] == res2.json()["tagline"]


class TestShareCardSafeFields:
    """No sensitive data, no auth tokens, no emails."""

    def test_no_sensitive_fields(self):
        """Share card should never include: password, email, auth tokens, API keys."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            json_str = str(data).lower()

            assert "password" not in json_str
            assert "token" not in json_str
            assert "secret" not in json_str
            assert "apikey" not in json_str
            assert "@" not in json_str  # no emails

    def test_metrics_structure_safe(self):
        """Metrics have only allowed fields: streak, momentum_score, weekly_delta, top_platform."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            allowed_metrics = {"streak", "momentum_score", "weekly_delta", "top_platform"}
            actual_metrics = set(data["metrics"].keys())

            assert actual_metrics.issubset(allowed_metrics)


class TestShareCardMetricRanges:
    """All metrics are in valid ranges (no negative, no overflow)."""

    def test_streak_non_negative(self):
        """Streak >= 0."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            assert data["metrics"]["streak"] >= 0

    def test_momentum_score_0_to_100(self):
        """Momentum score bounded to [0, 100]."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            score = data["metrics"]["momentum_score"]
            assert 0 <= score <= 100, f"Momentum score {score} out of range"

    def test_weekly_delta_reasonable(self):
        """Weekly delta should be small (within [-100, 100])."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            delta = data["metrics"]["weekly_delta"]
            assert -100 <= delta <= 100, f"Weekly delta {delta} unreasonable"

    def test_top_platform_is_string(self):
        """Top platform should be a string, not null."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            assert isinstance(data["metrics"]["top_platform"], str)
            assert len(data["metrics"]["top_platform"]) > 0


class TestShareCardLanguage:
    """No shame language (worthless, stupid, etc.)."""

    def test_no_shame_in_tagline(self):
        """Taglines must never contain shame words."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            tagline_lower = data["tagline"].lower()

            for shame_word in SHAME_WORDS:
                assert shame_word not in tagline_lower, (
                    f"Shame word '{shame_word}' found in tagline: {data['tagline']}"
                )

    def test_no_shame_in_subtitle(self):
        """Subtitles must never contain shame words."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            subtitle_lower = data["subtitle"].lower()

            for shame_word in SHAME_WORDS:
                assert shame_word not in subtitle_lower

    def test_trend_text_positive(self):
        """Trend text should be neutral or positive, never blame."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            subtitle = data["subtitle"]

            # Should be one of: rising, dipping, stable
            assert any(
                word in subtitle.lower() for word in ["rising", "dipping", "stable"]
            ), f"Unexpected trend text: {subtitle}"


class TestShareCardValidation:
    """Input validation: handle, style, edge cases."""

    def test_invalid_handle_empty(self):
        """Empty handle should fail."""
        res = client.get("/v1/profile/share-card?handle=&style=default")
        assert res.status_code == 400

    def test_invalid_handle_too_long(self):
        """Handle > 50 chars should fail."""
        long_handle = "a" * 51
        res = client.get(f"/v1/profile/share-card?handle={long_handle}&style=default")
        assert res.status_code == 400

    def test_invalid_style_defaults_to_default(self):
        """Unknown style should gracefully default."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=unknown")
        # Should succeed and use default theme
        assert res.status_code == 200
        assert res.json()["theme"] is not None

    def test_style_variants_all_valid(self):
        """All style variants return valid responses."""
        for style in ["default", "minimal", "bold"]:
            res = client.get(f"/v1/profile/share-card?handle=testuser&style={style}")
            assert res.status_code == 200
            data = res.json()
            assert "bg" in data["theme"]
            assert "accent" in data["theme"]


class TestShareCardFormat:
    """Response format: required fields, types."""

    def test_required_fields(self):
        """Share card must have: title, subtitle, metrics, tagline, theme, generated_at."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            required = {"title", "subtitle", "metrics", "tagline", "theme", "generated_at"}
            actual = set(data.keys())

            assert required.issubset(actual), (
                f"Missing fields: {required - actual}"
            )

    def test_generated_at_iso_format(self):
        """generated_at should be valid ISO 8601."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            try:
                datetime.fromisoformat(data["generated_at"])
            except ValueError:
                pytest.fail(f"Invalid ISO format: {data['generated_at']}")

    def test_metrics_required_fields(self):
        """Metrics must have: streak, momentum_score, weekly_delta, top_platform."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            required_metrics = {
                "streak",
                "momentum_score",
                "weekly_delta",
                "top_platform",
            }
            actual_metrics = set(data["metrics"].keys())

            assert required_metrics.issubset(actual_metrics)

    def test_theme_structure(self):
        """Theme must have: bg, accent."""
        res = client.get("/v1/profile/share-card?handle=testuser&style=default")
        if res.status_code == 200:
            data = res.json()
            assert "bg" in data["theme"]
            assert "accent" in data["theme"]
            assert isinstance(data["theme"]["bg"], str)
            assert isinstance(data["theme"]["accent"], str)


class TestShareCardEdgeCases:
    """Unicode, whitespace, special characters."""

    def test_handle_with_spaces_trimmed(self):
        """Spaces should be trimmed from handle."""
        res1 = client.get("/v1/profile/share-card?handle=%20testuser%20&style=default")
        res2 = client.get("/v1/profile/share-card?handle=testuser&style=default")

        if res1.status_code == 200 and res2.status_code == 200:
            assert res1.json()["title"] == res2.json()["title"]

    def test_handle_with_numbers(self):
        """Handles with numbers should work."""
        res = client.get("/v1/profile/share-card?handle=user123&style=default")
        assert res.status_code in [200, 404]  # 404 if user doesn't exist, but valid query

    def test_handle_with_underscore(self):
        """Handles with underscores should work."""
        res = client.get("/v1/profile/share-card?handle=user_name&style=default")
        assert res.status_code in [200, 404]

    def test_handle_with_dash(self):
        """Handles with dashes should work."""
        res = client.get("/v1/profile/share-card?handle=user-name&style=default")
        assert res.status_code in [200, 404]
