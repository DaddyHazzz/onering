"""
backend/tests/test_waitmode_api.py
Tests for Wait Mode API endpoints (Phase 8.4.1 restoration).
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def create_draft(user_id: str = "creator") -> str:
    resp = client.post(
        "/v1/collab/drafts",
        headers={"X-User-Id": user_id},
        json={"title": "WaitMode Draft", "platform": "x"},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["draft_id"]


class TestWaitModeNotes:
    def test_create_list_update_delete_note(self):
        draft_id = create_draft("author1")

        # Create note
        create = client.post(
            f"/v1/wait/drafts/{draft_id}/notes",
            headers={"X-User-Id": "author1"},
            json={"content": "Initial scratch"},
        )
        assert create.status_code == 200
        note = create.json()["data"]
        assert note["content"] == "Initial scratch"

        # List notes
        listing = client.get(
            f"/v1/wait/drafts/{draft_id}/notes",
            headers={"X-User-Id": "author1"},
        )
        assert listing.status_code == 200
        notes = listing.json()["data"]
        assert len(notes) == 1
        assert notes[0]["content"] == "Initial scratch"

        # Update note
        update = client.patch(
            f"/v1/wait/notes/{note["note_id"]}",
            headers={"X-User-Id": "author1"},
            json={"content": "Updated content"},
        )
        assert update.status_code == 200
        assert update.json()["data"]["content"] == "Updated content"

        # Delete note
        delete = client.delete(
            f"/v1/wait/notes/{note["note_id"]}",
            headers={"X-User-Id": "author1"},
        )
        assert delete.status_code == 200
        assert delete.json()["success"] is True


class TestWaitModeSuggestions:
    def test_queue_dismiss_and_consume_requires_ring_holder(self):
        # creator holds the ring initially
        draft_id = create_draft("holder1")
        # Add user2 as collaborator so they can queue/dismiss
        add_collab = client.post(
            f"/v1/collab/drafts/{draft_id}/collaborators",
            headers={"X-User-Id": "holder1"},
            params={"collaborator_id": "user2", "role": "contributor"},
        )
        assert add_collab.status_code == 200

        # queue a suggestion by a different user
        create_sug = client.post(
            f"/v1/wait/drafts/{draft_id}/suggestions",
            headers={"X-User-Id": "user2"},
            json={"kind": "idea", "content": "Try a stronger opening"},
        )
        assert create_sug.status_code == 200
        suggestion = create_sug.json()["data"]
        assert suggestion["status"] == "queued"

        # dismiss suggestion by author
        dismiss = client.post(
            f"/v1/wait/suggestions/{suggestion["suggestion_id"]}/dismiss",
            headers={"X-User-Id": "user2"},
        )
        assert dismiss.status_code == 200
        assert dismiss.json()["data"]["status"] == "dismissed"

        # re-queue another suggestion for consume test
        create_sug2 = client.post(
            f"/v1/wait/drafts/{draft_id}/suggestions",
            headers={"X-User-Id": "user2"},
            json={"kind": "cta", "content": "Add a CTA at end"},
        )
        assert create_sug2.status_code == 200
        suggestion2 = create_sug2.json()["data"]
        assert suggestion2["status"] == "queued"

        # non-holder cannot consume
        consume_forbidden = client.post(
            f"/v1/wait/suggestions/{suggestion2["suggestion_id"]}/consume",
            headers={"X-User-Id": "user2"},
        )
        assert consume_forbidden.status_code == 403

        # ring holder can consume (determine current holder from draft)
        draft_resp = client.get(f"/v1/collab/drafts/{draft_id}")
        assert draft_resp.status_code == 200
        current_holder = draft_resp.json()["data"]["ring_state"]["current_holder_id"]
        consume_ok = client.post(
            f"/v1/wait/suggestions/{suggestion2["suggestion_id"]}/consume",
            headers={"X-User-Id": current_holder},
        )
        assert consume_ok.status_code == 200
        assert consume_ok.json()["data"]["status"] == "consumed"


class TestWaitModeVotes:
    def test_vote_upsert_and_list(self):
        draft_id = create_draft("voter1")
        # Append a segment to have something to vote on
        seg_resp = client.post(
            f"/v1/collab/drafts/{draft_id}/segments",
            headers={"X-User-Id": "voter1"},
            json={"content": "Segment A", "idempotency_key": "segA"},
        )
        assert seg_resp.status_code == 200
        segment_id = seg_resp.json()["data"]["segments"][0]["segment_id"]

        # Upvote
        upvote = client.post(
            f"/v1/wait/drafts/{draft_id}/segments/{segment_id}/vote",
            headers={"X-User-Id": "voter1"},
            json={"value": 1},
        )
        assert upvote.status_code == 200
        assert upvote.json()["data"]["value"] == 1

        # Change vote (upsert)
        downvote = client.post(
            f"/v1/wait/drafts/{draft_id}/segments/{segment_id}/vote",
            headers={"X-User-Id": "voter1"},
            json={"value": -1},
        )
        assert downvote.status_code == 200
        assert downvote.json()["data"]["value"] == -1

        # List votes totals
        totals = client.get(
            f"/v1/wait/drafts/{draft_id}/votes",
            headers={"X-User-Id": "voter1"},
        )
        assert totals.status_code == 200
        data = totals.json()["data"]
        assert "segments" in data
        # Find summary for our segment
        seg_totals = next((s for s in data["segments"] if s["segment_id"] == segment_id), None)
        assert seg_totals is not None
        # At least reflect user's final vote
        assert seg_totals["downvotes"] >= 1
        assert seg_totals["user_vote"] == -1
