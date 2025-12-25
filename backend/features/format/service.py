"""Format service for generating platform-specific outputs from drafts (Phase 8.2)."""

import logging
from typing import Optional
from pydantic import BaseModel

from backend.models.collab import CollabDraft
from backend.features.format.templates import (
    Platform, PLATFORMS, FormatBlock, render_heading, render_hashtag, render_cta
)
from backend.features.format.validators import (
    FormatOptions, split_long_block, validate_blocks
)

logger = logging.getLogger(__name__)

class PlatformOutput(BaseModel):
    """Output for a single platform."""
    platform: str
    blocks: list[FormatBlock]
    plain_text: str
    character_count: int
    block_count: int
    warnings: list[str]

    class Config:
        from_attributes = True

class FormatGenerateResponse(BaseModel):
    """Response from format generation."""
    draft_id: str
    outputs: dict[str, PlatformOutput]  # platform -> output

    class Config:
        from_attributes = True

class FormatService:
    """Service for deterministic platform-specific formatting."""

    def format_draft(
        self,
        draft: CollabDraft,
        platforms: Optional[list[Platform]] = None,
        options: Optional[FormatOptions] = None,
    ) -> FormatGenerateResponse:
        """Format a draft for one or more platforms.
        
        Args:
            draft: CollabDraft to format
            platforms: Target platforms (None = all)
            options: Formatting options (tone, hashtags, CTA, etc.)
        
        Returns:
            FormatGenerateResponse with platform-specific outputs
        """
        if platforms is None:
            platforms = list(Platform)
        
        options = options or FormatOptions()
        
        outputs = {}
        for platform in platforms:
            logger.debug(f"[format] platform={platform.value}, draft_id={draft.id}")
            output = self._format_for_platform(draft, platform, options)
            outputs[platform.value] = output
        
        return FormatGenerateResponse(
            draft_id=draft.id,
            outputs=outputs
        )

    def _format_for_platform(
        self,
        draft: CollabDraft,
        platform: Platform,
        options: FormatOptions,
    ) -> PlatformOutput:
        """Format draft for a specific platform.
        
        Deterministic algorithm:
        1. Extract segments from draft
        2. Convert each segment to FormatBlock(s)
        3. Apply platform constraints (char limits, block type support)
        4. Render with platform-specific formatting
        5. Return blocks + plain_text + metadata
        """
        template = PLATFORMS[platform]
        blocks = []
        warnings = []
        
        # Step 1: Convert segments to blocks
        for segment in draft.segments:
            segment_blocks = self._segment_to_blocks(segment, platform, options)
            blocks.extend(segment_blocks)
        
        # Step 2: Enforce platform constraints
        valid, errors = validate_blocks(blocks, platform)
        if not valid:
            warnings.extend(errors)
            # Try to split oversized blocks
            blocks = self._enforce_constraints(blocks, template)
        
        # Step 3: Render blocks to plain text
        plain_text = self._render_blocks(blocks, template)
        
        return PlatformOutput(
            platform=platform.value,
            blocks=blocks,
            plain_text=plain_text,
            character_count=len(plain_text),
            block_count=len(blocks),
            warnings=warnings
        )

    def _segment_to_blocks(
        self,
        segment: dict,
        platform: Platform,
        options: FormatOptions,
    ) -> list[FormatBlock]:
        """Convert a draft segment to one or more FormatBlock(s).
        
        A segment typically has:
        - content_type: "text", "image", "code", etc.
        - text: main text content
        - metadata: platform hints, etc.
        """
        blocks = []
        template = PLATFORMS[platform]
        
        content_type = segment.get("content_type", "text")
        text = segment.get("text", "").strip()
        
        if not text:
            return blocks
        
        # Create main text block
        if content_type in ("text", "default"):
            # Split if necessary
            if template.max_chars_per_block and len(text) > template.max_chars_per_block:
                split = split_long_block(text, template.max_chars_per_block)
                blocks.extend([FormatBlock(type="text", text=t) for t in split])
            else:
                blocks.append(FormatBlock(type="text", text=text))
        
        elif content_type == "code":
            # Render code block with language hint
            blocks.append(FormatBlock(type="text", text=f"```\n{text}\n```"))
        
        elif content_type == "quote":
            blocks.append(FormatBlock(type="text", text=f"> {text}"))
        
        elif content_type == "image":
            # Just note that image exists
            blocks.append(FormatBlock(type="media_note", text="[Image included]"))
            if text:  # Image caption
                blocks.append(FormatBlock(type="text", text=text))
        
        # Add hashtags if platform supports
        if options.include_hashtags and template.supports_hashtags:
            hashtags = options.hashtag_suggestions or self._extract_hashtags(segment)
            if options.hashtag_count:
                hashtags = hashtags[:options.hashtag_count]
            for tag in hashtags:
                rendered = render_hashtag(tag, template.hashtag_format)
                blocks.append(FormatBlock(type="hashtag", text=rendered))
        
        # Add CTA if platform supports
        if options.include_cta and template.supports_cta:
            cta = options.cta_text or self._extract_cta(segment)
            if cta:
                rendered = render_cta(cta, template.cta_format)
                blocks.append(FormatBlock(type="cta", text=rendered))
        
        return blocks

    def _extract_hashtags(self, segment: dict) -> list[str]:
        """Extract hashtags from segment metadata."""
        metadata = segment.get("metadata", {})
        return metadata.get("hashtags", [])

    def _extract_cta(self, segment: dict) -> Optional[str]:
        """Extract CTA from segment metadata."""
        metadata = segment.get("metadata", {})
        return metadata.get("cta")

    def _enforce_constraints(
        self,
        blocks: list[FormatBlock],
        template,
    ) -> list[FormatBlock]:
        """Enforce platform constraints, splitting oversized blocks."""
        result = []
        
        for block in blocks:
            if template.max_chars_per_block and len(block.text) > template.max_chars_per_block:
                # Split and append
                split = split_long_block(block.text, template.max_chars_per_block)
                for t in split:
                    result.append(FormatBlock(type=block.type, text=t, heading=block.heading))
            else:
                result.append(block)
        
        # Limit to max_blocks if set
        if template.max_blocks and len(result) > template.max_blocks:
            result = result[:template.max_blocks]
        
        return result

    def _render_blocks(
        self,
        blocks: list[FormatBlock],
        template,
    ) -> str:
        """Render blocks to plain text for a platform."""
        lines = []
        
        for block in blocks:
            if block.type == "heading":
                heading = render_heading(block.text, template.heading_style)
                lines.append(heading)
            elif block.type in ("text", "hashtag", "cta", "media_note"):
                lines.append(block.text)
        
        return template.block_separator.join(lines)


# Singleton instance
format_service = FormatService()
