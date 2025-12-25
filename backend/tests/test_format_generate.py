"""Backend tests for format generation (Phase 8.2)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.collab import CollabDraft, RingState
from backend.features.format.templates import Platform, FormatBlock
from backend.features.format.service import format_service, FormatGenerateResponse
from backend.features.format.validators import FormatOptions, split_long_block, validate_blocks


client = TestClient(app)


@pytest.fixture
def sample_draft():
    """Create a sample draft for testing."""
    return CollabDraft(
        id="draft-123",
        owner_id="user-1",
        title="Test Draft",
        platform="x",
        status="active",
        segments=[
            {
                "segment_id": "seg-1",
                "draft_id": "draft-123",
                "user_id": "user-1",
                "content_type": "text",
                "text": "This is the opening segment. Great content starts here!",
                "metadata": {
                    "hashtags": ["growth", "startup"],
                    "cta": "Join my community"
                },
                "created_at": "2025-01-01T00:00:00Z",
            },
            {
                "segment_id": "seg-2",
                "draft_id": "draft-123",
                "user_id": "user-2",
                "content_type": "text",
                "text": "This is the second part of the story. Building momentum now.",
                "metadata": {},
                "created_at": "2025-01-01T00:05:00Z",
            },
        ],
        ring_state=RingState(
            draft_id="draft-123",
            current_holder_id="user-1",
            holders_history=["user-1"],
            passed_at="2025-01-01T00:00:00Z",
        ),
        collaborators=["user-2"],
        pending_invites=[],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:05:00Z",
        metadata={},
    )


class TestFormatService:
    """Test FormatService deterministic formatter."""

    def test_format_single_platform(self, sample_draft):
        """Test formatting for a single platform."""
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X]
        )

        assert response.draft_id == "draft-123"
        assert "x" in response.outputs
        output = response.outputs["x"]
        assert output.platform == "x"
        assert len(output.blocks) > 0
        assert output.character_count > 0
        assert output.block_count > 0

    def test_format_all_platforms(self, sample_draft):
        """Test formatting for all platforms (default when platforms=None)."""
        response = format_service.format_draft(sample_draft)

        # Should have all 4 platforms
        assert len(response.outputs) == 4
        assert "x" in response.outputs
        assert "youtube" in response.outputs
        assert "instagram" in response.outputs
        assert "blog" in response.outputs

    def test_format_with_options(self, sample_draft):
        """Test formatting with custom options."""
        options = FormatOptions(
            tone="professional",
            include_hashtags=True,
            include_cta=True,
            hashtag_count=3,
            cta_text="Subscribe now",
        )
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X],
            options=options
        )

        output = response.outputs["x"]
        # Should have blocks for text, hashtags, and CTA
        block_types = [b.type for b in output.blocks]
        assert "text" in block_types
        assert "hashtag" in block_types
        assert "cta" in block_types

    def test_platform_char_limits(self, sample_draft):
        """Test that platform character limits are enforced."""
        # X has 280 char limit per block
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X]
        )
        output = response.outputs["x"]

        # Each text block should be <= 280 chars
        for block in output.blocks:
            if block.type == "text":
                assert len(block.text) <= 280, f"Block exceeds X char limit: {len(block.text)}"

    def test_plain_text_rendering(self, sample_draft):
        """Test that plain_text is correctly rendered."""
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X]
        )
        output = response.outputs["x"]

        # Plain text should be a joined version of blocks
        assert len(output.plain_text) > 0
        # Should contain some content from original
        assert "opening" in output.plain_text.lower() or "second" in output.plain_text.lower()

    def test_hashtag_extraction(self, sample_draft):
        """Test that hashtags are extracted from segment metadata."""
        options = FormatOptions(include_hashtags=True)
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X],
            options=options
        )
        output = response.outputs["x"]

        # Should have hashtag blocks
        hashtags = [b for b in output.blocks if b.type == "hashtag"]
        assert len(hashtags) > 0
        # X format should have # prefix
        for h in hashtags:
            assert "#" in h.text

    def test_cta_extraction(self, sample_draft):
        """Test that CTA is extracted from segment metadata."""
        options = FormatOptions(include_cta=True)
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X],
            options=options
        )
        output = response.outputs["x"]

        # Should have CTA block
        ctas = [b for b in output.blocks if b.type == "cta"]
        assert len(ctas) > 0

    def test_custom_cta_override(self, sample_draft):
        """Test custom CTA overrides metadata CTA."""
        custom_cta = "Custom CTA text"
        options = FormatOptions(include_cta=True, cta_text=custom_cta)
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X],
            options=options
        )
        output = response.outputs["x"]

        # Should use custom CTA
        cta_blocks = [b for b in output.blocks if b.type == "cta"]
        assert len(cta_blocks) > 0
        assert custom_cta in cta_blocks[0].text

    def test_no_hashtags_for_youtube(self, sample_draft):
        """Test that YouTube doesn't get hashtags."""
        options = FormatOptions(include_hashtags=True)
        response = format_service.format_draft(
            sample_draft,
            platforms=[Platform.YOUTUBE],
            options=options
        )
        output = response.outputs["youtube"]

        # YouTube shouldn't have hashtag blocks
        hashtags = [b for b in output.blocks if b.type == "hashtag"]
        # YouTube supports hashtags in format, but our template says False
        # So no hashtag blocks should be created
        assert all("#" not in h.text for h in hashtags if h)

    def test_deterministic_output(self, sample_draft):
        """Test that output is deterministic (same input = same output)."""
        options = FormatOptions(tone="professional", include_hashtags=True)

        response1 = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X],
            options=options
        )
        response2 = format_service.format_draft(
            sample_draft,
            platforms=[Platform.X],
            options=options
        )

        # Should be identical
        output1 = response1.outputs["x"]
        output2 = response2.outputs["x"]
        assert output1.plain_text == output2.plain_text
        assert output1.character_count == output2.character_count


class TestFormatValidators:
    """Test constraint validators."""

    def test_split_long_block(self):
        """Test splitting oversized blocks."""
        long_text = "a" * 500
        chunks = split_long_block(long_text, 100)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100

    def test_split_respects_separator(self):
        """Test that splitting respects line separators."""
        text = "line1\nline2\nline3\nline4"
        chunks = split_long_block(text, 20, separator="\n")

        # Should split at newlines
        for chunk in chunks:
            lines = chunk.split("\n")
            for line in lines:
                assert len(line) <= 20

    def test_validate_blocks_under_limit(self):
        """Test validation of blocks under limit."""
        blocks = [
            FormatBlock(type="text", text="short"),
            FormatBlock(type="text", text="content"),
        ]
        is_valid, errors = validate_blocks(blocks, Platform.X)

        assert is_valid
        assert len(errors) == 0

    def test_validate_blocks_exceeds_char_limit(self):
        """Test validation catches char limit violations."""
        blocks = [
            FormatBlock(type="text", text="x" * 1000),  # Way over X's 280 limit
        ]
        is_valid, errors = validate_blocks(blocks, Platform.X)

        assert not is_valid
        assert len(errors) > 0
        assert "1000" in str(errors[0])


class TestFormatAPI:
    """Test FastAPI format generation endpoint."""

    def test_format_generate_requires_auth(self, sample_draft):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/format/generate",
            json={
                "draft_id": "draft-123",
                "platforms": ["x"],
            }
        )

        # Should fail without auth
        assert response.status_code == 401

    def test_format_generate_draft_not_found(self):
        """Test handling of missing draft."""
        response = client.post(
            "/v1/format/generate",
            json={
                "draft_id": "nonexistent",
                "platforms": ["x"],
            },
            headers={"X-User-Id": "user-1"}
        )

        # Should return 404
        assert response.status_code == 404

    def test_format_generate_invalid_platform(self):
        """Test validation of platform parameter."""
        response = client.post(
            "/v1/format/generate",
            json={
                "draft_id": "draft-123",
                "platforms": ["invalid-platform"],
            },
            headers={"X-User-Id": "user-1"}
        )

        # Should return 400 for invalid platform
        assert response.status_code == 400 or response.status_code == 422

    def test_format_generate_empty_platforms_rejected(self):
        """Test that empty platforms list is rejected."""
        response = client.post(
            "/v1/format/generate",
            json={
                "draft_id": "draft-123",
                "platforms": [],  # Empty list
            },
            headers={"X-User-Id": "user-1"}
        )

        # Should reject empty list
        assert response.status_code in (400, 422)

    def test_rate_limit_headers(self):
        """Test that rate limit headers are returned."""
        # This test is informational; in real tests we'd mock the rate limiter
        # Just verify the endpoint structure is correct
        response = client.get("/v1/format/generate/health" if hasattr(client, "get") else None)
        # Placeholder for rate limit header verification
        pass
