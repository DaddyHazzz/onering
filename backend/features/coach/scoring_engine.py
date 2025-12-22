"""Deterministic coach scoring engine. No external calls."""

import hashlib
import re
from typing import Literal


CoachTone = Literal["hopeful", "neutral", "confrontational", "reflective", "playful"]


class CoachScoringEngine:
    """Pure, deterministic scoring function for coach feedback."""
    
    # Disallowed manipulative patterns (values constraint)
    DISALLOWED_PATTERNS = {
        "faith_aligned": [
            r"\bgoddamn\b|god\s+damn|hell\s+",
            r"\bkill\s+yourself\b|kys\b",
            r"\bmanipulate\b|gaslight\b|trick\b",
        ],
        "optimistic": [
            r"\buseless\b|\bworthless\b|\bhopeless\b|\bpointless\b",
            r"\bkill\s+yourself\b|kys\b",
        ],
        "confrontational": [
            r"\bkill\s+yourself\b|kys\b",
            r"\byou\s+(?:suck|are\s+trash|are\s+worthless)\b",
        ],
        "neutral": [
            r"\bkill\s+yourself\b|kys\b",
        ],
    }
    
    @staticmethod
    def score_draft(
        draft: str,
        platform: Literal["x", "instagram", "linkedin"],
        values_mode: Literal["faith_aligned", "optimistic", "confrontational", "neutral"] = "neutral",
        post_type: Literal["simple", "viral_thread"] = "simple",
    ) -> dict:
        """Score a draft deterministically. Returns dict with all scores and metadata."""
        
        engine = CoachScoringEngine()
        
        # Check for disallowed language
        warnings = engine._check_disallowed_language(draft, values_mode)
        
        # Compute dimension scores
        clarity = engine._score_clarity(draft)
        resonance = engine._score_resonance(draft, post_type)
        platform_fit = engine._score_platform_fit(draft, platform)
        authenticity = engine._score_authenticity(draft, values_mode)
        momentum_alignment = engine._score_momentum_alignment(draft)
        
        # Detect tone
        tone_label, tone_confidence = engine._detect_tone(draft)
        
        # Overall score is weighted average
        overall_score = int(
            clarity * 0.20 +
            resonance * 0.25 +
            platform_fit * 0.20 +
            authenticity * 0.20 +
            momentum_alignment * 0.15
        )
        overall_score = max(0, min(100, overall_score))
        
        # Generate suggestions
        suggestions = engine._generate_suggestions(
            draft, clarity, resonance, platform_fit, authenticity, momentum_alignment, platform, values_mode
        )
        
        # Generate optional revised example (deterministic, template-based)
        revised_example = engine._generate_revised_example(draft, platform, post_type)
        
        return {
            "overall_score": overall_score,
            "clarity": clarity,
            "resonance": resonance,
            "platform_fit": platform_fit,
            "authenticity": authenticity,
            "momentum_alignment": momentum_alignment,
            "tone_label": tone_label,
            "tone_confidence": tone_confidence,
            "warnings": warnings,
            "suggestions": suggestions,
            "revised_example": revised_example,
        }
    
    @staticmethod
    def _check_disallowed_language(draft: str, values_mode: str) -> list[str]:
        """Check for disallowed patterns based on values mode."""
        warnings = []
        patterns = CoachScoringEngine.DISALLOWED_PATTERNS.get(values_mode, [])
        
        draft_lower = draft.lower()
        for pattern in patterns:
            if re.search(pattern, draft_lower):
                warnings.append(f"Disallowed language detected for {values_mode} mode")
                break
        
        # Check for excessive hashtags (universal)
        hashtag_count = len(re.findall(r"#\w+", draft))
        if hashtag_count > 5:
            warnings.append("Too many hashtags (reduces authenticity)")
        
        return warnings
    
    @staticmethod
    def _score_clarity(draft: str) -> int:
        """Score clarity of the draft (0-100)."""
        score = 50  # Base
        
        # Penalize extremely long sentences
        sentences = re.split(r"[.!?]+", draft)
        long_sentences = [s for s in sentences if len(s.strip().split()) > 30]
        if long_sentences:
            score -= min(20, len(long_sentences) * 5)
        
        # Reward structure: line breaks / bullets
        line_breaks = draft.count("\n")
        bullets = len(re.findall(r"^\s*[-•*]\s", draft, re.MULTILINE))
        if line_breaks > 2 or bullets > 0:
            score += 15
        
        # Penalize low punctuation (sign of run-on text)
        punctuation_count = len(re.findall(r"[.,!?;:]", draft))
        word_count = len(draft.split())
        if word_count > 50 and punctuation_count < word_count * 0.05:
            score -= 10
        
        # Reward specific words/phrases suggesting structure
        structure_keywords = ["first", "second", "third", "lastly", "then", "next", "because", "therefore"]
        if any(f"\\b{kw}\\b" in draft.lower() for kw in structure_keywords):
            score += 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_resonance(draft: str, post_type: str) -> int:
        """Score emotional resonance (0-100)."""
        score = 50  # Base
        
        # Reward first-person narrative and specificity
        first_person_count = len(re.findall(r"\b(I\s|me\s|my\s|we\s|us\s|our\s)\b", draft, re.IGNORECASE))
        if first_person_count > 3:
            score += 20
        elif first_person_count > 0:
            score += 10
        
        # Reward concrete details (numbers, dates, names)
        has_numbers = bool(re.search(r"\b\d+\b", draft))
        if has_numbers:
            score += 10
        
        # Penalize "flat corporate tone" (buzzwords without substance)
        buzzwords = [
            "synergy", "leverage", "optimize", "maximize", "utilize", "paradigm shift",
            "low-hanging fruit", "move the needle", "circle back"
        ]
        buzzword_count = sum(1 for bw in buzzwords if bw.lower() in draft.lower())
        if buzzword_count > 2:
            score -= 15
        
        # Reward emotional words (tied to authenticity)
        emotion_words = [
            "learned", "discovered", "struggled", "surprised", "proud", "grateful",
            "inspired", "challenged", "excited", "vulnerable", "changed"
        ]
        emotion_count = sum(1 for ew in emotion_words if ew.lower() in draft.lower())
        if emotion_count > 0:
            score += min(15, emotion_count * 5)
        
        # For viral_thread: reward pattern/insight language
        if post_type == "viral_thread":
            insight_words = ["pattern", "insight", "realize", "revealed", "truth", "actually"]
            insight_count = sum(1 for iw in insight_words if iw.lower() in draft.lower())
            if insight_count > 0:
                score += 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_platform_fit(draft: str, platform: str) -> int:
        """Score platform fit (0-100)."""
        score = 50  # Base
        draft_length = len(draft)
        
        if platform == "x":
            # X: reward brevity, hooks, scannability
            if draft_length < 150:
                score += 20
            elif draft_length < 280:
                score += 10
            elif draft_length > 400:
                score -= 15
            
            # Reward hooks (starts with compelling phrase)
            hook_starts = ["wait", "here's", "this", "thread:", "if you", "most people", "nobody talks about"]
            if any(draft.lower().startswith(h) for h in hook_starts):
                score += 15
            
            # Reward scannability (emojis, capitals for emphasis)
            emojis = len(re.findall(r"[\U0001F300-\U0001F9FF]", draft))
            if emojis > 0:
                score += 10
            
            # Reward line breaks (readability on X)
            if draft.count("\n") > 2:
                score += 10
        
        elif platform == "instagram":
            # Instagram: reward visual language, emotional warmth, captions
            visual_words = ["beautiful", "stunning", "amazing", "gorgeous", "vibrant", "shine", "glow"]
            visual_count = sum(1 for vw in visual_words if vw.lower() in draft.lower())
            if visual_count > 0:
                score += 15
            
            # Reward warmth (less sarcasm)
            sarcasm_markers = ["obviously", "yeah right", "sure"]
            sarcasm_count = sum(1 for sm in sarcasm_markers if sm.lower() in draft.lower())
            if sarcasm_count > 0:
                score -= 10
            else:
                score += 5
            
            # Instagram: acceptable to be longer (captions)
            if 100 < draft_length < 2000:
                score += 10
        
        elif platform == "linkedin":
            # LinkedIn: reward concrete insight + less sarcasm
            insight_words = ["learned", "achieved", "insight", "opportunity", "growth", "team"]
            insight_count = sum(1 for iw in insight_words if iw.lower() in draft.lower())
            if insight_count > 0:
                score += 15
            
            # Penalize extreme sarcasm/confrontation
            sarcasm_markers = ["obviously", "yeah right", "clearly you haven't"]
            sarcasm_count = sum(1 for sm in sarcasm_markers if sm.lower() in draft.lower())
            if sarcasm_count > 0:
                score -= 10
            
            # LinkedIn: slightly longer is fine
            if 150 < draft_length < 1500:
                score += 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_authenticity(draft: str, values_mode: str) -> int:
        """Score authenticity (0-100)."""
        score = 50  # Base
        
        # Penalize excessive hashtags
        hashtag_count = len(re.findall(r"#\w+", draft))
        if hashtag_count > 5:
            score -= 20
        
        # Penalize over-hyped claims ("best ever", "life-changing", etc. without evidence)
        hyperbole = ["best ever", "life-changing", "revolutionary", "game-changer", "100%"]
        hyperbole_count = sum(1 for h in hyperbole if h.lower() in draft.lower())
        if hyperbole_count > 1:
            score -= 10
        
        # Reward concrete experience language
        experience_words = ["I learned", "I messed up", "I discovered", "I failed", "I realized", "I tried"]
        experience_count = sum(1 for ew in experience_words if ew.lower() in draft.lower())
        if experience_count > 0:
            score += 15
        
        # Values mode: check tone alignment
        if values_mode == "faith_aligned":
            # Slightly reward hopeful/reflective tone for faith
            pass  # Tone checks handled elsewhere
        elif values_mode == "optimistic":
            # Penalize excessive negativity
            negative_words = ["never", "impossible", "can't", "won't", "useless", "worthless"]
            negative_count = sum(1 for nw in negative_words if nw.lower() in draft.lower())
            if negative_count > 2:
                score -= 10
        elif values_mode == "confrontational":
            # Less penalty for directness; more reward for hard truths
            bold_words = ["truth", "reality", "actually", "honestly", "real talk"]
            bold_count = sum(1 for bw in bold_words if bw.lower() in draft.lower())
            if bold_count > 0:
                score += 10
        
        return max(0, min(100, score))
    
    @staticmethod
    def _score_momentum_alignment(draft: str) -> int:
        """Score momentum alignment (0-100)."""
        score = 50  # Base
        
        # Reward "today action" / forward motion language
        action_words = [
            "today", "now", "starting", "trying", "building", "creating", "shipping",
            "launching", "testing", "experimenting", "pushing", "moving"
        ]
        action_count = sum(1 for aw in action_words if aw.lower() in draft.lower())
        if action_count > 0:
            score += 15
        
        # Penalize doom spirals (negative without lift)
        doom_words = ["dying", "failing", "broken", "ruined", "lost", "hopeless", "pointless"]
        doom_count = sum(1 for dw in doom_words if dw.lower() in draft.lower())
        
        # Count lift/redemption words
        lift_words = ["but", "however", "instead", "learned", "now", "moving forward", "next"]
        lift_count = sum(1 for lw in lift_words if lw.lower() in draft.lower())
        
        if doom_count > 0 and lift_count == 0:
            score -= 15
        elif doom_count > 0 and lift_count > 0:
            score += 5  # Doom + lift = redemption arc
        
        return max(0, min(100, score))
    
    @staticmethod
    def _detect_tone(draft: str) -> tuple[str, float]:
        """Detect tone deterministically. Returns (tone_label, confidence)."""
        lower_draft = draft.lower()
        
        # Score each tone
        hopeful_indicators = ["excited", "looking forward", "can't wait", "inspired", "grateful", "grateful"]
        hopeful_score = sum(1 for hi in hopeful_indicators if hi in lower_draft)
        
        reflective_indicators = ["realized", "learned", "discovered", "thought", "reflected", "wondered", "considered"]
        reflective_score = sum(1 for ri in reflective_indicators if ri in lower_draft)
        
        confrontational_indicators = ["actually", "honestly", "real talk", "truth is", "let's be clear", "obviously"]
        confrontational_score = sum(1 for ci in confrontational_indicators if ci in lower_draft)
        
        playful_indicators = ["haha", "lol", "😂", "hilarious", "funny", "joking", "playful"]
        playful_score = sum(1 for pi in playful_indicators if pi in lower_draft)
        
        # Default neutral; highest score wins
        scores = {
            "hopeful": hopeful_score,
            "reflective": reflective_score,
            "confrontational": confrontational_score,
            "playful": playful_score,
            "neutral": 0,  # Default tiebreaker
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return ("neutral", 0.5)
        
        tone_label = max(scores, key=scores.get)
        confidence = min(0.95, 0.5 + (max_score * 0.15))  # Confidence scales with indicator count
        
        return (tone_label, confidence)
    
    @staticmethod
    def _generate_suggestions(
        draft: str,
        clarity: int,
        resonance: int,
        platform_fit: int,
        authenticity: int,
        momentum_alignment: int,
        platform: str,
        values_mode: str,
    ) -> list[str]:
        """Generate 3-5 concrete, actionable suggestions."""
        suggestions = []
        
        # Suggestion 1: Clarity
        if clarity < 60:
            if len(draft.split()) > 100 and draft.count(".") < 3:
                suggestions.append("Break longer passages into shorter sentences for clarity")
            else:
                suggestions.append("Add more structure (bullet points or line breaks)")
        
        # Suggestion 2: Resonance
        if resonance < 60:
            if not any(w in draft.lower() for w in ["i ", "me ", "my ", "we "]):
                suggestions.append("Share a personal story or experience (use 'I' statements)")
            else:
                suggestions.append("Add a specific detail or example to strengthen resonance")
        
        # Suggestion 3: Platform Fit
        if platform_fit < 60:
            if platform == "x" and len(draft) > 300:
                suggestions.append(f"Tighten for X (current: {len(draft)} chars, consider <280)")
            elif platform == "linkedin" and "learned" not in draft.lower() and "insight" not in draft.lower():
                suggestions.append("Add a concrete insight or lesson to improve LinkedIn fit")
            elif platform == "instagram" and not any(w in draft.lower() for w in ["beautiful", "amazing", "vibrant"]):
                suggestions.append("Use more vivid, visual language for Instagram")
        
        # Suggestion 4: Authenticity
        if authenticity < 60:
            hashtag_count = len(re.findall(r"#\w+", draft))
            if hashtag_count > 5:
                suggestions.append("Reduce hashtags to focus on substance")
            elif any(h in draft.lower() for h in ["best ever", "game-changer", "revolutionary"]):
                suggestions.append("Replace hype words with concrete outcomes")
            else:
                suggestions.append("Share vulnerability or a real challenge you faced")
        
        # Suggestion 5: Momentum Alignment
        if momentum_alignment < 60:
            if not any(w in draft.lower() for w in ["today", "now", "trying", "building", "shipping"]):
                suggestions.append("Signal immediate action: what are you doing today or this week?")
            else:
                suggestions.append("Add clarity on your next step or learning from this")
        
        # Cap at 5 suggestions
        return suggestions[:5]
    
    @staticmethod
    def _generate_revised_example(draft: str, platform: str, post_type: str) -> str | None:
        """Generate a template-based revised example (deterministic). Max 600 chars."""
        
        # Extract key elements
        sentences = [s.strip() for s in re.split(r"[.!?]+", draft) if s.strip()]
        first_sentence = sentences[0] if sentences else ""
        
        # Build deterministic revision based on platform + post_type
        if platform == "x" and post_type == "simple":
            # X simple: hook + takeaway
            if first_sentence:
                revision = f"{first_sentence}\n\nKey takeaway: [your main insight]\n\nNext step: [what you're doing about it]"
            else:
                revision = "Hook your reader in the first line.\n\nKey takeaway: [your main insight]\n\nNext step: [what you're doing about it]"
        
        elif platform == "x" and post_type == "viral_thread":
            # X thread: numbered with hooks
            revision = "1/ Pattern I noticed:\n[Hook]\n\n2/ Why it matters:\n[Insight]\n\n3/ What to do:\n[Action]"
        
        elif platform == "linkedin":
            # LinkedIn: story + lesson + invitation
            revision = "Here's what I learned:\n\n[Your story]\n\nThe insight:\n[What it means]\n\nNow over to you:\n[Invitation]"
        
        elif platform == "instagram":
            # Instagram: visual + feeling + call-to-action
            revision = "[Visual description or emoji]\n\n[What you're feeling or thinking]\n\nWhat about you? [Question]"
        
        else:
            revision = None
        
        # Ensure under 600 chars
        if revision and len(revision) > 600:
            revision = revision[:597] + "..."
        
        return revision
