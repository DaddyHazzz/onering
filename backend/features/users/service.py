"""
User domain service (Phase 4.0).
- get_or_create_user(user_id)
- get_user(user_id)
- normalize_display_name()
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, insert

from backend.core.database import get_db_session, users as app_users, create_all_tables
from backend.models.user import User


def normalize_display_name(user_id: str, display_name: Optional[str]) -> str:
    return User.normalized_display_name(user_id, display_name)


def get_user(user_id: str) -> Optional[User]:
    with get_db_session() as session:
        row = session.execute(select(app_users).where(app_users.c.user_id == user_id)).first()
        if not row:
            return None
        display = row.display_name or normalize_display_name(row.user_id, None)
        return User(
            user_id=row.user_id,
            created_at=row.created_at,
            display_name=display,
            status=row.status,
        )


def get_or_create_user(user_id: str) -> User:
    # Ensure tables exist (idempotent in tests/dev)
    try:
        create_all_tables()
    except Exception:
        pass

    existing = get_user(user_id)
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    display = normalize_display_name(user_id, None)
    with get_db_session() as session:
        session.execute(
            insert(app_users).values(
                user_id=user_id,
                display_name=display,
                status="active",
                created_at=now,
            )
        )
        # Return created user
        return User(user_id=user_id, created_at=now, display_name=display, status="active")
