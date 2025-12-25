"""
backend/tests/test_smart_ring_pass_api.py
Tests for smart ring passing API endpoint.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def create_draft_with_collaborators():
    """Helper: create draft with alice as creator and bob, carol as collaborators."""
    resp = client.post(
        "/v1/collab/drafts",
        headers={"X-User-Id": "alice"},
        json={"title": "Smart Pass Draft", "platform": "x"},
    )
    draft = resp.json()["data"]
    draft_id = draft["draft_id"]
    # Add bob and carol as collaborators
    client.post(
        f"/v1/collab/drafts/{draft_id}/collaborators",
        headers={"X-User-Id": "alice"},
        params={"collaborator_id": "bob", "role": "contributor"},
    )
    client.post(
        f"/v1/collab/drafts/{draft_id}/collaborators",
        headers={"X-User-Id": "alice"},
        params={"collaborator_id": "carol", "role": "contributor"},
    )
    return draft_id


class TestSmartRingPassEndpoint:
    """Test suite for smart ring passing endpoint."""
    
    def test_smart_pass_most_inactive_prefers_no_activity(self):
        """most_inactive: Select collaborator with no activity over active ones."""
        draft_id = create_draft_with_collaborators()
        # Pass ring to bob, add activity
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "alice"},
            json={"to_user_id": "bob", "idempotency_key": "pass_ab"},
        )
        client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "bob"},
            json={"content": "Bob contributed", "idempotency_key": "seg_b1"},
        )
        # Pass ring back to alice
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "bob"},
            json={"to_user_id": "alice", "idempotency_key": "pass_ba"},
        )

        # Smart pass with most_inactive should select carol (no activity)
        resp = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "alice"},
            json={"strategy": "most_inactive", "allow_ai": False, "idempotency_key": "smart1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["selected_to_user_id"] == "carol"
        assert body["strategy_used"] == "most_inactive"
        assert "reasoning" in body
        assert body["data"]["ring_state"]["current_holder_id"] == "carol"
        assert "metrics" in body
        assert body["metrics"]["candidate_count"] == 2
    
    def test_smart_pass_round_robin_cycles_sorted_order(self):
        """round_robin: Cycle through collaborators deterministically in sorted order."""
        draft_id = create_draft_with_collaborators()
        # Make carol current holder
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "alice"},
            json={"to_user_id": "carol", "idempotency_key": "pass_ac"},
        )
        # Round robin from carol should select alice (sorted order: alice, bob, carol)
        resp = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "carol"},
            json={"strategy": "round_robin", "allow_ai": False, "idempotency_key": "smart2"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["selected_to_user_id"] == "alice"
        assert body["strategy_used"] == "round_robin"
        assert body["data"]["ring_state"]["current_holder_id"] == "alice"

    def test_smart_pass_back_to_creator_always_targets_owner(self):
        """back_to_creator: Return ring to draft owner (creator)."""
        draft_id = create_draft_with_collaborators()
        # Make bob current holder
        client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring",
            headers={"X-User-Id": "alice"},
            json={"to_user_id": "bob", "idempotency_key": "pass_ab2"},
        )
        # back_to_creator from bob selects alice (creator)
        resp = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "bob"},
            json={"strategy": "back_to_creator", "allow_ai": False, "idempotency_key": "smart3"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["selected_to_user_id"] == "alice"
        assert body["strategy_used"] == "back_to_creator"
        assert body["data"]["ring_state"]["current_holder_id"] == "alice"
    
    def test_smart_pass_409_no_candidates(self):
        """409 ConflictError: No eligible collaborators to pass to."""
        # Create draft with only alice (creator), no collaborators
        resp = client.post(
            "/v1/collab/drafts",
            headers={"X-User-Id": "alice_solo"},
            json={"title": "Solo Draft", "platform": "x"},
        )
        draft_id = resp.json()["data"]["draft_id"]

        # Smart pass from only holder should fail with 409
        resp = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "alice_solo"},
            json={"strategy": "most_inactive", "allow_ai": False, "idempotency_key": "smart_solo"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "no_collaborator_candidates"

    def test_smart_pass_ring_holder_enforcement(self):
        """403 PermissionError: Non-ring holder cannot smart pass."""
        draft_id = create_draft_with_collaborators()
        # alice holds ring initially

        # bob tries to smart pass (doesn't hold ring)
        resp = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "bob"},
            json={"strategy": "most_inactive", "allow_ai": False, "idempotency_key": "smart_fail"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert "error" in body

    def test_smart_pass_idempotency_no_double_pass(self):
        """Idempotency: Same idempotency_key doesn't pass ring twice."""
        draft_id = create_draft_with_collaborators()
        idempotency_key = "smart_idem_1"

        # First smart pass
        resp1 = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "alice"},
            json={"strategy": "most_inactive", "allow_ai": False, "idempotency_key": idempotency_key},
        )
        assert resp1.status_code == 200
        first_selected = resp1.json()["selected_to_user_id"]

        # Second smart pass with same idempotency key
        resp2 = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "alice"},
            json={"strategy": "most_inactive", "allow_ai": False, "idempotency_key": idempotency_key},
        )
        assert resp2.status_code == 200
        # Should return same selection, not change holder again
        second_selected = resp2.json()["selected_to_user_id"]
        assert first_selected == second_selected

    def test_smart_pass_response_shape(self):
        """Response includes all required fields: selected_to_user_id, strategy_used, reasoning, metrics."""
        draft_id = create_draft_with_collaborators()

        resp = client.post(
            f"/v1/collab/drafts/{draft_id}/pass-ring/smart",
            headers={"X-User-Id": "alice"},
            json={"strategy": "most_inactive", "allow_ai": False, "idempotency_key": "smart_shape"},
        )
        assert resp.status_code == 200
        body = resp.json()
        
        # Verify flattened response fields
        assert "data" in body  # Updated draft
        assert "selected_to_user_id" in body
        assert "strategy_used" in body
        assert "reasoning" in body
        assert "metrics" in body
        
        # Verify metrics structure
        metrics = body["metrics"]
        assert "candidate_count" in metrics
        assert "strategy" in metrics
        assert "computed_from" in metrics
