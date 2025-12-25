"""Wait mode data models (Phase 8.4).

Private artifacts for users waiting for the ring:
- Scratch notes (private notes about draft)
- Queued suggestions (ideas to be consumed by ring holder)
- Segment votes (lightweight feedback)
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class ScratchNote(BaseModel):
    """Private note created by non-ring holder."""
    
    model_config = ConfigDict(frozen=True)
    
    note_id: str = Field(description="UUID")
    draft_id: str
    author_user_id: str
    content: str = Field(min_length=1, max_length=2000)
    created_at: datetime
    updated_at: datetime


class QueuedSuggestion(BaseModel):
    """Queued suggestion waiting for ring holder to consume."""
    
    model_config = ConfigDict(frozen=True)
    
    suggestion_id: str = Field(description="UUID")
    draft_id: str
    author_user_id: str
    kind: Literal["idea", "rewrite", "next_segment", "title", "cta"]
    content: str = Field(min_length=1, max_length=1000)
    status: Literal["queued", "consumed", "dismissed"] = Field(default="queued")
    created_at: datetime
    consumed_at: Optional[datetime] = None
    consumed_by_user_id: Optional[str] = None
    consumed_segment_id: Optional[str] = None


class SegmentVote(BaseModel):
    """Lightweight vote on a draft segment."""
    
    model_config = ConfigDict(frozen=True)
    
    vote_id: str = Field(description="UUID")
    draft_id: str
    segment_id: str
    voter_user_id: str
    value: Literal[1, -1] = Field(description="+1 for upvote, -1 for downvote")
    created_at: datetime


# Request/Response models

class CreateNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class UpdateNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CreateSuggestionRequest(BaseModel):
    kind: Literal["idea", "rewrite", "next_segment", "title", "cta"]
    content: str = Field(min_length=1, max_length=1000)


class VoteRequest(BaseModel):
    value: Literal[1, -1] = Field(description="+1 for upvote, -1 for downvote")


class VoteSummary(BaseModel):
    """Aggregate vote counts for a segment."""
    segment_id: str
    upvotes: int = 0
    downvotes: int = 0
    user_vote: Optional[Literal[1, -1]] = None


class DraftVotesResponse(BaseModel):
    """All vote summaries for a draft."""
    draft_id: str
    segments: list[VoteSummary]
