from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

from backend.models.challenge import Challenge, ChallengeResult, ChallengeStatus, StreakEffect


# Static catalog of 20 challenge prompts across 4 types
CHALLENGE_CATALOG = [
    # Creative (5)
    ("creative", "Write a 3-tweet thread on something you learned this week."),
    ("creative", "Draft a hook that stops the scroll—test it on yourself first."),
    ("creative", "Rewrite your bio. Make it curiosity-driven, not resume-driven."),
    ("creative", "Share one contrarian belief you hold (no hedging)."),
    ("creative", "Turn a recent mistake into a teaching moment thread."),
    # Reflective (5)
    ("reflective", "Review your last 3 posts. Which one felt most true to you? Why?"),
    ("reflective", "Write down one thing you avoided posting this week. What held you back?"),
    ("reflective", "What's one post you'd write if nobody was watching?"),
    ("reflective", "Look at your most engaged post. What made it resonate?"),
    ("reflective", "Describe your creative voice in 3 words. Are your posts aligned?"),
    # Engagement (5)
    ("engagement", "Reply thoughtfully to 3 posts from creators you admire."),
    ("engagement", "DM one person whose work inspired you this week. Be specific."),
    ("engagement", "Find a small creator (< 1k followers) and amplify their best post."),
    ("engagement", "Comment on a post that challenged your assumptions. No hot takes."),
    ("engagement", "Share someone else's thread with your own takeaway (give credit)."),
    # Growth (5)
    ("growth", "Study 3 viral threads. What pattern do they share?"),
    ("growth", "Run a content experiment: post at a new time and track engagement."),
    ("growth", "Analyze your posting cadence. Are you consistent or sporadic?"),
    ("growth", "Research one platform feature you've never used (spaces, newsletters, etc.)."),
    ("growth", "Review your analytics: what's your best-performing content type?"),
]


class ChallengeService:
    """Deterministic daily challenge assignment and lifecycle management."""

    def __init__(self):
        self._challenges: Dict[str, Challenge] = {}

    def get_today_challenge(
        self,
        *,
        user_id: str,
        today: Optional[date] = None,
        archetype: Optional[str] = None
    ) -> ChallengeResult:
        """
        Get or assign today's challenge for a user (idempotent).
        
        If archetype is provided, softly weight selection toward matching type:
        - builder => favor growth challenges
        - philosopher => favor reflective challenges
        - connector => favor engagement challenges
        - truth_teller => favor creative (clear voice)
        - firestarter => favor creative (bold stance)
        - storyteller => favor creative (narrative)
        """
        current_date = today or self._utc_today()
        challenge = self._get_or_assign(
            user_id=user_id,
            target_date=current_date,
            archetype=archetype
        )
        return self._to_result(challenge)

    def accept_challenge(
        self, *, user_id: str, challenge_id: str, accepted_at: Optional[datetime] = None
    ) -> Tuple[ChallengeResult, List[dict]]:
        """Mark challenge as accepted (idempotent)."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")

        if challenge.user_id != user_id:
            raise ValueError("Challenge does not belong to this user")

        emitted: List[dict] = []
        if challenge.status == "assigned":
            challenge.status = "accepted"
            challenge.accepted_at = accepted_at or datetime.now(timezone.utc)
            emitted.append(
                {
                    "type": "challenge.accepted",
                    "payload": {
                        "userId": user_id,
                        "challengeId": challenge_id,
                        "acceptedAt": challenge.accepted_at.isoformat(),
                    },
                }
            )

        return self._to_result(challenge), emitted

    def complete_challenge(
        self,
        *,
        user_id: str,
        challenge_id: str,
        completed_at: Optional[datetime] = None,
        completion_source: Optional[str] = None,
    ) -> Tuple[ChallengeResult, List[dict]]:
        """Mark challenge as completed (idempotent)."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")

        if challenge.user_id != user_id:
            raise ValueError("Challenge does not belong to this user")

        if challenge.status == "expired":
            raise ValueError("Cannot complete an expired challenge")

        emitted: List[dict] = []
        if challenge.status in ("assigned", "accepted"):
            challenge.status = "completed"
            challenge.completed_at = completed_at or datetime.now(timezone.utc)
            if completion_source:
                challenge.completion_source = completion_source
            emitted.append(
                {
                    "type": "challenge.completed",
                    "payload": {
                        "userId": user_id,
                        "challengeId": challenge_id,
                        "completedAt": challenge.completed_at.isoformat(),
                        "result": "full",
                        "ringEarned": None,
                    },
                }
            )

        return self._to_result(challenge), emitted

    def expire_old_challenges(self, *, cutoff_date: Optional[date] = None) -> int:
        """Mark all challenges before cutoff_date as expired. Returns count."""
        cutoff = cutoff_date or self._utc_today()
        expired_count = 0
        for challenge in self._challenges.values():
            if challenge.date < cutoff and challenge.status in ("assigned", "accepted"):
                challenge.status = "expired"
                expired_count += 1
        return expired_count

    # Internal helpers -------------------------------------------------
    def _get_or_assign(
        self,
        *,
        user_id: str,
        target_date: date,
        archetype: Optional[str] = None
    ) -> Challenge:
        challenge_id = self._generate_challenge_id(user_id, target_date)

        if challenge_id in self._challenges:
            return self._challenges[challenge_id]

        # Deterministic selection from catalog (with archetype soft weighting)
        prompt_index = self._deterministic_index_with_archetype(
            user_id,
            target_date,
            len(CHALLENGE_CATALOG),
            archetype
        )
        challenge_type, prompt = CHALLENGE_CATALOG[prompt_index]

        challenge = Challenge(
            challenge_id=challenge_id,
            user_id=user_id,
            date=target_date,
            type=challenge_type,  # type: ignore
            prompt=prompt,
            status="assigned",
            metadata={"assigned_index": prompt_index, "archetype": archetype or "none"},
        )
        self._challenges[challenge_id] = challenge
        return challenge
    
    @staticmethod
    def _deterministic_index_with_archetype(
        user_id: str,
        target_date: date,
        catalog_size: int,
        archetype: Optional[str]
    ) -> int:
        """
        Deterministic index selection with archetype soft weighting.
        
        Algorithm:
        1. Filter catalog to archetype-preferred types (if archetype provided)
        2. Use hash to pick from filtered subset
        3. Fallback to full catalog if filtered subset empty
        
        Archetype preferences:
        - builder => "growth"
        - philosopher => "reflective"
        - connector => "engagement"
        - truth_teller, firestarter, storyteller => "creative"
        """
        if not archetype:
            return ChallengeService._deterministic_index(user_id, target_date, catalog_size)
        
        # Map archetype to preferred challenge type
        preference_map = {
            "builder": "growth",
            "philosopher": "reflective",
            "connector": "engagement",
            "truth_teller": "creative",
            "firestarter": "creative",
            "storyteller": "creative",
        }
        
        preferred_type = preference_map.get(archetype)
        if not preferred_type:
            return ChallengeService._deterministic_index(user_id, target_date, catalog_size)
        
        # Filter catalog to preferred type
        preferred_indices = [
            i for i, (ctype, _) in enumerate(CHALLENGE_CATALOG)
            if ctype == preferred_type
        ]
        
        if not preferred_indices:
            return ChallengeService._deterministic_index(user_id, target_date, catalog_size)
        
        # Pick from filtered subset deterministically
        hash_input = f"{user_id}:{target_date.isoformat()}:{archetype}"
        hash_val = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        chosen_index = hash_val % len(preferred_indices)
        return preferred_indices[chosen_index]

    @staticmethod
    def _generate_challenge_id(user_id: str, target_date: date) -> str:
        """Generate stable challenge_id from user + date."""
        composite = f"challenge:{user_id}:{target_date.isoformat()}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    @staticmethod
    def _deterministic_index(user_id: str, target_date: date, catalog_size: int) -> int:
        """Deterministic index selection using hash seeding."""
        seed = f"{user_id}:{target_date.isoformat()}"
        hash_val = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        return hash_val % catalog_size

    @staticmethod
    def _utc_today() -> date:
        return datetime.now(timezone.utc).date()

    def _to_result(self, challenge: Challenge) -> ChallengeResult:
        """Convert domain model to API result."""
        next_action_hint = self._get_next_action_hint(challenge)
        streak_effect: StreakEffect = "none"

        if challenge.status == "completed":
            streak_effect = "incremented"  # Caller must verify streak logic
        elif challenge.status in ("assigned", "accepted"):
            streak_effect = "would_increment"

        return ChallengeResult(
            challenge_id=challenge.challenge_id,
            date=challenge.date.isoformat(),
            type=challenge.type,
            prompt=challenge.prompt,
            status=challenge.status,
            next_action_hint=next_action_hint,
            streak_effect=streak_effect,
            metadata=challenge.metadata,
        )

    @staticmethod
    def _get_next_action_hint(challenge: Challenge) -> str:
        """Generate encouraging next-action hint based on status."""
        if challenge.status == "completed":
            return "Nice. You showed up today."
        if challenge.status == "accepted":
            return "You've got this. Share what you create."
        if challenge.status == "expired":
            return "A new challenge awaits tomorrow."
        return "Ready to try? No pressure."


# Singleton service
challenge_service = ChallengeService()
