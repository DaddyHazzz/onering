"""
Test Phase 4.2 entitlement usage key mapping.

Ensures the mapping from entitlement_key -> usage_key is centralized,
explicit, and works correctly for all supported entitlements.
"""
import pytest
from backend.features.entitlements.service import (
    ENTITLEMENT_USAGE_KEY_MAP,
    _get_usage_key,
)


class TestUsageKeyMapping:
    """Verify entitlement_key -> usage_key mapping is centralized."""

    def test_mapping_table_contains_all_implemented_entitlements(self):
        """Verify ENTITLEMENT_USAGE_KEY_MAP has all entitlements in use."""
        expected_entitlements = {
            "drafts.max",
            "collaborators.max",
            "segments.max",
        }
        assert set(ENTITLEMENT_USAGE_KEY_MAP.keys()) == expected_entitlements

    def test_drafts_max_maps_to_drafts_created(self):
        """Verify drafts.max -> drafts.created."""
        assert ENTITLEMENT_USAGE_KEY_MAP["drafts.max"] == "drafts.created"

    def test_collaborators_max_maps_to_collaborators_added(self):
        """Verify collaborators.max -> collaborators.added."""
        assert ENTITLEMENT_USAGE_KEY_MAP["collaborators.max"] == "collaborators.added"

    def test_segments_max_maps_to_segments_appended(self):
        """Verify segments.max -> segments.appended."""
        assert ENTITLEMENT_USAGE_KEY_MAP["segments.max"] == "segments.appended"

    def test_get_usage_key_with_explicit_override(self):
        """Verify explicit usage_key overrides mapping."""
        assert _get_usage_key("drafts.max", explicit_usage_key="custom.usage") == "custom.usage"

    def test_get_usage_key_from_mapping(self):
        """Verify _get_usage_key looks up from ENTITLEMENT_USAGE_KEY_MAP."""
        assert _get_usage_key("drafts.max") == "drafts.created"
        assert _get_usage_key("collaborators.max") == "collaborators.added"
        assert _get_usage_key("segments.max") == "segments.appended"

    def test_get_usage_key_unknown_entitlement_falls_back(self, caplog):
        """Verify unmapped entitlement_key uses fallback with warning."""
        result = _get_usage_key("unknown.max")
        assert result == "unknown.created"  # Simple .max -> .created fallback
        assert "[entitlements] unmapped entitlement_key" in caplog.text

    def test_get_usage_key_explicit_overrides_fallback(self):
        """Verify explicit usage_key avoids fallback."""
        result = _get_usage_key("unknown.max", explicit_usage_key="known.usage")
        assert result == "known.usage"
