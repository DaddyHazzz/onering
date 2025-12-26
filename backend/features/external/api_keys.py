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
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Tuple
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
    ip_allowlist: Optional[List[str]] = None,
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
            (key_id, key_hash, owner_user_id, scopes, rate_limit_tier, expires_at, ip_allowlist)
            VALUES (:key_id, :key_hash, :owner_user_id, :scopes, :tier, :expires_at, :ip_allowlist)
            RETURNING id
        """),
        {
            "key_id": key_id,
            "key_hash": key_hash,
            "owner_user_id": owner_user_id,
            "scopes": scopes,
            "tier": tier,
            "expires_at": expires_at,
            "ip_allowlist": ip_allowlist or [],
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
        "ip_allowlist": ip_allowlist or [],
    }


def validate_api_key(db: Session, key: str, *, client_ip: Optional[str] = None) -> Optional[Dict]:
    """
    Validate API key and return key info if valid.
    Returns None if invalid, expired, or inactive.
    Updates last_used_at timestamp.
    """
    if not key or not key.startswith("osk_"):
        return None
    
    # Check blocklist first (by key pattern or IP)
    blocked_key = db.execute(
        text("""
            SELECT 1 FROM external_api_blocklist
            WHERE target_type = 'key_pattern'
              AND :key LIKE target_value
              AND (expires_at IS NULL OR expires_at > NOW())
            LIMIT 1
        """),
        {"key": key},
    ).fetchone()

    if blocked_key:
        return None

    if client_ip:
        blocked_ip = db.execute(
            text("""
                SELECT 1 FROM external_api_blocklist
                WHERE target_type = 'ip'
                  AND target_value = :ip
                  AND (expires_at IS NULL OR expires_at > NOW())
                LIMIT 1
            """),
            {"ip": client_ip},
        ).fetchone()
        if blocked_ip:
            return None
    
    # Fetch all active keys and verify against each
    keys = db.execute(
        text(
            """
            SELECT id, key_id, key_hash, owner_user_id, scopes, rate_limit_tier, expires_at, ip_allowlist
            FROM external_api_keys
            WHERE is_active = true
              AND (expires_at IS NULL OR expires_at > NOW())
            """
        )
    ).fetchall()
    
    for row in keys:
        if verify_api_key(key, row[2]):  # row[2] is key_hash
            # Update last_used_at
            ip_allowlist = row[7] or []
            if ip_allowlist and client_ip not in ip_allowlist:
                return None

            db.execute(
                text("UPDATE external_api_keys SET last_used_at = NOW() WHERE id = :id"),
                {"id": row[0]},
            )
            db.commit()

            return {
                "id": str(row[0]),
                "key_id": row[1],
                "owner_user_id": row[3],
                "scopes": row[4],
                "rate_limit_tier": row[5],
                "expires_at": row[6],
                "ip_allowlist": ip_allowlist,
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
            SELECT id, key_id, scopes, rate_limit_tier, is_active, created_at, last_used_at, expires_at, ip_allowlist
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
            "ip_allowlist": row[8] or [],
        }
        for row in rows
    ]


def check_scope(key_info: Dict, required_scope: str) -> bool:
    """Check if API key has required scope."""
    return required_scope in key_info.get("scopes", [])


def check_rate_limit(db: Session, key_id: str, tier: str) -> Tuple[bool, int, int, datetime]:
    """Concurrency-safe hourly rate limit check with atomic upsert.

    Returns (allowed, current_count, limit, reset_at).
    """
    limit = RATE_LIMIT_TIERS.get(tier, 100)
    window_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    reset_at = window_start + timedelta(hours=1)

    # Attempt atomic upsert that only increments if under limit
    upsert_row = db.execute(
        text(
            """
            WITH upsert AS (
                INSERT INTO external_api_rate_limits (key_id, window_start, request_count)
                VALUES (:key_id, :window_start, 1)
                ON CONFLICT (key_id, window_start)
                DO UPDATE SET request_count = external_api_rate_limits.request_count + 1
                WHERE external_api_rate_limits.request_count < :limit
                RETURNING request_count
            )
            SELECT request_count FROM upsert
            """
        ),
        {"key_id": key_id, "window_start": window_start, "limit": limit},
    ).fetchone()

    if upsert_row:
        db.commit()
        current_count = upsert_row[0]
        return True, current_count, limit, reset_at

    # No upsert happened => limit reached; fetch current count without modifying
    existing = db.execute(
        text(
            """
            SELECT request_count
            FROM external_api_rate_limits
            WHERE key_id = :key_id AND window_start = :window_start
            """
        ),
        {"key_id": key_id, "window_start": window_start},
    ).fetchone()
    current_count = existing[0] if existing else limit
    db.commit()
    return False, current_count, limit, reset_at


def rotate_api_key(
    db: Session,
    key_id: str,
    *,
    preserve_key_id: bool = True,
    ip_allowlist: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
) -> Optional[Dict]:
    """Rotate an API key. When preserve_key_id is True, replaces hash on the same key.

    Returns new key info (with full_key) or None if key not found.
    """
    row = db.execute(
        text(
            """
            SELECT owner_user_id, scopes, rate_limit_tier
            FROM external_api_keys
            WHERE key_id = :key_id AND is_active = true
            LIMIT 1
            """
        ),
        {"key_id": key_id},
    ).fetchone()

    if not row:
        return None

    owner_user_id, scopes, tier = row
    new_key_id, full_key = generate_api_key()
    key_hash = hash_api_key(full_key)

    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    allowlist = ip_allowlist if ip_allowlist is not None else []

    if preserve_key_id:
        db.execute(
            text(
                """
                UPDATE external_api_keys
                SET key_hash = :key_hash,
                    rotated_at = NOW(),
                    expires_at = :expires_at,
                    ip_allowlist = :ip_allowlist
                WHERE key_id = :key_id
                """
            ),
            {
                "key_hash": key_hash,
                "expires_at": expires_at,
                "ip_allowlist": allowlist,
                "key_id": key_id,
            },
        )
        db.commit()
        return {
            "key_id": key_id,
            "full_key": full_key,
            "owner_user_id": owner_user_id,
            "scopes": scopes,
            "tier": tier,
            "expires_at": expires_at,
            "ip_allowlist": allowlist,
        }

    # Issue new key_id (deactivate old)
    db.execute(
        text("UPDATE external_api_keys SET is_active = false WHERE key_id = :key_id"),
        {"key_id": key_id},
    )
    new_key = create_api_key(
        db,
        owner_user_id=owner_user_id,
        scopes=scopes,
        tier=tier,
        expires_in_days=expires_in_days,
        ip_allowlist=allowlist,
    )
    db.commit()
    return new_key
