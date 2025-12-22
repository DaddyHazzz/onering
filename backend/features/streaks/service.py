from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from backend.models.streak import StreakRecord, StreakSnapshot, StreakStatus


class StreakService:
    """Deterministic, idempotent streak state machine with mercy mechanics."""

    def __init__(self, protection_stride: int = 7):
        self._records: Dict[str, StreakRecord] = {}
        self._protection_stride = protection_stride

    def record_posted(
        self,
        *,
        user_id: str,
        post_id: str,
        posted_at: Optional[datetime] = None,
        platform: str | None = None,
    ) -> Tuple[StreakRecord, List[dict]]:
        occurred_at = posted_at or datetime.now(timezone.utc)
        return self._apply_success(
            user_id=user_id,
            event_id=post_id,
            occurred_at=occurred_at,
            reason="post",
            platform=platform or "unspecified",
        )

    def record_scheduled(
        self,
        *,
        user_id: str,
        content_ref: str,
        scheduled_for: Optional[datetime] = None,
    ) -> StreakRecord:
        # Scheduled posts are tracked but do not advance streaks until posted.
        self._ensure_record(user_id)
        return self._records[user_id]

    def record_failed_post(self, *, user_id: str) -> StreakRecord:
        # Explicit no-op to document invariant: failed posts never break streaks.
        return self._ensure_record(user_id)

    def get_state(self, user_id: str) -> dict:
        record = self._ensure_record(user_id)
        status = self._status_for_record(record)
        return {
            "user_id": record.user_id,
            "current_length": record.current_length,
            "longest_length": record.longest_length,
            "last_active_date": record.last_active_date.isoformat() if record.last_active_date else None,
            "grace_used": record.grace_used,
            "decay_state": record.decay_state,
            "status": status,
            "next_action_hint": self._next_action_hint(record, status),
        }

    def history(self, user_id: str) -> List[dict]:
        record = self._ensure_record(user_id)
        return [
            {
                "day": snapshot.day.isoformat(),
                "current_length": snapshot.current_length,
                "longest_length": snapshot.longest_length,
                "status": snapshot.status,
                "reason": snapshot.reason,
            }
            for snapshot in record.history
        ]

    # Internal helpers -------------------------------------------------
    def _apply_success(
        self,
        *,
        user_id: str,
        event_id: Optional[str],
        occurred_at: datetime,
        reason: str,
        platform: str,
    ) -> Tuple[StreakRecord, List[dict]]:
        record = self._ensure_record(user_id)
        day = self._normalize_day(occurred_at)

        if event_id and event_id in record.processed_event_ids:
            return record, []

        if record.last_active_date and day <= record.last_active_date:
            if event_id:
                record.processed_event_ids.add(event_id)
            return record, []

        if day in record.incremented_days:
            if event_id:
                record.processed_event_ids.add(event_id)
            return record, []

        emitted: List[dict] = []

        # First ever action
        if record.last_active_date is None:
            record.current_length = 1
            record.longest_length = 1
            record.last_active_date = day
            record.incremented_days.add(day)
            if event_id:
                record.processed_event_ids.add(event_id)
            snapshot_status: StreakStatus = "active"
            record.history.append(
                StreakSnapshot(
                    day=day,
                    current_length=record.current_length,
                    longest_length=record.longest_length,
                    status=snapshot_status,
                    reason=reason,
                )
            )
            emitted.append(
                {
                    "type": "streak.incremented",
                    "payload": {
                        "userId": user_id,
                        "streakDay": day.isoformat(),
                        "reason": reason,
                        "protectionUsed": False,
                    },
                }
            )
            return record, emitted

        gap_days = max(0, (day - record.last_active_date).days)
        if gap_days == 0:
            if event_id:
                record.processed_event_ids.add(event_id)
            return record, []

        missed_days = max(0, gap_days - 1)
        status: StreakStatus = "active"
        protection_used = False

        uncovered_missed = missed_days
        if missed_days > 0 and not record.grace_used:
            protection_used = True
            record.grace_used = True
            status = "grace"
            uncovered_missed = max(0, missed_days - 1)

        decay_amount = 0
        if uncovered_missed > 0:
            decay_amount = min(record.current_length, max(1, uncovered_missed + 1))
            record.decay_state = "partial"
            status = "decayed"
            missed_day = day - timedelta(days=uncovered_missed)
            emitted.append(
                {
                    "type": "streak.missed",
                    "payload": {
                        "userId": user_id,
                        "missedDay": missed_day.isoformat(),
                        "protectionAvailable": False,
                    },
                }
            )
        else:
            record.decay_state = "none"

        record.current_length = max(1, record.current_length + 1 - decay_amount)
        record.longest_length = max(record.longest_length, record.current_length)
        record.last_active_date = day
        record.incremented_days.add(day)

        if record.current_length % self._protection_stride == 0:
            record.grace_used = False

        snapshot_status = status
        record.history.append(
            StreakSnapshot(
                day=day,
                current_length=record.current_length,
                longest_length=record.longest_length,
                status=snapshot_status,
                reason=reason,
            )
        )

        if event_id:
            record.processed_event_ids.add(event_id)

        emitted.append(
            {
                "type": "streak.incremented",
                "payload": {
                    "userId": user_id,
                    "streakDay": day.isoformat(),
                    "reason": reason,
                    "protectionUsed": protection_used,
                },
            }
        )
        return record, emitted

    def _status_for_record(self, record: StreakRecord) -> StreakStatus:
        if record.decay_state == "partial":
            return "decayed"
        if record.grace_used:
            return "grace"
        return "active"

    @staticmethod
    def _normalize_day(occurred_at: datetime) -> date:
        aware = occurred_at if occurred_at.tzinfo else occurred_at.replace(tzinfo=timezone.utc)
        return aware.astimezone(timezone.utc).date()

    def _next_action_hint(self, record: StreakRecord, status: StreakStatus) -> str:
        if record.current_length == 0:
            return "Share one post today to start your streak."  # never a red zero
        if status == "grace":
            return "You’re protected—post today to lock it in."  # supportive, no shame
        if status == "decayed":
            return "Momentum dipped—post today to rebuild and earn protection."  # recovery-oriented
        days_to_protection = (self._protection_stride - (record.current_length % self._protection_stride)) % self._protection_stride
        if days_to_protection == 0:
            days_to_protection = self._protection_stride
        return f"Post today to stay hot. {days_to_protection} day(s) to your next protection window."

    def _ensure_record(self, user_id: str) -> StreakRecord:
        if user_id not in self._records:
            self._records[user_id] = StreakRecord(user_id=user_id)
        return self._records[user_id]


# Singleton service used by routes
streak_service = StreakService()
