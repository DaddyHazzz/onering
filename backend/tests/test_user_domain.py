"""Tests for User domain (Phase 4.0)."""
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app
from backend.features.users.service import get_user, get_or_create_user, normalize_display_name
from backend.features.collaboration.service import create_draft, append_segment
from backend.models.collab import CollabDraftRequest, SegmentAppendRequest
from uuid import uuid4


def test_get_or_create_idempotent():
    uid = f"user-{uuid4()}"
    u1 = get_or_create_user(uid)
    u2 = get_or_create_user(uid)
    assert u1.user_id == u2.user_id
    assert u1.created_at <= u2.created_at  # same or earlier


def test_display_name_normalization_deterministic():
    uid = "deterministic-user"
    handle1 = normalize_display_name(uid, None)
    handle2 = normalize_display_name(uid, None)
    assert handle1 == handle2
    assert handle1.startswith("@u_")


def test_collab_paths_auto_create_users():
    creator = f"creator-{uuid4()}"
    draft = create_draft(creator, CollabDraftRequest(title="Test", platform="x"))
    # Append as current holder should also ensure existence
    req = SegmentAppendRequest(content="Hi", idempotency_key=str(uuid4()))
    append_segment(draft.draft_id, creator, req)
    # Both calls should have created the user record
    u = get_user(creator)
    assert u is not None
    assert u.user_id == creator
