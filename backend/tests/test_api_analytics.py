"""
backend/tests/test_api_analytics.py

Tests for analytics API endpoints (Phase 3.4).
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from backend.main import app
from backend.features.analytics.event_store import EventStore, create_event, get_store


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_event_store():
    """Clear event store before and after each test."""
    store = get_store()
    store.clear()
    yield
    store.clear()


@pytest.fixture
def fixed_now():
    """Fixed timestamp for deterministic testing."""
    return datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_events(fixed_now):
    """Sample events for testing."""
    events = [
        create_event("DraftCreated", {"draft_id": "draft-1", "creator_id": "user-1"}, now=fixed_now - timedelta(hours=3)),
        create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-1", "contributor_id": "user-1"}, now=fixed_now - timedelta(hours=2)),
        create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-2", "contributor_id": "user-2"}, now=fixed_now - timedelta(hours=1)),
        create_event("RINGPassed", {"draft_id": "draft-1", "from_user_id": "user-1", "to_user_id": "user-2"}, now=fixed_now - timedelta(minutes=30)),
        create_event("DraftViewed", {"draft_id": "draft-1", "user_id": "user-3"}, now=fixed_now - timedelta(minutes=15)),
        create_event("DraftShared", {"draft_id": "draft-1", "user_id": "user-1"}, now=fixed_now - timedelta(minutes=5)),
    ]
    
    # Append events to store using get_store() for backend consistency
    store = get_store()
    for i, event in enumerate(events):
        store.append(event, f"test-key-{i}")
    
    return events


class TestDraftAnalyticsEndpoint:
    """Test GET /v1/collab/drafts/{draft_id}/analytics endpoint."""
    
    def test_get_draft_analytics_success(self, client, sample_events, fixed_now):
        """GET draft analytics returns correct metrics."""
        response = client.get(
            "/api/analytics/v1/collab/drafts/draft-1/analytics",
            params={"now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        
        analytics = data["data"]
        assert analytics["draft_id"] == "draft-1"
        assert analytics["views"] == 1
        assert analytics["shares"] == 1
        assert analytics["segments_count"] == 2
        assert analytics["contributors_count"] == 2
        assert analytics["ring_passes_count"] == 1
    
    def test_get_draft_analytics_nonexistent_draft_returns_defaults(self, client, fixed_now):
        """GET analytics for nonexistent draft returns sensible defaults."""
        response = client.get(
            "/api/analytics/v1/collab/drafts/nonexistent-draft/analytics",
            params={"now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        analytics = data["data"]
        assert analytics["views"] == 0
        assert analytics["shares"] == 0
        assert analytics["segments_count"] == 1  # Minimum
        assert analytics["contributors_count"] == 1  # Minimum
    
    def test_get_draft_analytics_deterministic(self, client, sample_events, fixed_now):
        """Same draft + same now => identical response."""
        response1 = client.get(
            "/api/analytics/v1/collab/drafts/draft-1/analytics",
            params={"now": fixed_now.isoformat()}
        )
        response2 = client.get(
            "/api/analytics/v1/collab/drafts/draft-1/analytics",
            params={"now": fixed_now.isoformat()}
        )
        
        assert response1.json() == response2.json()
    
    def test_get_draft_analytics_invalid_timestamp_returns_400(self, client):
        """Invalid timestamp format returns 400."""
        response = client.get(
            "/api/analytics/v1/collab/drafts/draft-1/analytics",
            params={"now": "not-a-timestamp"}
        )
        
        assert response.status_code == 400


class TestLeaderboardEndpoint:
    """Test GET /v1/analytics/leaderboard endpoint."""
    
    def test_get_leaderboard_collaboration_success(self, client, sample_events, fixed_now):
        """GET leaderboard with collaboration metric returns top 10."""
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "collaboration", "now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        
        leaderboard = data["data"]
        assert leaderboard["metric_type"] == "collaboration"
        assert len(leaderboard["entries"]) <= 10
        assert "message" in leaderboard
    
    def test_get_leaderboard_momentum_success(self, client, sample_events, fixed_now):
        """GET leaderboard with momentum metric works."""
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "momentum", "now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["metric_type"] == "momentum"
    
    def test_get_leaderboard_consistency_success(self, client, sample_events, fixed_now):
        """GET leaderboard with consistency metric works."""
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "consistency", "now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["metric_type"] == "consistency"
    
    def test_get_leaderboard_invalid_metric_returns_400(self, client):
        """Invalid metric type returns 400."""
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "invalid_metric"}
        )
        
        assert response.status_code == 400
        assert "Invalid metric type" in response.json()["detail"]
    
    def test_get_leaderboard_deterministic(self, client, sample_events, fixed_now):
        """Same metric + same now => identical response."""
        response1 = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "collaboration", "now": fixed_now.isoformat()}
        )
        response2 = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "collaboration", "now": fixed_now.isoformat()}
        )
        
        assert response1.json() == response2.json()
    
    def test_get_leaderboard_entries_max_10(self, client, fixed_now):
        """Leaderboard returns max 10 entries (prevents rank shame)."""
        # Create events for 15 users
        for i in range(15):
            event = create_event(
                "DraftCreated",
                {"draft_id": f"draft-{i}", "creator_id": f"user-{i}"},
                now=fixed_now
            )
            EventStore.append(event, f"key-{i}")
        
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "collaboration", "now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["entries"]) <= 10
    
    def test_get_leaderboard_insights_never_comparative(self, client, sample_events, fixed_now):
        """Leaderboard insights never contain comparative language."""
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "collaboration", "now": fixed_now.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        forbidden_phrases = [
            "you're behind",
            "catch up",
            "falling behind",
            "ahead of",
            "better than",
        ]
        
        # Check message
        message_lower = data["data"]["message"].lower()
        for phrase in forbidden_phrases:
            assert phrase not in message_lower
        
        # Check insights
        for entry in data["data"]["entries"]:
            insight_lower = entry["insight"].lower()
            for phrase in forbidden_phrases:
                assert phrase not in insight_lower
    
    def test_get_leaderboard_invalid_timestamp_returns_400(self, client):
        """Invalid timestamp format returns 400."""
        response = client.get(
            "/api/analytics/v1/analytics/leaderboard",
            params={"metric": "collaboration", "now": "not-a-timestamp"}
        )
        
        assert response.status_code == 400

