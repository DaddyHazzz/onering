"""Platform-specific formatting templates for Phase 8.2 (Auto-Format for Platform)."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Platform(str, Enum):
    """Supported platforms."""
    X = "x"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    BLOG = "blog"

@dataclass
class FormatBlock:
    """Normalized block output (platform-agnostic structure)."""
    type: str  # "heading", "text", "hashtag", "cta", "media_note"
    text: str
    heading: Optional[str] = None

@dataclass
class PlatformTemplate:
    """Platform-specific formatting rules and constraints."""
    name: str
    max_chars_per_block: Optional[int]  # None = unlimited
    block_separator: str  # How blocks are separated in plain text
    max_blocks: Optional[int]
    supports_hashtags: bool
    supports_cta: bool
    supports_media: bool
    heading_style: str  # "markdown" (# ##), "caps" (ALL CAPS), "none"
    line_ending: str  # "\n" or "\r\n"
    hashtag_format: str  # "{hashtag}" or "[{hashtag}]"
    cta_format: str  # "{cta}" or "(CTA: {cta})"

# Platform Configurations
PLATFORMS = {
    Platform.X: PlatformTemplate(
        name="X",
        max_chars_per_block=280,
        block_separator="\n---\n",
        max_blocks=None,
        supports_hashtags=True,
        supports_cta=True,
        supports_media=True,
        heading_style="caps",
        line_ending="\n",
        hashtag_format="#{hashtag}",
        cta_format="{cta}"
    ),
    Platform.YOUTUBE: PlatformTemplate(
        name="YouTube",
        max_chars_per_block=5000,
        block_separator="\n\n",
        max_blocks=None,
        supports_hashtags=False,
        supports_cta=True,
        supports_media=True,
        heading_style="markdown",
        line_ending="\n",
        hashtag_format="{hashtag}",  # YouTube doesn't use # in descriptions
        cta_format="→ {cta}"
    ),
    Platform.INSTAGRAM: PlatformTemplate(
        name="Instagram",
        max_chars_per_block=2200,
        block_separator="\n\n",
        max_blocks=None,
        supports_hashtags=True,
        supports_cta=True,
        supports_media=True,
        heading_style="none",
        line_ending="\n",
        hashtag_format="#{hashtag}",
        cta_format="→ {cta}"
    ),
    Platform.BLOG: PlatformTemplate(
        name="Blog",
        max_chars_per_block=10000,
        block_separator="\n\n",
        max_blocks=None,
        supports_hashtags=False,
        supports_cta=True,
        supports_media=True,
        heading_style="markdown",
        line_ending="\n",
        hashtag_format="{hashtag}",
        cta_format="{cta}"
    ),
}

def get_platform_template(platform: Platform) -> PlatformTemplate:
    """Retrieve template for a platform."""
    return PLATFORMS[platform]

def render_heading(text: str, style: str) -> str:
    """Render heading based on platform style."""
    if style == "markdown":
        return f"## {text}"
    elif style == "caps":
        return text.upper()
    else:
        return text

def render_hashtag(text: str, format_str: str) -> str:
    """Render hashtag based on platform format."""
    clean = text.strip().lstrip("#")
    return format_str.format(hashtag=clean)

def render_cta(text: str, format_str: str) -> str:
    """Render CTA based on platform format."""
    return format_str.format(cta=text.strip())
