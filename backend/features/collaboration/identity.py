"""
backend/features/collaboration/identity.py
Deterministic handle -> user_id resolution for tests.

STUB: This is a test-only implementation. In production (Phase 3.5+),
replace with real Clerk lookup or database query.
"""

import hashlib


def resolve_handle_to_user_id(handle: str) -> str:
    """
    Resolve a handle (username) to a user_id deterministically.

    For MVP/tests: Generate deterministic ID from handle hash.
    This ensures same handle always maps to same user_id.

    Production migration:
    - Call Clerk API to lookup handle -> user_id
    - Cache result in Redis
    - Handle "not found" gracefully

    Args:
        handle: Username/handle (e.g., "alice", "@bob")

    Returns:
        user_id: Deterministic user ID for tests
    """
    # Normalize handle (remove @ prefix if present)
    normalized = handle.lstrip("@").lower().strip()

    # Generate deterministic ID from handle hash
    # Same handle always produces same user_id
    hash_obj = hashlib.sha1(normalized.encode())
    hash_hex = hash_obj.hexdigest()[:12]
    user_id = f"user_{hash_hex}"

    return user_id


def is_valid_user_id(user_id: str) -> bool:
    """Check if user_id is valid format"""
    return isinstance(user_id, str) and len(user_id) > 0


def is_valid_handle(handle: str) -> bool:
    """Check if handle is valid format"""
    normalized = handle.lstrip("@").lower().strip()
    return len(normalized) > 0 and len(normalized) <= 50
