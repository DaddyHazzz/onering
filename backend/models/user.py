from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    created_at: datetime
    display_name: Optional[str] = None
    status: str = "active"

    @staticmethod
    def normalized_display_name(user_id: str, display_name: Optional[str] = None) -> str:
        if display_name and display_name.strip():
            return display_name.strip()
        # Deterministic fallback handle
        import hashlib
        h = hashlib.sha1(user_id.encode("utf-8")).hexdigest()
        return f"@u_{h[-6:]}"
