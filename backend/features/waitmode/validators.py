"""Wait mode validators (Phase 8.4)."""

from pydantic import BaseModel, Field, validator
from typing import Literal, Optional


class WaitModeFilters(BaseModel):
    """Query filters for wait mode lists."""
    
    status: Optional[Literal["queued", "consumed", "dismissed"]] = None
    shared: Optional[bool] = False  # For future: shared suggestions visible to others
