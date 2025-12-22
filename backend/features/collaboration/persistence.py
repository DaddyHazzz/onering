"""
backend/features/collaboration/persistence.py

PostgreSQL persistence layer for collaboration drafts (Phase 3.5).

Replaces in-memory _drafts_store with database-backed storage.
Maintains exact same API contract as service.py.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
import json
import hashlib
from sqlalchemy import select, insert, update, delete, and_
from sqlalchemy.exc import IntegrityError

from backend.core.database import (
    get_db_session,
    drafts,
    draft_segments,
    draft_collaborators,
    ring_passes,
    idempotency_keys,
)
from backend.models.collab import (
    CollabDraft,
    DraftSegment,
    RingState,
    DraftStatus,
)


class DraftPersistence:
    """
    PostgreSQL-backed draft persistence.
    
    Provides same interface as in-memory store but with durability.
    """
    
    @staticmethod
    def create_draft(draft: CollabDraft) -> bool:
        """
        Persist new draft to database.
        
        Args:
            draft: CollabDraft instance to persist
        
        Returns:
            True if created, False if already exists
        """
        try:
            with get_db_session() as session:
                # Insert draft
                draft_row = {
                    'id': draft.draft_id,
                    'created_by': draft.creator_id,
                    'title': draft.title,
                    'description': draft.platform,  # Store platform in description for now
                    'created_at': draft.created_at,
                    'updated_at': draft.updated_at,
                    'published': draft.status == DraftStatus.COMPLETED,
                    'published_at': None,
                    'view_count': 0,
                }
                
                session.execute(insert(drafts).values(**draft_row))
                
                # Insert segments
                for segment in draft.segments:
                    segment_row = {
                        'draft_id': draft.draft_id,
                        'author': segment.user_id,
                        'content': segment.content,
                        'position': segment.segment_order,
                        'created_at': segment.created_at,
                    }
                    session.execute(insert(draft_segments).values(**segment_row))
                
                # Insert initial ring holder only if different from creator
                # (creator is already tracked as initial holder in holders_history)
                if draft.ring_state.current_holder_id != draft.creator_id:
                    ring_row = {
                        'draft_id': draft.draft_id,
                        'from_user': draft.creator_id,
                        'to_user': draft.ring_state.current_holder_id,
                        'passed_at': draft.ring_state.passed_at,
                    }
                    session.execute(insert(ring_passes).values(**ring_row))
                
                # Insert creator as collaborator (owner role)
                collab_row = {
                    'draft_id': draft.draft_id,
                    'user_id': draft.creator_id,
                    'role': 'owner',
                }
                session.execute(insert(draft_collaborators).values(**collab_row))
                
                session.commit()
                return True
                
        except IntegrityError:
            # Draft already exists
            return False
    
    @staticmethod
    def get_draft(draft_id: str) -> Optional[CollabDraft]:
        """
        Retrieve draft from database.
        
        Args:
            draft_id: Draft UUID
        
        Returns:
            CollabDraft instance or None if not found
        """
        with get_db_session() as session:
            # Fetch draft
            draft_result = session.execute(
                select(drafts).where(drafts.c.id == draft_id)
            ).first()
            
            if not draft_result:
                return None
            
            # Fetch segments (ordered by position)
            segments_result = session.execute(
                select(draft_segments)
                .where(draft_segments.c.draft_id == draft_id)
                .order_by(draft_segments.c.position)
            ).all()
            
            segments = []
            for seg_row in segments_result:
                # Deterministic display name using SHA1 hash
                hash_obj = hashlib.sha1(seg_row.author.encode('utf-8'))
                hash_hex = hash_obj.hexdigest()
                author_display = f"@u_{hash_hex[-6:]}"
                
                segment = DraftSegment(
                    segment_id=str(seg_row.id),
                    draft_id=draft_id,
                    user_id=seg_row.author,
                    content=seg_row.content,
                    created_at=seg_row.created_at,
                    segment_order=seg_row.position,
                    author_user_id=seg_row.author,
                    author_display=author_display,
                    ring_holder_user_id_at_write=seg_row.author,
                    ring_holder_display_at_write=author_display,
                )
                segments.append(segment)
            
            # Fetch ring history
            ring_result = session.execute(
                select(ring_passes)
                .where(ring_passes.c.draft_id == draft_id)
                .order_by(ring_passes.c.passed_at)
            ).all()
            
            ring_history = [draft_result.created_by]  # Start with initial holder
            last_pass_time = draft_result.created_at
            current_holder = draft_result.created_by
            
            for ring_row in ring_result:
                ring_history.append(ring_row.to_user)
                current_holder = ring_row.to_user
                last_pass_time = ring_row.passed_at
            
            # Fetch collaborators
            collabs_result = session.execute(
                select(draft_collaborators).where(
                    draft_collaborators.c.draft_id == draft_id
                )
            ).all()
            
            collaborators = [
                row.user_id for row in collabs_result
                if row.user_id != draft_result.created_by
            ]
            
            # Build ring state
            ring_state = RingState(
                draft_id=draft_id,
                current_holder_id=current_holder,
                holders_history=ring_history,
                passed_at=last_pass_time,
                last_passed_at=last_pass_time,
            )
            
            # Build draft
            status = DraftStatus.COMPLETED if draft_result.published else DraftStatus.ACTIVE
            
            draft = CollabDraft(
                draft_id=draft_id,
                creator_id=draft_result.created_by,
                title=draft_result.title,
                platform=draft_result.description or "X",  # Default to X if not set
                status=status,
                segments=segments,
                ring_state=ring_state,
                collaborators=collaborators,
                created_at=draft_result.created_at,
                updated_at=draft_result.updated_at,
            )
            
            return draft
    
    @staticmethod
    def list_drafts_by_user(user_id: str) -> List[CollabDraft]:
        """
        List all drafts involving user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of CollabDraft instances
        """
        with get_db_session() as session:
            # Find drafts where user is creator or collaborator
            draft_ids = set()
            
            # Creator
            creator_results = session.execute(
                select(drafts.c.id).where(drafts.c.created_by == user_id)
            )
            for row in creator_results:
                draft_ids.add(row.id)
            
            # Collaborator
            collab_results = session.execute(
                select(draft_collaborators.c.draft_id).where(
                    draft_collaborators.c.user_id == user_id
                )
            )
            for row in collab_results:
                draft_ids.add(row.draft_id)
            
            # Segment author
            segment_results = session.execute(
                select(draft_segments.c.draft_id).where(
                    draft_segments.c.author == user_id
                )
            )
            for row in segment_results:
                draft_ids.add(row.draft_id)
            
            # Fetch all drafts
            drafts_list = []
            for draft_id in draft_ids:
                draft = DraftPersistence.get_draft(draft_id)
                if draft:
                    drafts_list.append(draft)
            
            return drafts_list
    
    @staticmethod
    def update_draft(draft: CollabDraft) -> bool:
        """
        Update existing draft in database.
        
        Args:
            draft: Updated CollabDraft instance
        
        Returns:
            True if updated, False if not found
        """
        try:
            with get_db_session() as session:
                # Update draft row
                stmt = (
                    update(drafts)
                    .where(drafts.c.id == draft.draft_id)
                    .values(
                        updated_at=draft.updated_at,
                        published=draft.status == DraftStatus.COMPLETED,
                    )
                )
                
                result = session.execute(stmt)
                
                if result.rowcount == 0:
                    return False
                
                session.commit()
                return True
                
        except Exception:
            return False
    
    @staticmethod
    def append_segment(draft_id: str, segment: DraftSegment) -> bool:
        """
        Append segment to draft.
        
        Args:
            draft_id: Draft UUID
            segment: DraftSegment to append
        
        Returns:
            True if appended, False on error
        """
        try:
            with get_db_session() as session:
                segment_row = {
                    'draft_id': draft_id,
                    'author': segment.user_id,
                    'content': segment.content,
                    'position': segment.segment_order,
                    'created_at': segment.created_at,
                }
                
                session.execute(insert(draft_segments).values(**segment_row))
                
                # Update draft updated_at
                session.execute(
                    update(drafts)
                    .where(drafts.c.id == draft_id)
                    .values(updated_at=datetime.now(timezone.utc))
                )
                
                # Commit is automatic in context manager
                return True
                
        except Exception as e:
            print(f"[persistence] append_segment error: {e}")
            return False
    
    @staticmethod
    def pass_ring(draft_id: str, from_user: str, to_user: str, passed_at: datetime) -> bool:
        """
        Record ring pass.
        
        Args:
            draft_id: Draft UUID
            from_user: User passing ring
            to_user: User receiving ring
            passed_at: Timestamp of pass
        
        Returns:
            True if recorded, False on error
        """
        try:
            with get_db_session() as session:
                ring_row = {
                    'draft_id': draft_id,
                    'from_user': from_user,
                    'to_user': to_user,
                    'passed_at': passed_at,
                }
                
                session.execute(insert(ring_passes).values(**ring_row))
                
                # Update draft updated_at
                session.execute(
                    update(drafts)
                    .where(drafts.c.id == draft_id)
                    .values(updated_at=passed_at)
                )
                
                session.commit()
                return True
                
        except Exception:
            return False
    
    @staticmethod
    def check_idempotency(key: str) -> bool:
        """
        Check if idempotency key has been seen.
        
        Args:
            key: Idempotency key
        
        Returns:
            True if key exists, False otherwise
        """
        with get_db_session() as session:
            result = session.execute(
                select(idempotency_keys.c.key).where(
                    idempotency_keys.c.key == key
                )
            ).first()
            
            return result is not None
    
    @staticmethod
    def record_idempotency(key: str, scope: str = "collab") -> bool:
        """
        Record idempotency key.
        
        Args:
            key: Idempotency key
            scope: Scope of key (default: collab)
        
        Returns:
            True if recorded, False if already exists
        """
        try:
            with get_db_session() as session:
                session.execute(
                    insert(idempotency_keys).values(
                        key=key,
                        scope=scope
                    )
                )
                session.commit()
                return True
                
        except IntegrityError:
            return False
    
    @staticmethod
    def add_collaborator(draft_id: str, user_id: str) -> bool:
        """
        Add user as collaborator to draft (idempotent).
        
        Args:
            draft_id: Draft UUID
            user_id: User to add
        
        Returns:
            True if added, False if already collaborator or error
        """
        try:
            with get_db_session() as session:
                collab_row = {
                    'draft_id': draft_id,
                    'user_id': user_id,
                    'role': 'collaborator',
                }
                session.execute(insert(draft_collaborators).values(**collab_row))
                session.commit()
                return True
        except IntegrityError:
            # Already a collaborator (UNIQUE constraint)
            return False
        except Exception:
            return False
    
    @staticmethod
    def clear_all() -> None:
        """
        Clear all draft data.
        FOR TESTING ONLY.
        """
        with get_db_session() as session:
            session.execute(delete(ring_passes))
            session.execute(delete(draft_segments))
            session.execute(delete(draft_collaborators))
            session.execute(delete(drafts))
            # Also clear idempotency keys with collab scope
            session.execute(
                idempotency_keys.delete().where(idempotency_keys.c.scope == "collab")
            )
            session.commit()
