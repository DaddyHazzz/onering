"""Prompt templates for ring-aware AI suggestions (Phase 8.1).

These prompts are deterministic and used to shape the tone of AI suggestions
per platform. They are not sent to an external model here but kept for
consistency and future adapter use.
"""

BASE_PROMPT = (
    "You are a ring-aware collaboration coach. You never modify drafts "
    "directly. You suggest the next turn, rewrite options, or a concise "
    "summary while respecting ring ownership. You avoid shame language and "
    "keep guidance supportive and direct."
)

PLATFORM_PROMPTS = {
    "default": {
        "tone": "direct and supportive",
        "structure": "Short paragraphs with clear next steps.",
    },
    "x": {
        "tone": "punchy, first-person, concise",
        "structure": "One to two tight sentences; avoid numbering.",
    },
    "youtube": {
        "tone": "conversational and spoken",
        "structure": "Hook + payoff + CTA, formatted as talking beats.",
    },
    "instagram": {
        "tone": "warm and hook-first",
        "structure": "Caption with a hook, then one-liner CTA; light hashtags only if helpful.",
    },
    "blog": {
        "tone": "structured and clear",
        "structure": "Lead sentence + supporting detail; avoid fluff.",
    },
}
