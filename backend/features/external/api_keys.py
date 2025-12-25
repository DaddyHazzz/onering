"""
External API key management service (Phase 10.3).

Handles creation, validation, rotation, and revocation of external API keys.
Keys use bcrypt hashing and follow the format: osk_<random_base64>

Security properties:
- Keys are bcrypt-hashed before storage
- Public key_id stored separately for fast lookup
- Scopes validated on every request
- Rate limits enforced per tier
- Kill switch via ONERING_EXTERNAL_API_ENABLED flag
"""
import os
import secrets
import base64
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.config import settings


# Rate limit tiers (requests per hour)
RATE_LIMIT_TIERS = {
    "free": 100,
    "pro": 1000,
    "enterprise": 10000,
}

# Valid scopes
VALID_SCOPES = [
    "read:rings",
    "read:drafts",
    "read:ledger",
    "read:enforcement",
]


def is_external_api_enabled() -> bool:
    """Check if external API is enabled."""
    return os.getenv("ONERING_EXTERNAL_API_ENABLED", "0") == "1"


def generate_api_key() -> tuple[str, str]:
    """
    Generate new API key.
    Returns (key_id, full_key) tuple.
    
    Format: osk_<32_random_bytes_base64>
    key_id is first 16 chars of hash for lookup.
    """
    random_bytes = secrets.token_bytes(32)
    key_suffix = base64.b64encode(random_bytes).decode('utf-8').rstrip('=')
    full_key = f"osk_{key_suffix}"
    
    # Generate key_id (public identifier)
    key_hash = bcrypt.hashpw(full_key.encode(), bcrypt.gensalt()).decode('utf-8')
    key_id = f"osk_{secrets.token_hex(8)}"  # Simple unique ID
    
    return key_id, full_key


def hash_api_key(key: str) -> str:
    """Hash API key with bcrypt."""
    return bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode('utf-8')


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify API key against stored hash."""
    try:
        return bcrypt.checkpw(key.encode(), key_hash.encode())
    except Exception:
        return False


def create_api_key(
    db: Session,
    owner_user_id: str,
    scopes: List[str],
    tier: str = "free",
    expires_in_days: Optional[int] = None,
) -> Dict:
    """
    Create new external API key.
    Returns dict with key_id and full_key (only time full key is shown).
    """
    # Validate scopes
    invalid_scopes = [s for s in scopes if s not in VALID_SCOPES]
    if invalid_scopes:
        raise ValueError(f"Invalid scopes: {invalid_scopes}")
    
    # Validate tier
    if tier not in RATE_LIMIT_TIERS:
        raise ValueError(f"Invalid tier: {tier}")
    
    key_id, full_key = generate_api_key()
    key_hash = hash_api_key(full_key)
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    result = db.execute(
        text("""
            INSERT INTO external_api_keys 
            (key_id, key_hash, owner_user_id, scopes, rate_limit_tier, expires_at)
            VALUES (:key_id, :key_hash, :owner_user_id, :scopes, :tier, :expires_at)
            RETURNING id
        """),
        {
            "key_id": key_id,
            "key_hash": key_hash,
            "owner_user_id": owner_user_id,
            "scopes": scopes,
            "tier": tier,
            "expires_at": expires_at,
        }
    )
    db.commit()
    
    return {
        "id": str(result.scalar()),
        "key_id": key_id,
        "full_key": full_key,  # Only shown once
        "scopes": scopes,
        "tier": tier,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


def validate_api_key(db: Session, key: str) -> Optional[Dict]:
    """
    Validate API key and return key info if valid.
    Returns None if invalid, expired, or inactive.
    Updates last_used_at timestamp.
    """
    if not key or not key.startswith("osk_"):
        return None
    
    # Check blocklist first (by key pattern)
    blocked = db.execute(
        text("""
            SELECT 1 FROM external_api_blocklist
            WHERE target_type = 'key_pattern'
            AND :key LIKE target_value
            AND (expires_at IS NULL OR expires_at > NOW())
            LIMIT 1
        """),
        {"key": key}
    ).fetchone()
    
    if blocked:
        return None
    
    # Fetch all active keys and verify against each
    keys = db.execute(
        text("""
            SELECT id, key_id, key_hash, owner_user_id, scopes, rate_limit_tier, expires_at
            FROM external_api_keys
            WHERE is_active = true
            AND (expires_at IS NULL OR expires_at > NOW())
        """)
    ).fetchall()
    
    for row in keys:
        if verify_api_key(key, row[2]):  # row[2] is key_hash
            # Update last_used_at
            db.execute(
                text("UPDATE external_api_keys SET last_used_at = NOW() WHERE id = :id"),
                {"id": row[0]}
            )
            db.commit()
            
            return {
                "id": str(row[0]),
                "key_id": row[1],
                "owner_user_id": row[3],
                "scopes": row[4],
                "rate_limit_tier": row[5],
                "expires_at": row[6],
            }
    
    return None


def revoke_api_key(db: Session, key_id: str, owner_user_id: Optional[str] = None) -> bool:
    """
    Revoke API key by key_id.
    If owner_user_id provided, only revokes if owned by that user.
    Returns True if revoked, False if not found.
    """
    if owner_user_id:
        result = db.execute(
            text("""
                UPDATE external_api_keys
                SET is_active = false
                WHERE key_id = :key_id AND owner_user_id = :owner_user_id
                RETURNING id
            """),
            {"key_id": key_id, "owner_user_id": owner_user_id}
        )
    else:
        result = db.execute(
            text("""
                UPDATE external_api_keys
                SET is_active = false
                WHERE key_id = :key_id
                RETURNING id
            """),
            {"key_id": key_id}
        )
    
    db.commit()
    return result.rowcount > 0


def list_api_keys(db: Session, owner_user_id: str) -> List[Dict]:
    """List all API keys for user (without full keys)."""
    rows = db.execute(
        text("""
            SELECT id, key_id, scopes, rate_limit_tier, is_active, created_at, last_used_at, expires_at
            FROM external_api_keys
            WHERE owner_user_id = :owner_user_id
            ORDER BY created_at DESC
        """),
        {"owner_user_id": owner_user_id}
    ).fetchall()
    
    return [
        {
            "id": str(row[0]),
            "key_id": row[1],
            "scopes": row[2],
            "tier": row[3],
            "is_active": row[4],
            "created_at": row[5].isoformat(),
            "last_used_at": row[6].isoformat() if row[6] else None,
            "expires_at": row[7].isoformat() if row[7] else None,
        }
        for row in rows
    ]


def check_scope(key_info: Dict, required_scope: str) -> bool:
    """Check if API key has required scope."""
    return required_scope in key_info.get("scopes", [])


def check_rate_limit(db: Session, key_id: str, tier: str) -> tuple[bool, int, int]:
    """
    Check rate limit for API key.
    Returns (allowed, current_count, limit) tuple.
    Uses hourly window.
    """
    limit = RATE_LIMIT_TIERS.get(tier, 100)
    window_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Get current count
    row = db.execute(
        text("""
            SELECT request_count
            FROM external_api_rate_limits
            WHERE key_id = :key_id AND window_start = :window_start
        """),
        {"key_id": key_id, "window_start": window_start}
    ).fetchone()
    
    current_count = row[0] if row else 0
    allowed = current_count < limit
    
    if allowed:
        # Increment count
        db.execute(
            text("""
                INSERT INTO external_api_rate_limits (key_id, window_start, request_count)
                VALUES (:key_id, :window_start, 1)
                ON CONFLICT (key_id, window_start)
                DO UPDATE SET request_count = external_api_rate_limits.request_count + 1
            """),
            {"key_id": key_id, "window_start": window_start}
        )
        db.commit()
        current_count += 1
    
    return allowed, current_count, limit
