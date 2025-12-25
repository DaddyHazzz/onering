"""Validators and constraint enforcement for platform formatting."""

from typing import Optional
from pydantic import BaseModel, field_validator, ValidationError

from backend.features.format.templates import Platform, PLATFORMS, FormatBlock

class FormatOptions(BaseModel):
    """Options for formatting (tone, hashtags, CTA)."""
    tone: Optional[str] = None  # "professional", "casual", "witty", etc.
    include_hashtags: bool = True
    include_cta: bool = True
    hashtag_count: Optional[int] = None  # Limit to N hashtags
    hashtag_suggestions: Optional[list[str]] = None  # Pre-defined hashtags
    cta_text: Optional[str] = None  # Custom CTA override
    cta_suggestions: Optional[list[str]] = None  # Pre-defined CTAs

    @field_validator("tone")
    def validate_tone(cls, v):
        valid_tones = {"professional", "casual", "witty", "motivational", "technical"}
        if v and v not in valid_tones:
            raise ValueError(f"tone must be one of {valid_tones}, got {v}")
        return v

    @field_validator("hashtag_count")
    def validate_hashtag_count(cls, v):
        if v is not None and v < 0:
            raise ValueError("hashtag_count must be non-negative")
        return v

class FormatRequest(BaseModel):
    """Format generation request."""
    draft_id: str
    platforms: Optional[list[Platform]] = None  # None = all platforms
    options: Optional[FormatOptions] = None

    @field_validator("platforms")
    def validate_platforms(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("platforms cannot be empty list")
        return v

def split_long_block(text: str, max_chars: int, separator: str = "\n") -> list[str]:
    """Split long text into chunks respecting max_chars constraint.
    
    Args:
        text: Text to split
        max_chars: Maximum characters per chunk
        separator: Line separator (e.g., "\n", ".")
    
    Returns:
        List of chunks, each <= max_chars
    """
    if len(text) <= max_chars:
        return [text]
    
    lines = text.split(separator)
    chunks = []
    current = ""
    
    for line in lines:
        if not current:
            current = line
        elif len(current) + len(separator) + len(line) <= max_chars:
            current += separator + line
        else:
            chunks.append(current)
            current = line
    
    if current:
        chunks.append(current)
    
    return chunks or [text[:max_chars]]  # Fallback for single line > max_chars

def validate_block_length(block: FormatBlock, platform: Platform) -> tuple[bool, Optional[str]]:
    """Validate block against platform constraints.
    
    Args:
        block: Block to validate
        platform: Target platform
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    template = PLATFORMS[platform]
    
    if template.max_chars_per_block:
        if len(block.text) > template.max_chars_per_block:
            return False, f"{platform.value} supports max {template.max_chars_per_block} chars, got {len(block.text)}"
    
    if block.type == "heading" and not template.heading_style or template.heading_style == "none":
        return False, f"{platform.value} does not support headings"
    
    return True, None

def validate_blocks(blocks: list[FormatBlock], platform: Platform) -> tuple[bool, list[str]]:
    """Validate list of blocks against platform constraints.
    
    Args:
        blocks: Blocks to validate
        platform: Target platform
    
    Returns:
        Tuple of (is_valid, errors_list)
    """
    template = PLATFORMS[platform]
    errors = []
    
    if template.max_blocks and len(blocks) > template.max_blocks:
        errors.append(f"Too many blocks: {len(blocks)} > {template.max_blocks} for {platform.value}")
    
    for i, block in enumerate(blocks):
        valid, error = validate_block_length(block, platform)
        if not valid:
            errors.append(f"Block {i}: {error}")
    
    return len(errors) == 0, errors
