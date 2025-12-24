"""
backend/tests/test_ring_enforcement.py
Tests for ring holder enforcement (Phase 5.1+5.2).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestRingEnforcement:
    """Test suite for ring holder rules"""
    
    def test_ring_holder_can_append_segment(self):
        """Test that ring holder can append segments"""
        # Create draft (user becomes ring holder)
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "holder1"},
            json={"title": "Ring Test 1", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Ring holder appends segment
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "holder1"},
            json={"content": "Holder's segment", "idempotency_key": "seg1"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["segments"]) == 1
    
    def test_non_holder_cannot_append_segment(self):
        """Test that non-holder gets 403 with ring_required code"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "holder2"},
            json={"title": "Ring Test 2", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Add non-holder as collaborator first
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "holder2"},
            params={"collaborator_id": "nonholder", "role": "contributor"}
        )
        
        # Non-holder (collaborator but not ring holder) tries to append segment
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "nonholder"},
            json={"content": "Should fail", "idempotency_key": "seg2"}
        )
        
        # Assert 403 with ring_required error code
        assert response.status_code == 403
        error_data = response.json()
        assert error_data["error"]["code"] == "ring_required"
        assert "ring" in error_data["error"]["message"].lower()
    
    def test_ring_passed_new_holder_can_append(self):
        """Test that new ring holder can append after ring pass"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "holder3"},
            json={"title": "Ring Test 3", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Add newholder as collaborator first
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "holder3"},
            params={"collaborator_id": "newholder", "role": "contributor"}
        )
        
        # Pass ring to new user (who is now a collaborator)
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "holder3"},
            json={"to_user_id": "newholder", "idempotency_key": "pass_ring_3"}
        )
        
        # New holder appends segment
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "newholder"},
            json={"content": "New holder's segment", "idempotency_key": "seg3"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ring_state"]["current_holder_id"] == "newholder"
        assert len(data["segments"]) == 1
    
    def test_old_holder_cannot_append_after_pass(self):
        """Test that old ring holder loses append privileges"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "holder4"},
            json={"title": "Ring Test 4", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Add newholder2 as collaborator first
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "holder4"},
            params={"collaborator_id": "newholder2", "role": "contributor"}
        )
        
        # Pass ring to new user
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "holder4"},
            json={"to_user_id": "newholder2", "idempotency_key": "pass_ring_4"}
        )
        
        # Old holder tries to append segment
        response = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "holder4"},
            json={"content": "Should fail", "idempotency_key": "seg4"}
        )
        
        # Assert 403 with ring_required code
        assert response.status_code == 403
        error_data = response.json()
        assert error_data["error"]["code"] == "ring_required"
    
    def test_multiple_ring_passes(self):
        """Test ring passing through multiple users"""
        # Create draft
        create_resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "user_a"},
            json={"title": "Ring Test 5", "platform": "x"}
        )
        draft_id = create_resp.json()["data"]["draft_id"]
        
        # Add user_b and user_c as collaborators
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "user_a"},
            params={"collaborator_id": "user_b", "role": "contributor"}
        )
        client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "user_a"},
            params={"collaborator_id": "user_c", "role": "contributor"}
        )
        
        # Pass ring: A -> B
        pass_ab = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "user_a"},
            json={"to_user_id": "user_b", "idempotency_key": "pass_ring_ab"}
        )
        assert pass_ab.status_code == 200, f"Pass A->B failed: {pass_ab.json()}"
        
        # Pass ring: B -> C
        pass_bc = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "user_b"},
            json={"to_user_id": "user_c", "idempotency_key": "pass_ring_bc"}
        )
        assert pass_bc.status_code == 200, f"Pass B->C failed: {pass_bc.json()}"
        
        # Only user_c can append
        response_a = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "user_a"},
            json={"content": "A's segment", "idempotency_key": "seg_a"}
        )
        response_b = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "user_b"},
            json={"content": "B's segment", "idempotency_key": "seg_b"}
        )
        response_c = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "user_c"},
            json={"content": "C's segment", "idempotency_key": "seg_c"}
        )
        
        assert response_a.status_code == 403
        assert response_b.status_code == 403
        assert response_c.status_code == 200
        
        # Verify C's segment was added
        data = response_c.json()["data"]
        assert data["ring_state"]["current_holder_id"] == "user_c"
        assert len(data["segments"]) == 1
        assert data["segments"][0]["content"] == "C's segment"
