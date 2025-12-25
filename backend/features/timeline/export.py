"""Export service: generate markdown/json exports with attribution.

Phase 8.3: Export drafts with credit sections.
"""

import json
import logging
from typing import Literal, Optional
from pydantic import BaseModel

from backend.features.collaboration.service import get_draft
from backend.features.timeline.service import timeline_service
from backend.core.errors import NotFoundError

logger = logging.getLogger(__name__)


class ExportRequest(BaseModel):
    """Export request model."""
    format: Literal["markdown", "json"]
    include_credits: bool = True

    class Config:
        frozen = True


class ExportResponse(BaseModel):
    """Export response model."""
    draft_id: str
    format: str
    filename: str
    content_type: str
    content: str

    class Config:
        frozen = True


class ExportService:
    """Service for exporting drafts with attribution."""
    
    def export_draft(
        self,
        draft_id: str,
        export_format: Literal["markdown", "json"],
        include_credits: bool = True
    ) -> ExportResponse:
        """Export a draft in specified format.
        
        Args:
            draft_id: Draft ID to export
            export_format: Output format (markdown or json)
            include_credits: Whether to include credits section
        
        Returns:
            ExportResponse with content and metadata
        
        Raises:
            NotFoundError: If draft not found
        """
        # Fetch draft
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        # Fetch attribution if credits requested
        attribution = None
        if include_credits:
            attribution = timeline_service.get_attribution(draft_id)
        
        # Generate content based on format
        if export_format == "markdown":
            content = self._generate_markdown(draft, attribution)
            filename = f"draft_{draft_id}.md"
            content_type = "text/markdown"
        else:  # json
            content = self._generate_json(draft, attribution)
            filename = f"draft_{draft_id}.json"
            content_type = "application/json"
        
        return ExportResponse(
            draft_id=draft_id,
            format=export_format,
            filename=filename,
            content_type=content_type,
            content=content
        )
    
    def _generate_markdown(self, draft, attribution) -> str:
        """Generate markdown export."""
        lines = []
        
        # Title
        lines.append(f"# {draft.title}\n")
        lines.append(f"*Platform: {draft.platform}*\n")
        lines.append(f"*Status: {draft.status}*\n")
        lines.append(f"*Created: {draft.created_at}*\n")
        lines.append("\n---\n")
        
        # Segments
        for segment in draft.segments:
            # Segment header with author if available
            author_display = segment.author_display or f"@{segment.user_id[-6:]}"
            lines.append(f"\n### Segment {segment.segment_order} — by {author_display}\n")
            lines.append(f"{segment.content}\n")
        
        # Credits section
        if attribution and attribution.contributors:
            lines.append("\n---\n")
            lines.append("\n## Credits\n")
            lines.append("\nThis draft was collaboratively created by:\n")
            
            for contributor in attribution.contributors:
                user_display = f"@{contributor.user_id[-6:]}"
                lines.append(f"- **{user_display}**: {contributor.segment_count} segment(s)")
                lines.append(f" ({contributor.first_ts.strftime('%Y-%m-%d')} to {contributor.last_ts.strftime('%Y-%m-%d')})\n")
        
        return "\n".join(lines)
    
    def _generate_json(self, draft, attribution) -> str:
        """Generate JSON export."""
        export_data = {
            "draft_id": draft.draft_id,
            "title": draft.title,
            "platform": draft.platform,
            "status": draft.status,
            "created_at": draft.created_at.isoformat() if hasattr(draft.created_at, 'isoformat') else str(draft.created_at),
            "updated_at": draft.updated_at.isoformat() if hasattr(draft.updated_at, 'isoformat') else str(draft.updated_at),
            "segments": [
                {
                    "segment_id": seg.segment_id,
                    "segment_order": seg.segment_order,
                    "user_id": seg.user_id,
                    "author_display": seg.author_display or f"@{seg.user_id[-6:]}",
                    "content": seg.content,
                    "created_at": seg.created_at.isoformat() if hasattr(seg.created_at, 'isoformat') else str(seg.created_at),
                }
                for seg in draft.segments
            ],
            "collaborators": draft.collaborators,
        }
        
        # Add credits if available
        if attribution and attribution.contributors:
            export_data["credits"] = [
                {
                    "user_id": contrib.user_id,
                    "segment_count": contrib.segment_count,
                    "segment_ids": contrib.segment_ids,
                    "first_contribution": contrib.first_ts.isoformat() if hasattr(contrib.first_ts, 'isoformat') else str(contrib.first_ts),
                    "last_contribution": contrib.last_ts.isoformat() if hasattr(contrib.last_ts, 'isoformat') else str(contrib.last_ts),
                }
                for contrib in attribution.contributors
            ]
        
        return json.dumps(export_data, indent=2)


# Singleton service instance
export_service = ExportService()
