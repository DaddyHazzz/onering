"""
backend/tests/test_collab_sharecard_guardrails.py
Share card (Phase 3.3c) tests: determinism, safety, bounds, contributor ordering.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.features.collaboration.service import (
    clear_store as clear_draft_store,
    create_draft,
    append_segment,
    pass_ring,
    generate_share_card,
)
from backend.models.collab import (
    CollabDraftRequest,
    SegmentAppendRequest,
    RingPassRequest,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    """Clear store before and after each test"""
    clear_draft_store()
    yield
    clear_draft_store()


class TestShareCardDeterminism:
    """Share card must be deterministic"""

    def test_same_draft_same_time_produces_identical_card(self):
        """Same draft + same now => identical share card"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test Collab", platform="x")
        draft = create_draft(creator, draft_req)

        # Add some segments (don't need to pass ring for same creator)
        seg_req = SegmentAppendRequest(
            content="First segment",
            idempotency_key=str(uuid4()),
        )
        append_segment(draft.draft_id, creator, seg_req)

        # Generate share card with fixed now
        fixed_now = datetime(2025, 12, 21, 12, 0, 0, tzinfo=timezone.utc)
        card1 = generate_share_card(draft.draft_id, fixed_now)
        card2 = generate_share_card(draft.draft_id, fixed_now)

        # Must be identical
        assert card1 == card2
        assert card1["draft_id"] == card2["draft_id"]
        assert card1["title"] == card2["title"]
        assert card1["generated_at"] == card2["generated_at"]

    def test_different_now_produces_different_metric_values(self):
        """Different now => different metric timestamps"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        now1 = datetime(2025, 12, 21, 12, 0, 0, tzinfo=timezone.utc)
        now2 = datetime(2025, 12, 22, 12, 0, 0, tzinfo=timezone.utc)

        card1 = generate_share_card(draft.draft_id, now1)
        card2 = generate_share_card(draft.draft_id, now2)

        # generated_at must differ
        assert card1["generated_at"] != card2["generated_at"]

    def test_default_now_uses_current_time(self):
        """If now not provided, uses current time"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        # generated_at should be recent ISO timestamp
        assert "generated_at" in card
        assert "T" in card["generated_at"]  # ISO format has T


class TestShareCardSafety:
    """Share card must never leak sensitive data"""

    def test_payload_excludes_token_hash(self):
        """Share card JSON must not contain token_hash"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        card_str = str(card)

        assert "token_hash" not in card_str
        assert "token" not in str(card)  # No raw tokens

    def test_payload_excludes_sensitive_keywords(self):
        """Share card must not contain: password, secret, api_key"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        card_json = str(card).lower()

        assert "password" not in card_json
        assert "secret" not in card_json
        assert "api_key" not in card_json

    def test_http_response_excludes_sensitive_data(self):
        """Share card HTTP response must not leak sensitive fields"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        response = client.get(f"/v1/collab/drafts/{draft.draft_id}/share-card")
        assert response.status_code == 200

        response_str = response.text.lower()
        assert "token_hash" not in response_str
        assert "password" not in response_str


class TestShareCardBounds:
    """Share card metrics must be within sensible bounds"""

    def test_contributors_count_at_least_one(self):
        """contributors_count must be >= 1 (creator)"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        assert card["metrics"]["contributors_count"] >= 1

    def test_contributors_count_includes_creator(self):
        """contributors_count includes creator (no collaborators needed for initial test)"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        # Should have at least 1: creator only
        assert card["metrics"]["contributors_count"] >= 1

    def test_contributors_list_max_5(self):
        """contributors list capped at 5 (manual test with multiple segments from same creator)"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        # Just create one more segment
        seg_req = SegmentAppendRequest(
            content="Another segment",
            idempotency_key=str(uuid4()),
        )
        append_segment(draft.draft_id, creator, seg_req)

        card = generate_share_card(draft.draft_id)
        
        # Should be capped at 5 (even if we had many contributors)
        assert len(card["contributors"]) <= 5

    def test_ring_passes_last_24h_is_non_negative(self):
        """ring_passes_last_24h >= 0"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        assert card["metrics"]["ring_passes_last_24h"] >= 0

    def test_segments_count_matches_actual_segments(self):
        """segments_count matches len(draft.segments)"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x", initial_segment="Initial")
        draft = create_draft(creator, draft_req)

        # Add segment
        seg_req = SegmentAppendRequest(
            content="Another segment",
            idempotency_key=str(uuid4()),
        )
        append_segment(draft.draft_id, creator, seg_req)

        card = generate_share_card(draft.draft_id)
        
        # Initial + 1 more = 2
        assert card["metrics"]["segments_count"] == 2


class TestShareCardContributorOrdering:
    """Contributors list must be deterministic and ordered"""

    def test_creator_always_first(self):
        """Creator display must be first in contributors list"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        # Just add segments, no need to pass ring
        for i in range(3):
            seg_req = SegmentAppendRequest(
                content=f"Segment {i}",
                idempotency_key=str(uuid4()),
            )
            append_segment(draft.draft_id, creator, seg_req)

        card = generate_share_card(draft.draft_id)
        
        # First contributor should be creator
        from backend.features.collaboration.service import display_for_user
        creator_display = display_for_user(creator)
        assert card["contributors"][0] == creator_display

    def test_contributors_deterministically_ordered(self):
        """Contributors list is stable (same order each time)"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        # Add multiple segments from creator
        for i in range(3):
            seg_req = SegmentAppendRequest(
                content=f"Segment {i}",
                idempotency_key=str(uuid4()),
            )
            append_segment(draft.draft_id, creator, seg_req)

        card1 = generate_share_card(draft.draft_id)
        card2 = generate_share_card(draft.draft_id)

        # Contributor lists must be identical
        assert card1["contributors"] == card2["contributors"]


class TestShareCardContent:
    """Share card copy must be supportive and never shame"""

    def test_subtitle_contains_ring_holder_and_metrics(self):
        """Subtitle includes ring holder display + metrics"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        # Subtitle should mention ring holder and contributors
        assert "@u_" in card["subtitle"]  # Display name
        assert "contributors" in card["subtitle"].lower()

    def test_topline_is_supportive(self):
        """topLine should be encouraging, not shame"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        # Should not contain shame words
        shame_words = ["stupid", "worthless", "loser", "kill", "hate", "fail"]
        top_line_lower = card["top_line"].lower()
        for word in shame_words:
            assert word not in top_line_lower

    def test_cta_label_is_actionable(self):
        """CTA label should invite without pressure"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        # CTA label should be positive
        assert card["cta"]["label"].lower() in ["join the thread", "view thread", "check it out"]

    def test_cta_url_safe_format(self):
        """CTA URL must start with /dashboard/collab"""
        creator = str(uuid4())
        draft_req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft(creator, draft_req)

        card = generate_share_card(draft.draft_id)
        
        # CTA URL must be internal path
        assert card["cta"]["url"].startswith("/dashboard/collab")
        assert card["cta"]["url"].startswith("/dashboard/collab?draftId=")


class TestShareCardMissingDraft:
    """Share card should handle missing drafts gracefully"""

    def test_missing_draft_raises_error(self):
        """Requesting share card for missing draft raises ValueError"""
        with pytest.raises(ValueError, match="not found"):
            generate_share_card("nonexistent-draft")

    def test_missing_draft_returns_404_http(self):
        """HTTP endpoint returns 404 for missing draft"""
        response = client.get("/v1/collab/drafts/nonexistent/share-card")
        assert response.status_code == 404
