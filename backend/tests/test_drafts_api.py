"""
backend/tests/test_drafts_api.py
Tests for drafts API endpoints (Phase 5.1+5.2).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestDraftsAPI:
    """Test suite for drafts API endpoints"""
    
    def test_create_draft_success(self):
        """Test creating a new draft"""
        response = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user123"},
            json={"title": "Test Draft", "platform": "x"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "Test Draft"
        assert data["creator_id"] == "user123"
        assert data["ring_state"]["current_holder_id"] == "user123"
        assert len(data["segments"]) == 0
    
    def test_create_draft_missing_auth(self):
        """Test creating draft without auth header"""
        response = client.post(
            "/v1/collab/drafts",
            json={"title": "Test Draft", "platform": "x"}
        )
        assert response.status_code == 401
        assert "error" in response.json()
    
    def test_list_drafts_empty(self):
        """Test listing drafts for user with no drafts"""
        response = client.get(
            "/v1/collab/drafts",
            headers={"X-User-Id": "newuser"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["data"] == []
    
    def test_list_drafts_with_drafts(self):
        """Test listing drafts after creating some"""
        # Create two drafts
        client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user456"},
            json={"title": "Draft 1", "platform": "x"}
        )
        client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user456"},
            json={"title": "Draft 2", "platform": "x"}
        )
        
        # List drafts
        response = client.get(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        titles = [d["title"] for d in data["data"]]
        assert "Draft 1" in titles
        assert "Draft 2" in titles
    
    def test_get_draft_success(self):
        """Test retrieving a specific draft"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user789"},
            json={"title": "Get Test Draft", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Get draft
        response = client.get(f"/v1/collab/drafts/{draft_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["draft_id"] == draft_id
        assert data["title"] == "Get Test Draft"
    
    def test_get_draft_not_found(self):
        """Test retrieving non-existent draft"""
        response = client.get("/v1/collab/drafts/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()
    
    def test_append_segment_success(self):
        """Test appending segment by ring holder"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user111"},
            json={"title": "Segment Test", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Append segment
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "user111"},
            json={"content": "First segment", "idempotency_key": "seg1"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["segments"]) == 1
        assert data["segments"][0]["content"] == "First segment"
    
    def test_pass_ring_success(self):
        """Test passing ring to another user"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user222"},
            json={"title": "Ring Pass Test", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Add collaborator first
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "user222"},
            params={"collaborator_id": "user333", "role": "contributor"}
        )
        
        # Pass ring
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "user222"},
            json={"to_user_id": "user333", "idempotency_key": "ring-pass-123"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ring_state"]["current_holder_id"] == "user333"
    
    def test_add_collaborator_by_creator(self):
        """Test adding collaborator by draft creator"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "creator1"},
            json={"title": "Collab Test", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Add collaborator
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "creator1"},
            params={"collaborator_id": "collab1", "role": "contributor"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["draft_id"] is not None
    
    def test_add_collaborator_by_non_creator(self):
        """Test that non-creator cannot add collaborators"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "creator2"},
            json={"title": "Collab Test 2", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Try to add collaborator as non-creator
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "notcreator"},
            params={"collaborator_id": "collab2", "role": "contributor"}
        )
        assert response.status_code == 403
