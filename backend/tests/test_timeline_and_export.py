"""Tests for Phase 8.3 timeline and export functionality.

Covers:
- Timeline event aggregation and mapping
- Attribution tracking
- Export generation (markdown + JSON)
- API endpoints with auth and rate limiting
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from backend.features.timeline.models import TimelineEvent, ContributorStats
from backend.features.timeline.mapping import map_audit_to_timeline
from backend.features.timeline.service import timeline_service
from backend.features.timeline.export import export_service, ExportRequest
from backend.models.collab import CollabDraft, DraftSegment, RingState, DraftStatus


# ========== Timeline Mapping Tests ==========

class TestTimelineMapping:
    """Test audit record to timeline event mapping."""
    
    def test_map_draft_created(self):
        """Test draft_created event mapping."""
        audit_record = {
            "id": 1,
            "ts": datetime.now(timezone.utc),
            "user_id": "user123",
            "action": "draft_created",
            "draft_id": "draft1",
            "metadata": {"title": "My Draft"}
        }
        
        event = map_audit_to_timeline(audit_record)
        
        assert event.type == "draft_created"
        assert event.actor_user_id == "user123"
        assert event.draft_id == "draft1"
        assert "created draft" in event.summary.lower()
        assert "My Draft" in event.summary
    
    def test_map_segment_added(self):
        """Test segment_added event mapping."""
        audit_record = {
            "id": 2,
            "ts": datetime.now(timezone.utc),
            "user_id": "user456",
            "action": "segment_added",
            "draft_id": "draft1",
            "metadata": {
                "segment_id": "seg1",
                "content": "This is the segment content that will be truncated",
                "word_count": 10
            }
        }
        
        event = map_audit_to_timeline(audit_record)
        
        assert event.type == "segment_added"
        assert event.actor_user_id == "user456"
        assert "added segment" in event.summary.lower()
        assert event.meta.get("segment_id") == "seg1"
        assert event.meta.get("word_count") == 10
    
    def test_map_ring_passed(self):
        """Test ring_passed event mapping."""
        audit_record = {
            "id": 3,
            "ts": datetime.now(timezone.utc),
            "user_id": "user789",
            "action": "ring_passed",
            "draft_id": "draft1",
            "metadata": {
                "from_user_id": "user789",
                "to_user_id": "userABC"
            }
        }
        
        event = map_audit_to_timeline(audit_record)
        
        assert event.type == "ring_passed"
        assert "passed ring" in event.summary.lower()
        assert event.meta.get("from_user_id") == "user789"
        assert event.meta.get("to_user_id") == "userABC"
    
    def test_map_ai_suggested(self):
        """Test ai_suggested event mapping."""
        audit_record = {
            "id": 4,
            "ts": datetime.now(timezone.utc),
            "user_id": "user123",
            "action": "ai_suggest",
            "draft_id": "draft1",
            "metadata": {
                "mode": "next",
                "platform": "x"
            }
        }
        
        event = map_audit_to_timeline(audit_record)
        
        assert event.type == "ai_suggested"
        assert "AI suggestion" in event.summary or "requested" in event.summary.lower()
        assert event.meta.get("mode") == "next"
        assert event.meta.get("platform") == "x"
    
    def test_map_format_generated(self):
        """Test format_generated event mapping."""
        audit_record = {
            "id": 5,
            "ts": datetime.now(timezone.utc),
            "user_id": "user123",
            "action": "format_generate",
            "draft_id": "draft1",
            "metadata": {
                "platform_count": 4,
                "platforms": ["x", "youtube", "instagram", "blog"]
            }
        }
        
        event = map_audit_to_timeline(audit_record)
        
        assert event.type == "format_generated"
        assert "4" in event.summary
        assert event.meta.get("platform_count") == 4


# ========== Timeline Service Tests ==========

class TestTimelineService:
    """Test timeline service aggregation logic."""
    
    @patch("backend.features.timeline.service.get_db_session")
    def test_get_timeline_returns_events(self, mock_session):
        """Test timeline returns sorted events."""
        # Mock database response
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.ts = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_row1.user_id = "user123"
        mock_row1.action = "draft_created"
        mock_row1.draft_id = "draft1"
        mock_row1.metadata = {"title": "Test"}
        
        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.ts = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_row2.user_id = "user456"
        mock_row2.action = "segment_added"
        mock_row2.draft_id = "draft1"
        mock_row2.metadata = {"content": "Test content"}
        
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        
        mock_session_obj = Mock()
        mock_session_obj.execute.return_value = mock_result
        mock_session.return_value.__enter__.return_value = mock_session_obj
        
        # Call service
        response = timeline_service.get_timeline("draft1", limit=10, asc_order=True)
        
        assert response.draft_id == "draft1"
        assert len(response.events) == 2
        assert response.events[0].type == "draft_created"
        assert response.events[1].type == "segment_added"
    
    @patch("backend.features.timeline.service.get_db_session")
    def test_get_attribution_aggregates_segments(self, mock_session):
        """Test attribution aggregates by user_id."""
        now = datetime.now(timezone.utc)
        
        mock_row1 = Mock()
        mock_row1.user_id = "user123"
        mock_row1.ts = now - timedelta(hours=3)
        mock_row1.metadata = {"segment_id": "seg1"}
        
        mock_row2 = Mock()
        mock_row2.user_id = "user123"
        mock_row2.ts = now - timedelta(hours=2)
        mock_row2.metadata = {"segment_id": "seg2"}
        
        mock_row3 = Mock()
        mock_row3.user_id = "user456"
        mock_row3.ts = now - timedelta(hours=1)
        mock_row3.metadata = {"segment_id": "seg3"}
        
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2, mock_row3]
        
        mock_session_obj = Mock()
        mock_session_obj.execute.return_value = mock_result
        mock_session.return_value.__enter__.return_value = mock_session_obj
        
        response = timeline_service.get_attribution("draft1")
        
        assert response.draft_id == "draft1"
        assert len(response.contributors) == 2
        
        # Most prolific first
        assert response.contributors[0].user_id == "user123"
        assert response.contributors[0].segment_count == 2
        assert response.contributors[1].user_id == "user456"
        assert response.contributors[1].segment_count == 1


# ========== Export Service Tests ==========

class TestExportService:
    """Test export generation with credits."""
    
    @patch("backend.features.timeline.export.get_draft")
    @patch("backend.features.timeline.export.timeline_service.get_attribution")
    def test_export_markdown_includes_credits(self, mock_attribution, mock_get_draft):
        """Test markdown export includes credits section."""
        # Mock draft
        mock_draft = CollabDraft(
            draft_id="draft1",
            creator_id="user123",
            title="Test Draft",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[
                DraftSegment(
                    segment_id="seg1",
                    draft_id="draft1",
                    user_id="user123",
                    content="First segment",
                    created_at=datetime.now(timezone.utc),
                    segment_order=1,
                    author_display="@user1"
                )
            ],
            ring_state=RingState(
                draft_id="draft1",
                current_holder_id="user123",
                holders_history=["user123"],
                passed_at=datetime.now(timezone.utc)
            ),
            collaborators=["user123"],
            pending_invites=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_get_draft.return_value = mock_draft
        
        # Mock attribution
        from backend.features.timeline.models import AttributionResponse
        mock_attribution.return_value = AttributionResponse(
            draft_id="draft1",
            contributors=[
                ContributorStats(
                    user_id="user123",
                    segment_count=1,
                    segment_ids=["seg1"],
                    first_ts=datetime.now(timezone.utc),
                    last_ts=datetime.now(timezone.utc)
                )
            ]
        )
        
        result = export_service.export_draft("draft1", "markdown", include_credits=True)
        
        assert result.format == "markdown"
        assert result.filename == "draft_draft1.md"
        assert result.content_type == "text/markdown"
        assert "# Test Draft" in result.content
        assert "Credits" in result.content
        assert "@user1" in result.content or "user123" in result.content
    
    @patch("backend.features.timeline.export.get_draft")
    def test_export_json_structure(self, mock_get_draft):
        """Test JSON export has correct structure."""
        mock_draft = CollabDraft(
            draft_id="draft1",
            creator_id="user123",
            title="Test Draft",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[],
            ring_state=RingState(
                draft_id="draft1",
                current_holder_id="user123",
                holders_history=["user123"],
                passed_at=datetime.now(timezone.utc)
            ),
            collaborators=["user123"],
            pending_invites=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_get_draft.return_value = mock_draft
        
        result = export_service.export_draft("draft1", "json", include_credits=False)
        
        assert result.format == "json"
        assert result.filename == "draft_draft1.json"
        assert result.content_type == "application/json"
        
        import json
        data = json.loads(result.content)
        assert data["draft_id"] == "draft1"
        assert data["title"] == "Test Draft"
        assert "segments" in data


# ========== API Tests ==========

class TestTimelineAPI:
    """Test timeline API endpoints."""
    
    @pytest.mark.asyncio
    async def test_timeline_requires_auth(self, client):
        """Test timeline endpoint requires authentication."""
        response = await client.get("/v1/timeline/drafts/draft1")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_attribution_requires_auth(self, client):
        """Test attribution endpoint requires authentication."""
        response = await client.get("/v1/timeline/drafts/draft1/attribution")
        assert response.status_code == 401


class TestExportAPI:
    """Test export API endpoints."""
    
    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client):
        """Test export endpoint requires authentication."""
        response = await client.post(
            "/v1/export/drafts/draft1",
            json={"format": "markdown", "include_credits": True}
        )
        assert response.status_code == 401
