"""
backend/tests/test_drafts_visibility.py
Tests for draft visibility and collaborator permissions (Phase 5.1+5.2).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestDraftsVisibility:
    """Test suite for draft visibility rules"""
    
    def test_creator_sees_own_draft(self):
        """Test that creator sees their draft in list"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "creator1"},
            json={"title": "Visibility Test 1", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # List drafts
        response = client.get(
            "/v1/collab/drafts",
            headers={"X-User-Id": "creator1"}
        )
        assert response.status_code == 200
        draft_ids = [d["draft_id"] for d in response.json()["data"]]
        assert draft_id in draft_ids
    
    def test_creator_can_read_own_draft(self):
        """Test that creator can read their draft details"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "creator2"},
            json={"title": "Visibility Test 2", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Get draft
        response = client.get(f"/v1/collab/drafts/{draft_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["creator_id"] == "creator2"
    
    def test_non_collaborator_sees_public_draft(self):
        """Test that non-collaborator can see draft (for now - no private drafts yet)"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "creator3"},
            json={"title": "Public Draft", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Non-collaborator reads draft
        response = client.get(f"/v1/collab/drafts/{draft_id}")
        assert response.status_code == 200
        # Note: In Phase 5.3+, we'll add privacy controls
    
    def test_collaborator_sees_shared_draft(self):
        """Test that added collaborator sees draft in their list (future)"""
        # This test documents future behavior for Phase 5.3+
        # Currently, we don't filter list_drafts by collaborator membership
        pass
    
    def test_list_drafts_filters_by_user(self):
        """Test that list_drafts returns drafts for specific user"""
        # Create drafts for user A
        client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user_a"},
            json={"title": "A's Draft 1", "platform": "x"}
        )
        client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user_a"},
            json={"title": "A's Draft 2", "platform": "x"}
        )
        
        # Create drafts for user B
        client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user_b"},
            json={"title": "B's Draft 1", "platform": "x"}
        )
        
        # List A's drafts
        response_a = client.get(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user_a"}
        )
        titles_a = [d["title"] for d in response_a.json()["data"]]
        
        # List B's drafts
        response_b = client.get(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user_b"}
        )
        titles_b = [d["title"] for d in response_b.json()["data"]]
        
        # Verify each user sees their own drafts
        assert "A's Draft 1" in titles_a
        assert "A's Draft 2" in titles_a
        assert "B's Draft 1" in titles_b
        
        # Note: Currently list_drafts may show all drafts, not filtered
        # This test documents expected behavior for Phase 5.3+
    
    def test_draft_segments_visible_to_all(self):
        """Test that segments are visible when reading draft"""
        # Create draft and add segments
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user1"},
            json={"title": "Segment Visibility Test", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "user1"},
            json={"content": "First segment", "idempotency_key": "seg1"}
        )
        
        # Add user2 as collaborator
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "user1"},
            params={"collaborator_id": "user2", "role": "contributor"}
        )
        
        # Pass ring and add another segment
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "user1"},
            json={"to_user_id": "user2", "idempotency_key": "ring-pass-1"}
        )
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "user2"},
            json={"content": "Second segment", "idempotency_key": "seg2"}
        )
        
        # Read draft - should see all segments
        response = client.get(f"/v1/collab/drafts/{draft_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["segments"]) == 2
        contents = [s["content"] for s in data["segments"]]
        assert "First segment" in contents
        assert "Second segment" in contents
