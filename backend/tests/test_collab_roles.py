"""Role guardrails for collaboration (Phase 4.0)."""
import pytest
from uuid import uuid4
from backend.features.collaboration.service import create_draft, append_segment
from backend.features.collaboration.persistence import DraftPersistence
from backend.models.collab import CollabDraftRequest, SegmentAppendRequest
from backend.core.database import check_connection


@pytest.mark.skipif(not check_connection(), reason="PostgreSQL required for role persistence test")
def test_append_requires_owner_or_collaborator_and_ring_holder(clean_db=None):
    creator = str(uuid4())
    other = str(uuid4())
    draft = create_draft(creator, CollabDraftRequest(title="Role Test", platform="x"))

    # Not ring holder: other cannot append even if added later
    with pytest.raises(Exception):
        append_segment(draft.draft_id, other, SegmentAppendRequest(content="nope", idempotency_key=str(uuid4())))

    # Add other as collaborator via persistence
    DraftPersistence.add_collaborator(draft.draft_id, other, role='collaborator')

    # Still cannot append unless ring is passed; creator is ring holder
    with pytest.raises(Exception):
        append_segment(draft.draft_id, other, SegmentAppendRequest(content="still no", idempotency_key=str(uuid4())))

    # Creator can append (owner + ring holder)
    append_segment(draft.draft_id, creator, SegmentAppendRequest(content="ok", idempotency_key=str(uuid4())))
