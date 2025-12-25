"""Wait mode service (Phase 8.4).

Manages scratch notes, queued suggestions, and segment votes for non-ring holders.
All operations enforce:
- Collaborator access to draft
- Author-only privacy for notes/suggestions
- Ring holder requirement for consuming suggestions
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update, delete, and_, func
from backend.core.database import get_db_session, wait_notes, wait_suggestions, wait_votes
from backend.core.errors import NotFoundError, PermissionError, ValidationError
from backend.features.collaboration.service import get_draft
from backend.features.audit.service import record_audit_event
from backend.core.tracing import start_span
from backend.core.logging import get_request_id
from backend.features.waitmode.models import (
    ScratchNote,
    QueuedSuggestion,
    SegmentVote,
    VoteSummary,
    DraftVotesResponse,
)


class WaitModeService:
    """Service for wait mode operations."""
    
    def _check_collaborator_access(self, draft_id: str, user_id: str) -> None:
        """Verify user is creator or collaborator on draft."""
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        # Check if user is creator or collaborator
        if draft.creator_id != user_id and user_id not in draft.collaborators:
            raise PermissionError(f"User {user_id} is not a collaborator on draft {draft_id}")
    
    def _check_ring_holder(self, draft_id: str, user_id: str) -> None:
        """Verify user currently holds the ring."""
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        if draft.ring_state.current_holder_id != user_id:
            raise PermissionError(f"User {user_id} does not hold the ring for draft {draft_id}")
    
    # ===== SCRATCH NOTES =====
    
    def create_note(
        self,
        draft_id: str,
        author_user_id: str,
        content: str,
        request_id: Optional[str] = None,
    ) -> ScratchNote:
        """Create a private scratch note."""
        with start_span("waitmode.create_note", {"draft_id": draft_id, "user_id": author_user_id}):
            self._check_collaborator_access(draft_id, author_user_id)
            
            note_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            with get_db_session() as session:
                session.execute(
                    wait_notes.insert().values(
                        note_id=note_id,
                        draft_id=draft_id,
                        author_user_id=author_user_id,
                        content=content,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.commit()
            
            record_audit_event(
                action="wait_note_created",
                user_id=author_user_id,
                draft_id=draft_id,
                request_id=request_id or get_request_id(),
                metadata={"note_id": note_id},
            )
            
            return ScratchNote(
                note_id=note_id,
                draft_id=draft_id,
                author_user_id=author_user_id,
                content=content,
                created_at=now,
                updated_at=now,
            )
    
    def list_notes(
        self,
        draft_id: str,
        user_id: str,
    ) -> List[ScratchNote]:
        """List notes for a draft (author-only)."""
        with start_span("waitmode.list_notes", {"draft_id": draft_id, "user_id": user_id}):
            self._check_collaborator_access(draft_id, user_id)
            
            with get_db_session() as session:
                result = session.execute(
                    select(wait_notes)
                    .where(and_(
                        wait_notes.c.draft_id == draft_id,
                        wait_notes.c.author_user_id == user_id,
                    ))
                    .order_by(wait_notes.c.created_at.desc())
                )
                rows = result.fetchall()
            
            return [
                ScratchNote(
                    note_id=row.note_id,
                    draft_id=row.draft_id,
                    author_user_id=row.author_user_id,
                    content=row.content,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]
    
    def update_note(
        self,
        note_id: str,
        user_id: str,
        content: str,
        request_id: Optional[str] = None,
    ) -> ScratchNote:
        """Update a note (author only)."""
        with start_span("waitmode.update_note", {"note_id": note_id, "user_id": user_id}):
            with get_db_session() as session:
                # Fetch existing note
                result = session.execute(
                    select(wait_notes).where(wait_notes.c.note_id == note_id)
                )
                row = result.fetchone()
                
                if not row:
                    raise NotFoundError(f"Note {note_id} not found")
                
                if row.author_user_id != user_id:
                    raise PermissionError(f"User {user_id} is not the author of note {note_id}")
                
                now = datetime.now(timezone.utc)
                session.execute(
                    update(wait_notes)
                    .where(wait_notes.c.note_id == note_id)
                    .values(content=content, updated_at=now)
                )
                session.commit()
            
            record_audit_event(
                action="wait_note_updated",
                user_id=user_id,
                draft_id=row.draft_id,
                request_id=request_id or get_request_id(),
                metadata={"note_id": note_id},
            )
            
            return ScratchNote(
                note_id=note_id,
                draft_id=row.draft_id,
                author_user_id=row.author_user_id,
                content=content,
                created_at=row.created_at,
                updated_at=now,
            )
    
    def delete_note(
        self,
        note_id: str,
        user_id: str,
        request_id: Optional[str] = None,
    ) -> None:
        """Delete a note (author only)."""
        with start_span("waitmode.delete_note", {"note_id": note_id, "user_id": user_id}):
            with get_db_session() as session:
                # Fetch to verify ownership
                result = session.execute(
                    select(wait_notes).where(wait_notes.c.note_id == note_id)
                )
                row = result.fetchone()
                
                if not row:
                    raise NotFoundError(f"Note {note_id} not found")
                
                if row.author_user_id != user_id:
                    raise PermissionError(f"User {user_id} is not the author of note {note_id}")
                
                session.execute(
                    delete(wait_notes).where(wait_notes.c.note_id == note_id)
                )
                session.commit()
            
            record_audit_event(
                action="wait_note_deleted",
                user_id=user_id,
                draft_id=row.draft_id,
                request_id=request_id or get_request_id(),
                metadata={"note_id": note_id},
            )
    
    # ===== QUEUED SUGGESTIONS =====
    
    def create_suggestion(
        self,
        draft_id: str,
        author_user_id: str,
        kind: str,
        content: str,
        request_id: Optional[str] = None,
    ) -> QueuedSuggestion:
        """Create a queued suggestion."""
        with start_span("waitmode.create_suggestion", {"draft_id": draft_id, "user_id": author_user_id, "kind": kind}):
            self._check_collaborator_access(draft_id, author_user_id)
            
            suggestion_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            with get_db_session() as session:
                session.execute(
                    wait_suggestions.insert().values(
                        suggestion_id=suggestion_id,
                        draft_id=draft_id,
                        author_user_id=author_user_id,
                        kind=kind,
                        content=content,
                        status="queued",
                        created_at=now,
                    )
                )
                session.commit()
            
            record_audit_event(
                action="wait_suggestion_created",
                user_id=author_user_id,
                draft_id=draft_id,
                request_id=request_id or get_request_id(),
                metadata={"suggestion_id": suggestion_id, "kind": kind},
            )
            
            return QueuedSuggestion(
                suggestion_id=suggestion_id,
                draft_id=draft_id,
                author_user_id=author_user_id,
                kind=kind,
                content=content,
                status="queued",
                created_at=now,
            )
    
    def list_suggestions(
        self,
        draft_id: str,
        user_id: str,
        status: Optional[str] = None,
    ) -> List[QueuedSuggestion]:
        """List suggestions for a draft (author-only by default)."""
        with start_span("waitmode.list_suggestions", {"draft_id": draft_id, "user_id": user_id, "status": status}):
            self._check_collaborator_access(draft_id, user_id)
            
            with get_db_session() as session:
                query = select(wait_suggestions).where(and_(
                    wait_suggestions.c.draft_id == draft_id,
                    wait_suggestions.c.author_user_id == user_id,
                ))
                
                if status:
                    query = query.where(wait_suggestions.c.status == status)
                
                query = query.order_by(wait_suggestions.c.created_at.desc())
                
                result = session.execute(query)
                rows = result.fetchall()
            
            return [
                QueuedSuggestion(
                    suggestion_id=row.suggestion_id,
                    draft_id=row.draft_id,
                    author_user_id=row.author_user_id,
                    kind=row.kind,
                    content=row.content,
                    status=row.status,
                    created_at=row.created_at,
                    consumed_at=row.consumed_at,
                    consumed_by_user_id=row.consumed_by_user_id,
                    consumed_segment_id=row.consumed_segment_id,
                )
                for row in rows
            ]
    
    def dismiss_suggestion(
        self,
        suggestion_id: str,
        user_id: str,
        request_id: Optional[str] = None,
    ) -> QueuedSuggestion:
        """Dismiss a suggestion (author only)."""
        with start_span("waitmode.dismiss_suggestion", {"suggestion_id": suggestion_id, "user_id": user_id}):
            with get_db_session() as session:
                result = session.execute(
                    select(wait_suggestions).where(wait_suggestions.c.suggestion_id == suggestion_id)
                )
                row = result.fetchone()
                
                if not row:
                    raise NotFoundError(f"Suggestion {suggestion_id} not found")
                
                if row.author_user_id != user_id:
                    raise PermissionError(f"User {user_id} is not the author of suggestion {suggestion_id}")
                
                session.execute(
                    update(wait_suggestions)
                    .where(wait_suggestions.c.suggestion_id == suggestion_id)
                    .values(status="dismissed")
                )
                session.commit()
            
            record_audit_event(
                action="wait_suggestion_dismissed",
                user_id=user_id,
                draft_id=row.draft_id,
                request_id=request_id or get_request_id(),
                metadata={"suggestion_id": suggestion_id},
            )
            
            return QueuedSuggestion(
                suggestion_id=suggestion_id,
                draft_id=row.draft_id,
                author_user_id=row.author_user_id,
                kind=row.kind,
                content=row.content,
                status="dismissed",
                created_at=row.created_at,
            )
    
    def consume_suggestion(
        self,
        suggestion_id: str,
        user_id: str,
        segment_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> QueuedSuggestion:
        """Consume a suggestion (ring holder only)."""
        with start_span("waitmode.consume_suggestion", {"suggestion_id": suggestion_id, "user_id": user_id}):
            with get_db_session() as session:
                result = session.execute(
                    select(wait_suggestions).where(wait_suggestions.c.suggestion_id == suggestion_id)
                )
                row = result.fetchone()
                
                if not row:
                    raise NotFoundError(f"Suggestion {suggestion_id} not found")
                
                # Check ring holder permission
                self._check_ring_holder(row.draft_id, user_id)
                
                now = datetime.now(timezone.utc)
                session.execute(
                    update(wait_suggestions)
                    .where(wait_suggestions.c.suggestion_id == suggestion_id)
                    .values(
                        status="consumed",
                        consumed_at=now,
                        consumed_by_user_id=user_id,
                        consumed_segment_id=segment_id,
                    )
                )
                session.commit()
            
            record_audit_event(
                action="wait_suggestion_consumed",
                user_id=user_id,
                draft_id=row.draft_id,
                request_id=request_id or get_request_id(),
                metadata={"suggestion_id": suggestion_id, "segment_id": segment_id},
            )
            
            return QueuedSuggestion(
                suggestion_id=suggestion_id,
                draft_id=row.draft_id,
                author_user_id=row.author_user_id,
                kind=row.kind,
                content=row.content,
                status="consumed",
                created_at=row.created_at,
                consumed_at=now,
                consumed_by_user_id=user_id,
                consumed_segment_id=segment_id,
            )
    
    # ===== SEGMENT VOTES =====
    
    def vote_segment(
        self,
        draft_id: str,
        segment_id: str,
        voter_user_id: str,
        value: int,
        request_id: Optional[str] = None,
    ) -> SegmentVote:
        """Vote on a segment (upsert behavior)."""
        with start_span("waitmode.vote_segment", {"draft_id": draft_id, "segment_id": segment_id, "user_id": voter_user_id, "value": value}):
            self._check_collaborator_access(draft_id, voter_user_id)
            
            vote_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            with get_db_session() as session:
                # Check if vote exists
                result = session.execute(
                    select(wait_votes).where(and_(
                        wait_votes.c.segment_id == segment_id,
                        wait_votes.c.voter_user_id == voter_user_id,
                    ))
                )
                existing = result.fetchone()
                
                if existing:
                    # Update existing vote
                    session.execute(
                        update(wait_votes)
                        .where(and_(
                            wait_votes.c.segment_id == segment_id,
                            wait_votes.c.voter_user_id == voter_user_id,
                        ))
                        .values(value=value)
                    )
                    vote_id = existing.vote_id
                else:
                    # Insert new vote
                    session.execute(
                        wait_votes.insert().values(
                            vote_id=vote_id,
                            draft_id=draft_id,
                            segment_id=segment_id,
                            voter_user_id=voter_user_id,
                            value=value,
                            created_at=now,
                        )
                    )
                
                session.commit()
            
            record_audit_event(
                action="wait_vote_set",
                user_id=voter_user_id,
                draft_id=draft_id,
                request_id=request_id or get_request_id(),
                metadata={"segment_id": segment_id, "value": value},
            )
            
            return SegmentVote(
                vote_id=vote_id,
                draft_id=draft_id,
                segment_id=segment_id,
                voter_user_id=voter_user_id,
                value=value,
                created_at=now,
            )
    
    def list_votes(
        self,
        draft_id: str,
        user_id: str,
    ) -> DraftVotesResponse:
        """List votes for all segments in a draft."""
        with start_span("waitmode.list_votes", {"draft_id": draft_id, "user_id": user_id}):
            self._check_collaborator_access(draft_id, user_id)
            
            draft = get_draft(draft_id)
            if not draft:
                raise NotFoundError(f"Draft {draft_id} not found")
            
            with get_db_session() as session:
                result = session.execute(
                    select(wait_votes).where(wait_votes.c.draft_id == draft_id)
                )
                votes = result.fetchall()
            
            # Aggregate votes by segment
            vote_map = {}
            user_votes = {}
            
            for vote in votes:
                seg_id = vote.segment_id
                if seg_id not in vote_map:
                    vote_map[seg_id] = {"upvotes": 0, "downvotes": 0}
                
                if vote.value == 1:
                    vote_map[seg_id]["upvotes"] += 1
                else:
                    vote_map[seg_id]["downvotes"] += 1
                
                if vote.voter_user_id == user_id:
                    user_votes[seg_id] = vote.value
            
            # Build response for each segment
            summaries = []
            for segment in draft.segments:
                seg_id = segment.segment_id
                summary = VoteSummary(
                    segment_id=seg_id,
                    upvotes=vote_map.get(seg_id, {}).get("upvotes", 0),
                    downvotes=vote_map.get(seg_id, {}).get("downvotes", 0),
                    user_vote=user_votes.get(seg_id),
                )
                summaries.append(summary)
            
            return DraftVotesResponse(
                draft_id=draft_id,
                segments=summaries,
            )


# Singleton service
waitmode_service = WaitModeService()
