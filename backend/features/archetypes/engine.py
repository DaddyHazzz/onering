"""
Archetype Engine — Pure Deterministic Functions

All functions are pure: same inputs => same outputs.
No external API calls, no randomness beyond deterministic hashing.

Stability Rules:
1. Decay factor (0.92) ensures historical patterns persist
2. Large score gaps resist flipping from single weak signals
3. Merge function averages with recency bias
"""

import hashlib
from typing import Optional
from backend.models.archetype import ArchetypeId


# Keyword patterns for text analysis
ARCHETYPE_KEYWORDS = {
    ArchetypeId.TRUTH_TELLER: [
        "truth", "reality", "actually", "honestly", "fact", "clear", "obvious",
        "directly", "straightforward", "no bs", "cut through", "simple"
    ],
    ArchetypeId.BUILDER: [
        "build", "ship", "create", "launch", "deliver", "implement", "action",
        "execute", "practical", "steps", "how to", "tutorial", "guide"
    ],
    ArchetypeId.PHILOSOPHER: [
        "think", "wonder", "question", "explore", "consider", "reflect",
        "meaning", "why", "nature", "philosophy", "deeper", "perspective"
    ],
    ArchetypeId.CONNECTOR: [
        "community", "together", "we", "us", "share", "connect", "join",
        "collaborate", "help", "support", "feedback", "thoughts", "what do you"
    ],
    ArchetypeId.FIRESTARTER: [
        "energy", "bold", "challenge", "disrupt", "break", "push", "radical",
        "revolution", "wake up", "enough", "change now", "fire"
    ],
    ArchetypeId.STORYTELLER: [
        "story", "once", "remember", "scene", "moment", "detail", "narrative",
        "journey", "experience", "lived", "happened", "imagine"
    ],
}


def score_from_text(text: str, platform: str = "generic") -> dict[str, float]:
    """
    Analyze text content and return archetype scores (0..100).
    
    Algorithm:
    1. Normalize text (lowercase)
    2. Count keyword matches per archetype
    3. Apply platform multipliers (twitter shorter = firestarter boost)
    4. Clamp 0..100
    
    Args:
        text: Draft or published post text
        platform: "twitter", "linkedin", etc. (affects weighting)
    
    Returns:
        dict mapping archetype enum values to scores
    """
    if not text or len(text.strip()) == 0:
        # Empty text: default neutral
        return {archetype.value: 50.0 for archetype in ArchetypeId}
    
    text_lower = text.lower()
    word_count = len(text.split())
    
    # Base scores from keyword matches
    scores = {}
    for archetype, keywords in ARCHETYPE_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in text_lower)
        # Score = base 40 + matches * 10, clamped
        raw_score = 40.0 + (match_count * 10.0)
        scores[archetype.value] = min(100.0, max(0.0, raw_score))
    
    # Platform-specific adjustments
    if platform == "twitter" and word_count < 30:
        # Short tweets favor firestarter + truth_teller
        scores[ArchetypeId.FIRESTARTER.value] = min(100.0, scores[ArchetypeId.FIRESTARTER.value] * 1.2)
        scores[ArchetypeId.TRUTH_TELLER.value] = min(100.0, scores[ArchetypeId.TRUTH_TELLER.value] * 1.1)
    elif platform == "linkedin" and word_count > 100:
        # Long LinkedIn posts favor philosopher + storyteller
        scores[ArchetypeId.PHILOSOPHER.value] = min(100.0, scores[ArchetypeId.PHILOSOPHER.value] * 1.15)
        scores[ArchetypeId.STORYTELLER.value] = min(100.0, scores[ArchetypeId.STORYTELLER.value] * 1.15)
    
    return scores


def score_from_coach_feedback(
    coach_scores: dict[str, int],
    suggestions: list[str],
    warnings: list[str]
) -> dict[str, float]:
    """
    Extract archetype signals from coach feedback.
    
    Algorithm:
    - High clarity score => truth_teller boost
    - Many actionable suggestions => builder boost
    - Reflective suggestions => philosopher boost
    - Questions in suggestions => connector boost
    - Warnings present => slight firestarter penalty (we want energy WITH safety)
    
    Args:
        coach_scores: {clarity, specificity, impact, safety} scores (0..10)
        suggestions: list of suggestion strings
        warnings: list of warning strings
    
    Returns:
        dict mapping archetype enum values to scores
    """
    scores = {archetype.value: 50.0 for archetype in ArchetypeId}
    
    # Clarity => truth_teller
    clarity = coach_scores.get("clarity", 5)
    scores[ArchetypeId.TRUTH_TELLER.value] = 40.0 + (clarity * 6.0)
    
    # Actionable suggestions => builder
    action_words = ["do", "try", "add", "remove", "change", "implement"]
    action_count = sum(
        1 for sugg in suggestions
        for word in action_words
        if word in sugg.lower()
    )
    scores[ArchetypeId.BUILDER.value] = 40.0 + min(60.0, action_count * 12.0)
    
    # Reflective words => philosopher
    reflect_words = ["consider", "think about", "reflect", "explore", "why"]
    reflect_count = sum(
        1 for sugg in suggestions
        for word in reflect_words
        if word in sugg.lower()
    )
    scores[ArchetypeId.PHILOSOPHER.value] = 40.0 + min(60.0, reflect_count * 15.0)
    
    # Questions => connector
    question_count = sum(1 for sugg in suggestions if "?" in sugg)
    scores[ArchetypeId.CONNECTOR.value] = 40.0 + min(60.0, question_count * 15.0)
    
    # Safety score => firestarter modulation
    safety = coach_scores.get("safety", 7)
    # Low safety = high energy but risky; high safety = controlled energy
    scores[ArchetypeId.FIRESTARTER.value] = 40.0 + ((10 - safety) * 4.0)
    
    # Impact + specificity => storyteller
    impact = coach_scores.get("impact", 5)
    specificity = coach_scores.get("specificity", 5)
    scores[ArchetypeId.STORYTELLER.value] = 40.0 + (impact * 3.0) + (specificity * 3.0)
    
    # Clamp all
    for key in scores:
        scores[key] = min(100.0, max(0.0, scores[key]))
    
    return scores


def score_from_challenge_type(challenge_type: str) -> dict[str, float]:
    """
    Map challenge type to archetype boost.
    
    Challenge types (from challenges feature):
    - "first_post", "clarity", "specificity", "vulnerability", "teach", "question"
    
    Returns:
        dict with one or two archetypes boosted, rest at baseline
    """
    scores = {archetype.value: 50.0 for archetype in ArchetypeId}
    
    boost_map = {
        "first_post": ArchetypeId.BUILDER,
        "clarity": ArchetypeId.TRUTH_TELLER,
        "specificity": ArchetypeId.STORYTELLER,
        "vulnerability": ArchetypeId.PHILOSOPHER,
        "teach": ArchetypeId.BUILDER,
        "question": ArchetypeId.CONNECTOR,
        "ship": ArchetypeId.BUILDER,
        "energy": ArchetypeId.FIRESTARTER,
    }
    
    archetype = boost_map.get(challenge_type)
    if archetype:
        scores[archetype.value] = 75.0  # Meaningful boost
    
    return scores


def merge_scores(
    current_scores: dict[str, float],
    new_scores: dict[str, float],
    decay: float = 0.92
) -> dict[str, float]:
    """
    Merge new signal scores into current scores with decay.
    
    Algorithm:
    - current_scores decay by factor (default 0.92)
    - new_scores added at full strength
    - result = (current * decay + new) / (1 + decay)
    - clamped 0..100
    
    This creates stability: old patterns persist but new signals matter.
    
    Args:
        current_scores: existing scores
        new_scores: scores from new signal
        decay: how much historical scores persist (0.92 = 92% retention)
    
    Returns:
        merged scores dict
    """
    merged = {}
    all_keys = set(current_scores.keys()) | set(new_scores.keys())
    
    for key in all_keys:
        current = current_scores.get(key, 50.0)
        new = new_scores.get(key, 50.0)
        
        # Weighted average with decay
        merged_score = (current * decay + new) / (1.0 + decay)
        merged[key] = min(100.0, max(0.0, merged_score))
    
    return merged


def pick_primary_secondary(scores: dict[str, float]) -> tuple[ArchetypeId, Optional[ArchetypeId]]:
    """
    Select primary and optional secondary archetype from scores.
    
    Rules:
    - Primary: highest score
    - Secondary: second highest IF within 15 points of primary
    - If gap > 15 points, no secondary (clear dominance)
    
    Args:
        scores: dict mapping archetype enum values to scores
    
    Returns:
        (primary, secondary) tuple
    """
    if not scores:
        return (ArchetypeId.BUILDER, None)  # Default
    
    # Sort by score descending
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    primary_key = sorted_items[0][0]
    primary_score = sorted_items[0][1]
    
    primary = ArchetypeId(primary_key)
    secondary = None
    
    if len(sorted_items) > 1:
        secondary_key = sorted_items[1][0]
        secondary_score = sorted_items[1][1]
        
        # Secondary only if close enough
        if (primary_score - secondary_score) <= 15.0:
            secondary = ArchetypeId(secondary_key)
    
    return (primary, secondary)


def explain(
    primary: ArchetypeId,
    secondary: Optional[ArchetypeId],
    supporting_signals: list[str]
) -> list[str]:
    """
    Generate exactly 3 supportive bullet points explaining archetype assignment.
    
    Rules:
    - Always supportive, never shameful
    - Never use words: bad, wrong, fail, terrible, useless, stupid
    - Specific to archetype(s)
    - Mention supporting evidence if available
    
    Args:
        primary: primary archetype
        secondary: optional secondary archetype
        supporting_signals: list of signal sources (e.g., ["post", "challenge"])
    
    Returns:
        list of exactly 3 strings (bullet points)
    """
    # Primary archetype descriptions
    primary_bullets = {
        ArchetypeId.TRUTH_TELLER: [
            "You cut through noise with clarity and directness.",
            "Your voice brings honesty to complex topics.",
            "Readers trust your straightforward perspective.",
        ],
        ArchetypeId.BUILDER: [
            "You ship consistently and focus on actionable outcomes.",
            "Your work shows a bias toward execution over theory.",
            "You're building momentum through tangible progress.",
        ],
        ArchetypeId.PHILOSOPHER: [
            "You explore ideas deeply and ask meaningful questions.",
            "Your reflective nature invites others to think differently.",
            "You bring thoughtfulness to every topic you touch.",
        ],
        ArchetypeId.CONNECTOR: [
            "You foster community and invite collaboration.",
            "Your questions create space for others to contribute.",
            "You're building connections through genuine curiosity.",
        ],
        ArchetypeId.FIRESTARTER: [
            "You bring high energy and challenge the status quo.",
            "Your bold voice sparks conversation and change.",
            "You're unafraid to push boundaries with intention.",
        ],
        ArchetypeId.STORYTELLER: [
            "You craft narratives with vivid, specific details.",
            "Your stories make abstract ideas tangible and memorable.",
            "You're building a body of work rich with lived experience.",
        ],
    }
    
    # Get base bullets for primary
    bullets = list(primary_bullets[primary])
    
    # If secondary exists and we have supporting signals, mention blend
    if secondary and len(supporting_signals) > 0:
        blend_map = {
            (ArchetypeId.TRUTH_TELLER, ArchetypeId.BUILDER): "clarity meets execution",
            (ArchetypeId.PHILOSOPHER, ArchetypeId.STORYTELLER): "depth meets narrative",
            (ArchetypeId.CONNECTOR, ArchetypeId.BUILDER): "community meets action",
            (ArchetypeId.FIRESTARTER, ArchetypeId.TRUTH_TELLER): "energy meets clarity",
        }
        blend = blend_map.get((primary, secondary)) or blend_map.get((secondary, primary))
        if blend:
            bullets[2] = f"Your blend of {blend} creates unique value."
    
    # Ensure exactly 3 bullets
    return bullets[:3]


def _hash_signal(user_id: str, date: str, payload: dict) -> str:
    """Generate idempotency key for signal."""
    payload_str = str(sorted(payload.items()))
    combined = f"{user_id}|{date}|{payload_str}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
