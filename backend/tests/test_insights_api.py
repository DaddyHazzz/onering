"""
backend/tests/test_insights_api.py
Integration tests for insights API endpoint.
Phase 8.7.1: Complete backend test suite with real collaboration service integration.
"""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def create_draft_with_collaborators(creator_id="alice", title="Insights Test Draft"):
    """Helper: create draft with creator and two collaborators."""
    resp = client.post(
        "/v1/collab/drafts",
        headers={"X-User-Id": creator_id},
        json={"title": title, "platform": "x"},
    )
    draft = resp.json()["data"]
    draft_id = draft["draft_id"]
    
    # Add bob and carol as collaborators
    client.post(
        f"/v1/collab/drafts/{draft_id}/collaborators",
        headers={"X-User-Id": creator_id},
        params={"collaborator_id": "bob", "role": "contributor"},
    )
    client.post(
        f"/v1/collab/drafts/{draft_id}/collaborators",
        headers={"X-User-Id": creator_id},
        params={"collaborator_id": "carol", "role": "contributor"},
    )
    
    return draft_id


class TestInsightsAPI:
    """Test suite for GET /api/insights/drafts/{draft_id} endpoint."""
    
    def test_stalled_draft_insight(self):
        """Stalled draft: no activity for >48h should generate STALLED insight."""
        draft_id = create_draft_with_collaborators()
        
        # Add initial segment
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "alice"},
            json={"content": "Initial segment", "idempotency_key": "seg_init"},
        )
        
        # Request insights with deterministic time 50 hours in the future
        now = datetime.now(timezone.utc) + timedelta(hours=50)
        resp = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
            params={"now": now.isoformat()},
        )
        
        assert resp.status_code == 200
        body = resp.json()
        
        # Should have STALLED insight
        assert "insights" in body
        insights = body["insights"]
        stalled = [i for i in insights if i["type"] == "stalled"]
        assert len(stalled) > 0
        # Message should mention stalled or inactivity
        assert "stalled" in stalled[0]["title"].lower() or "activity" in stalled[0]["message"].lower()
    
    def test_dominant_user_insight(self):
        """Dominant user: one user with >60% of words should generate DOMINANT_USER insight."""
        draft_id = create_draft_with_collaborators()
        
        # Alice adds many words (>60% of total)
        for i in range(5):
            client.post(
                f"/v1/collab/drafts/{draft_id}/segments",
                headers={"X-User-Id": "alice"},
                json={"content": "Alice writes a lot of content here " * 10, "idempotency_key": f"seg_a{i}"},
            )
        
        # Pass ring to bob
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "alice"},
            json={"to_user_id": "bob", "idempotency_key": "pass_ab"},
        )
        
        # Bob adds minimal content (<10% of total)
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "bob"},
            json={"content": "Bob's small contribution", "idempotency_key": "seg_b1"},
        )
        
        # Request insights
        resp = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
        )
        
        assert resp.status_code == 200
        body = resp.json()
        
        # Should have DOMINANT_USER insight
        insights = body["insights"]
        dominant = [i for i in insights if i["type"] == "dominant_user"]
        assert len(dominant) > 0
        # Message should mention alice and dominance/contribution
        assert "alice" in dominant[0]["message"].lower()
        assert ("dominant" in dominant[0]["message"].lower() or "contributed" in dominant[0]["message"].lower())
    
    def test_healthy_draft_no_critical_insights(self):
        """Healthy draft: recent activity, balanced contributions → no critical insights."""
        draft_id = create_draft_with_collaborators()
        
        # Alice adds content
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "alice"},
            json={"content": "Alice writes some content", "idempotency_key": "seg_a1"},
        )
        
        # Pass ring to bob
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "alice"},
            json={"to_user_id": "bob", "idempotency_key": "pass_ab"},
        )
        
        # Bob adds similar amount
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "bob"},
            json={"content": "Bob writes some content too", "idempotency_key": "seg_b1"},
        )
        
        # Pass ring to carol
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "bob"},
            json={"to_user_id": "carol", "idempotency_key": "pass_bc"},
        )
        
        # Carol adds content
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "carol"},
            json={"content": "Carol writes balanced content", "idempotency_key": "seg_c1"},
        )
        
        # Request insights immediately (recent activity)
        resp = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
        )
        
        assert resp.status_code == 200
        body = resp.json()
        
        # Should NOT have STALLED or DOMINANT_USER insights
        insights = body["insights"]
        critical_categories = [i["type"] for i in insights]
        assert "stalled" not in critical_categories
        assert "dominant_user" not in critical_categories
    
    def test_alerts_no_activity_and_long_hold(self):
        """Alerts: no_activity_alert (>72h) and long_hold_alert (>24h for one user)."""
        draft_id = create_draft_with_collaborators()
        
        # Alice holds ring but does nothing for 25 hours
        now_25h = datetime.now(timezone.utc) + timedelta(hours=25)
        
        resp = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
            params={"now": now_25h.isoformat()},
        )
        
        assert resp.status_code == 200
        body = resp.json()
        
        # Should have long_ring_hold alert (>24h)
        assert "alerts" in body
        alerts = body["alerts"]
        long_hold = [a for a in alerts if a["alert_type"] == "long_ring_hold"]
        assert len(long_hold) > 0
        assert "24" in long_hold[0]["reason"] or "held" in long_hold[0]["reason"].lower()
        
        # Now test no_activity_alert (>72h)
        now_75h = datetime.now(timezone.utc) + timedelta(hours=75)
        
        resp2 = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
            params={"now": now_75h.isoformat()},
        )
        
        assert resp2.status_code == 200
        body2 = resp2.json()
        
        alerts2 = body2["alerts"]
        no_activity = [a for a in alerts2 if a["alert_type"] == "no_activity"]
        assert len(no_activity) > 0
        assert "72" in no_activity[0]["reason"] or "activity" in no_activity[0]["reason"].lower()
    
    def test_403_non_collaborator_access(self):
        """Non-collaborator access: should return 403 Forbidden."""
        draft_id = create_draft_with_collaborators(creator_id="alice")
        
        # Dan (not a collaborator) tries to access insights
        resp = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "dan"},
        )
        
        assert resp.status_code == 403
        body = resp.json()
        assert "collaborator" in body["detail"].lower()
    
    def test_deterministic_insights_with_now_parameter(self):
        """Deterministic: same 'now' parameter should produce identical insights."""
        draft_id = create_draft_with_collaborators()
        
        # Add segment
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "alice"},
            json={"content": "Test segment", "idempotency_key": "seg_det"},
        )
        
        # Fixed now timestamp
        now = datetime.now(timezone.utc) + timedelta(hours=50)
        
        # Request insights twice with same 'now'
        resp1 = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
            params={"now": now.isoformat()},
        )
        
        resp2 = client.get(
            f"/api/insights/drafts/{draft_id}",
            headers={"X-User-Id": "alice"},
            params={"now": now.isoformat()},
        )
        
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        
        body1 = resp1.json()
        body2 = resp2.json()
        
        # Insights should be identical
        assert body1["insights"] == body2["insights"]
        assert body1["recommendations"] == body2["recommendations"]
        assert body1["alerts"] == body2["alerts"]
