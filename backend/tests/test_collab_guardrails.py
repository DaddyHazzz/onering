"""
backend/tests/test_collab_guardrails.py
Collaboration draft tests: idempotency, permissions, safe fields, determinism.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.main import app
from backend.features.collaboration.service import (
    clear_store,
    create_draft,
    append_segment,
    pass_ring,
    get_draft,
)
from backend.models.collab import (
    CollabDraftRequest,
    SegmentAppendRequest,
    RingPassRequest,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    """Clear store before each test"""
    clear_store()
    yield
    clear_store()


class TestCollabIdempotency:
    """Append and pass-ring operations must be idempotent"""

    def test_append_segment_idempotency(self):
        """Appending same idempotency_key twice should not create duplicate"""
        user_id = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_id, request)

        idempotency_key = str(uuid4())
        append_request = SegmentAppendRequest(
            content="Hello", idempotency_key=idempotency_key
        )

        # First append
        result1 = append_segment(draft.draft_id, user_id, append_request)
        assert len(result1.segments) == 1

        # Second append with same key (should be idempotent)
        result2 = append_segment(draft.draft_id, user_id, append_request)
        assert len(result2.segments) == 1
        assert result2.segments[0].content == "Hello"

    def test_pass_ring_idempotency(self):
        """Passing ring with same idempotency_key twice should be idempotent"""
        user_a = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_a, request)

        idempotency_key = str(uuid4())
        pass_request = RingPassRequest(
            to_user_id=user_a, idempotency_key=idempotency_key  # Pass back to owner
        )

        # First pass
        result1 = pass_ring(draft.draft_id, user_a, pass_request)
        assert result1.ring_state.current_holder_id == user_a
        history_length_1 = len(result1.ring_state.holders_history)

        # Second pass with same key (should be idempotent - no new history entry)
        result2 = pass_ring(draft.draft_id, user_a, pass_request)
        assert result2.ring_state.current_holder_id == user_a
        history_length_2 = len(result2.ring_state.holders_history)
        # Idempotent: same history length (not incremented)
        assert history_length_2 == history_length_1


class TestCollabPermissions:
    """Only ring holder can append; only current holder can pass"""

    def test_only_ring_holder_can_append(self):
        """Non-ring-holder cannot append"""
        from backend.features.collaboration.invite_service import (
            create_invite as create_collab_invite,
            accept_invite,
        )
        from backend.models.invite import CreateInviteRequest, AcceptInviteRequest

        user_a = str(uuid4())
        user_b = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_a, request)

        # Create invite for user_b
        invite_req = CreateInviteRequest(
            target_user_id=user_b, idempotency_key=str(uuid4())
        )
        invite, token = create_collab_invite(draft.draft_id, user_a, invite_req)

        # user_b accepts invite
        accept_req = AcceptInviteRequest(token=token, idempotency_key=str(uuid4()))
        accept_invite(invite.invite_id, user_b, accept_req)

        # Manually add user_b as collaborator on draft (in real app, this is done by invite acceptance webhook)
        from backend.features.collaboration.service import _drafts_store
        draft.collaborators.append(user_b)
        _drafts_store[draft.draft_id] = draft

        # Now pass ring to user_b (who is a collaborator)
        pass_request = RingPassRequest(
            to_user_id=user_b, idempotency_key=str(uuid4())
        )
        pass_ring(draft.draft_id, user_a, pass_request)

        # user_a (no longer ring holder) tries to append
        append_request = SegmentAppendRequest(
            content="Unauthorized", idempotency_key=str(uuid4())
        )
        with pytest.raises(PermissionError):
            append_segment(draft.draft_id, user_a, append_request)

    def test_only_ring_holder_can_pass(self):
        """Non-ring-holder cannot pass ring"""
        user_a = str(uuid4())
        user_b = str(uuid4())
        user_c = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_a, request)

        # user_b tries to pass ring (not holder)
        pass_request = RingPassRequest(
            to_user_id=user_c, idempotency_key=str(uuid4())
        )
        with pytest.raises(PermissionError):
            pass_ring(draft.draft_id, user_b, pass_request)


class TestCollabSafeFields:
    """Draft responses contain only safe, public fields"""

    def test_draft_has_safe_fields(self):
        """Draft should have: draft_id, title, platform, status, segments, ring_state"""
        user_id = str(uuid4())
        request = CollabDraftRequest(
            title="Safe Draft", platform="x", initial_segment="First post"
        )
        draft = create_draft(user_id, request)

        # Check safe fields present
        assert draft.draft_id
        assert draft.title == "Safe Draft"
        assert draft.platform == "x"
        assert draft.status.value in ["active", "locked", "completed"]
        assert len(draft.segments) == 1
        assert draft.ring_state.current_holder_id == user_id

    def test_segment_has_safe_fields(self):
        """Segment should have: segment_id, content, user_id, created_at, segment_order"""
        user_id = str(uuid4())
        request = CollabDraftRequest(
            title="Test", platform="x", initial_segment="Hello world"
        )
        draft = create_draft(user_id, request)
        segment = draft.segments[0]

        assert segment.segment_id
        assert segment.content == "Hello world"
        assert segment.user_id == user_id
        assert segment.created_at
        assert segment.segment_order == 0


class TestCollabRingTracking:
    """Ring holder history and state must be accurate"""

    def test_ring_holder_history(self):
        """Ring holder history should track all passes"""
        creator = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, request)

        # Initial holder
        assert draft.ring_state.current_holder_id == creator
        assert draft.ring_state.holders_history == [creator]

        # Pass ring back to creator multiple times (only valid recipient without collaborators)
        for i in range(1, 4):
            pass_request = RingPassRequest(
                to_user_id=creator, idempotency_key=str(uuid4())
            )
            draft = pass_ring(draft.draft_id, creator, pass_request)
            # After passing back to creator, holder is still creator
            assert draft.ring_state.current_holder_id == creator

    def test_segment_order_increments(self):
        """Segments should have correct order"""
        user_id = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_id, request)

        contents = ["First", "Second", "Third"]
        for i, content in enumerate(contents):
            append_request = SegmentAppendRequest(
                content=content, idempotency_key=str(uuid4())
            )
            draft = append_segment(draft.draft_id, user_id, append_request)

        # Check order
        for i, segment in enumerate(draft.segments):
            assert segment.segment_order == i
            assert segment.content == contents[i]


class TestCollabValidation:
    """Input validation: title length, content bounds, platform"""

    def test_title_max_length(self):
        """Title > 200 chars should fail"""
        long_title = "x" * 201

        # Pydantic should reject before reaching create_draft
        from pydantic_core import ValidationError
        with pytest.raises(ValidationError):
            CollabDraftRequest(title=long_title, platform="x")

    def test_segment_content_max_length(self):
        """Segment content > 500 chars should fail"""
        long_content = "x" * 501

        # Pydantic should reject before reaching append_segment
        from pydantic_core import ValidationError
        with pytest.raises(ValidationError):
            SegmentAppendRequest(
                content=long_content, idempotency_key=str(uuid4())
            )

    def test_platform_values(self):
        """Platform should be x, instagram, tiktok, or youtube"""
        user_id = str(uuid4())
        for platform in ["x", "instagram", "tiktok", "youtube"]:
            request = CollabDraftRequest(title="Test", platform=platform)
            draft = create_draft(user_id, request)
            assert draft.platform == platform


class TestCollabAPI:
    """API endpoint integration tests"""

    def test_create_draft_api(self):
        """POST /v1/collab/drafts creates draft"""
        user_id = str(uuid4())
        res = client.post(
            "/v1/collab/drafts",
            params={"user_id": user_id},
            json={
                "title": "API Test",
                "platform": "x",
                "initial_segment": "Hello from API",
            },
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["title"] == "API Test"
        assert len(data["segments"]) == 1

    def test_get_draft_api(self):
        """GET /v1/collab/drafts/{draft_id} fetches draft"""
        user_id = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_id, request)

        res = client.get(f"/v1/collab/drafts/{draft.draft_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["draft_id"] == draft.draft_id

    def test_list_drafts_api(self):
        """GET /v1/collab/drafts lists user's drafts"""
        user_id = str(uuid4())
        for i in range(3):
            request = CollabDraftRequest(
                title=f"Draft {i}", platform="x"
            )
            create_draft(user_id, request)

        res = client.get("/v1/collab/drafts", params={"user_id": user_id})
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 3

    def test_append_segment_api(self):
        """POST /v1/collab/drafts/{draft_id}/segments appends"""
        user_id = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_id, request)

        res = client.post(
            f"/v1/collab/drafts/{draft.draft_id}/segments",
            params={"user_id": user_id},
            json={"content": "New segment", "idempotency_key": str(uuid4())},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data["segments"]) == 1

    def test_pass_ring_api(self):
        """POST /v1/collab/drafts/{draft_id}/pass-ring passes ring"""
        user_a = str(uuid4())
        request = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(user_a, request)

        res = client.post(
            f"/v1/collab/drafts/{draft.draft_id}/pass-ring",
            params={"user_id": user_a},
            json={"to_user_id": user_a, "idempotency_key": str(uuid4())},  # Pass back to owner
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["ring_state"]["current_holder_id"] == user_a


class TestCollabDeterminism:
    """Draft creation and state should be deterministic (except timestamps)"""

    def test_same_request_creates_same_draft_state(self):
        """Same input produces structurally identical drafts (timestamps may differ slightly)"""
        user_id = str(uuid4())
        request = CollabDraftRequest(
            title="Determinism Test", platform="x", initial_segment="Same content"
        )

        draft1 = create_draft(user_id, request)
        draft2 = create_draft(user_id, request)

        # Same structure
        assert draft1.title == draft2.title
        assert draft1.platform == draft2.platform
        assert draft1.segments[0].content == draft2.segments[0].content
        assert draft1.ring_state.current_holder_id == draft2.ring_state.current_holder_id
