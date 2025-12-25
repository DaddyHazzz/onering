Canonical documentation for OneRing. Migrated from /docs on 2025-12-25.

# Authentication & Authorization (Phase 6.1)

**Status**: Phase 6.1 — Real Auth with Clerk Integration  
**Last Updated**: Dec 23, 2025  
**Test Coverage**: All 535 backend tests ✅ | All 299 frontend tests ✅

---

## Overview

OneRing uses **Clerk** for authentication in production and **X-User-Id header** for backward compatibility during testing.

### Auth Stack
- **Frontend**: `@clerk/nextjs` (Clerk SDK)
- **Backend**: FastAPI with Clerk JWT validation
- **JWT Format**: Clerk issues JWTs with `sub` claim = Clerk user ID
- **Fallback**: X-User-Id header for tests (never use in production)

---

## Frontend Auth Flow

### Step 1: Clerk Sign-In

User signs in via Clerk's hosted UI:

```typescript
// src/app/layout.tsx wraps app with ClerkProvider
<ClerkProvider>
  <html>
    <body>
      <ClerkTokenSync>
        {children}
      </ClerkTokenSync>
    </body>
  </html>
</ClerkProvider>
```

### Step 2: Sync JWT to localStorage

When user signs in, `useClerkToken()` hook stores JWT in localStorage:

```typescript
// src/hooks/useClerkToken.ts
export function useClerkToken() {
  const { getToken } = useAuth();

  useEffect(() => {
    const syncToken = async () => {
      const token = await getToken();
      if (token) {
        localStorage.setItem("clerk_token", token);
      }
    };
    syncToken();
  }, [getToken]);
}
```

### Step 3: Send JWT in API Requests

`collabApi.ts` automatically injects the JWT:

```typescript
// src/lib/collabApi.ts
async function getAuthHeaders(): Promise<Record<string, string>> {
  // Try Clerk JWT first
  const clerkToken = localStorage.getItem("clerk_token");
  if (clerkToken) {
    return { "Authorization": `Bearer ${clerkToken}` };
  }
  
  // Fall back to X-User-Id (tests)
  const testUserId = localStorage.getItem("test_user_id");
  if (testUserId) {
    return { "X-User-Id": testUserId };
  }
  
  return {};  // Read-only mode
}
```

### Step 4: Handle Auth Errors

If JWT expires or is invalid:

```typescript
if (response.status === 401) {
  // Sign out user and redirect to sign-in
  const { signOut } = useAuth();
  await signOut();
}
```

---

## Backend Auth Flow

### Step 1: Receive Request

FastAPI endpoint receives request with one of:

```
# Clerk JWT (production)
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# X-User-Id header (tests)
X-User-Id: test_user_123
```

### Step 2: Validate JWT (or fall back to X-User-Id)

`backend/core/auth.py` validates JWT:

```python
async def get_current_user_id(request: Request, x_user_id: Optional[str] = Header(None)) -> str:
    # Try Clerk JWT first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        user_id = verify_clerk_jwt(jwt_token)  # Validates signature
        return user_id
    
    # Fall back to X-User-Id
    if x_user_id:
        return x_user_id
    
    # No auth
    raise HTTPException(status_code=401, detail="Unauthorized")
```

### Step 3: Upsert User to Database

After validating JWT, automatically create user if first login:

```python
# In get_current_user_id()
user_id = verify_clerk_jwt(jwt_token)

# Upsert user (Phase 6.1)
from backend.features.users.service import get_or_create_user
get_or_create_user(user_id)

return user_id
```

The `app_users` table now has real Clerk users:

```sql
SELECT * FROM app_users;
-- user_id     | display_name | status | created_at
-- user_clerk_123 | NULL       | active | 2025-12-23 ...
```

### Step 4: Use User ID in Endpoints

All collab endpoints use authenticated user:

```python
@router.post("/v1/collab/drafts")
async def create_draft(
    request: CollabDraftRequest,
    user_id: str = Depends(get_current_user_id),  # ← Authenticated!
) -> CollabDraftResponse:
    # Create draft for user_id
    draft = create_draft(
        id=...,
        created_by=user_id,  # ← Real Clerk user ID
        title=request.title,
    )
    return draft
```

---

## JWT Verification Details

### Clerk JWT Structure

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
.
{
  "sub": "user_2rL0nP5Q0q0k2L9M3R4T5U6V",  ← User ID (extracted)
  "iss": "https://your-instance.clerk.accounts.dev",
  "aud": "your-application-id",
  "iat": 1703331600,
  "exp": 1703335200,
  ...
}
.
{signature}
```

### Verification Process

1. **Decode without verification** → Get algorithm
2. **Fetch Clerk's JWKS** → Get public keys
3. **Verify signature** → Using appropriate key from JWKS
4. **Check expiration** → `exp` claim
5. **Extract `sub`** → Clerk user ID

### Why HS256 vs RS256?

- **HS256** (HMAC): Fast, symmetric key (CLERK_SECRET_KEY)
- **RS256** (RSA): Slower, asymmetric keys (fetch from JWKS)

Clerk supports both. Backend validates both algorithms.

---

## Backward Compatibility (X-User-Id)

Tests and local dev can use the X-User-Id header to bypass Clerk JWT:

```bash
# Test without Clerk
curl -H "X-User-Id: test_user_123" \
     -X POST http://localhost:8000/v1/collab/drafts \
     -d '{"title":"Test"}'
```

This is **NOT for production**. Always use Clerk JWT in deployed environments.

---

## Env Variables Required

### Frontend (.env.local)

```dotenv
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```

Get from Clerk Dashboard → API Keys → Publishable Key.

### Backend (backend/.env)

```dotenv
CLERK_SECRET_KEY=sk_test_...
CLERK_ISSUER=https://your-instance.clerk.accounts.dev
CLERK_JWKS_URL=https://your-instance.clerk.accounts.dev/.well-known/jwks.json
```

Get from Clerk Dashboard → API Keys → Secret Key.

---

## Testing Auth

### Test with Clerk JWT

```python
# conftest.py
import jwt
from datetime import datetime, timezone, timedelta
from backend.core.config import settings

def create_test_jwt(user_id: str, expires_in: int = 3600) -> str:
    """Create a test JWT for integration tests."""
    payload = {
        "sub": user_id,
        "iss": settings.CLERK_ISSUER or "https://test.clerk.accounts.dev",
        "aud": "test-app",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, settings.CLERK_SECRET_KEY, algorithm="HS256")

# Then in tests:
def test_create_draft_with_jwt(client):
    token = create_test_jwt("user_test_123")
    response = client.post(
        "/v1/collab/drafts",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test"},
    )
    assert response.status_code == 200
```

### Test with X-User-Id (Backward Compat)

```python
def test_create_draft_with_x_user_id(client):
    response = client.post(
        "/v1/collab/drafts",
        headers={"X-User-Id": "test_user_123"},
        json={"title": "Test"},
    )
    assert response.status_code == 200
```

### Test Unauthorized

```python
def test_create_draft_no_auth(client):
    response = client.post(
        "/v1/collab/drafts",
        json={"title": "Test"},
    )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]["message"]
```

---

## Graceful Degradation

If auth fails, the app gracefully degrades:

```typescript
export async function listDrafts(): Promise<CollabDraft[]> {
  try {
    const response = await apiFetch("/drafts");
    return response.data || [];
  } catch (error) {
    if (error.status === 401) {
      // Not authenticated - read-only mode
      console.warn("Auth failed, switching to read-only");
      return [];  // Empty list (or show sign-in prompt)
    }
    throw error;
  }
}
```

---

## Auth Migration Timeline

| Phase | Auth Method | Status |
|-------|-------------|--------|
| 5.x | X-User-Id only | ✅ Legacy |
| 6.1 | Clerk JWT + X-User-Id fallback | 🚀 **NOW** |
| 6.2+ | Clerk JWT only (X-User-Id removed) | ⏳ Future |
| 7.0 | Clerk OAuth + OIDC federation | ⏳ Future |

---

## Troubleshooting

### 401 Unauthorized in Backend

**Symptom**: "Missing Authorization (Bearer JWT) or X-User-Id header"

**Causes**:
1. JWT expired → Re-authenticate
2. Missing Authorization header → Check `collabApi.ts` is injecting it
3. Invalid Clerk secret → Verify `CLERK_SECRET_KEY` in `.env`
4. Wrong algorithm → Check JWT algorithm matches config

**Fix**:
```typescript
// Verify token in localStorage
console.log("Token:", localStorage.getItem("clerk_token"));

// Check API request in DevTools
// Network tab → see Authorization header
```

### Token Not Syncing

**Symptom**: `getToken()` returns null, localStorage empty

**Causes**:
1. User not signed in
2. Clerk provider not wrapped
3. `useClerkToken` hook not called

**Fix**:
```typescript
// Ensure ClerkTokenSync is in layout
<ClerkProvider>
  <ClerkTokenSync>
    {children}
  </ClerkTokenSync>
</ClerkProvider>
```

### JWT Validation Fails in Backend

**Symptom**: "Invalid token" or "Token verification failed"

**Causes**:
1. `CLERK_SECRET_KEY` mismatch
2. Token from different Clerk instance
3. Token malformed/corrupted

**Fix**:
```bash
# Verify secret in backend/.env
grep CLERK_SECRET_KEY backend/.env

# Check if it matches Clerk Dashboard → API Keys → Secret Key
```

---

## Security Considerations

✅ **DO**:
- Store JWT in localStorage (resets on browser close)
- Validate JWT on every request
- Check expiration (`exp` claim)
- Use HTTPS in production
- Rotate CLERK_SECRET_KEY if compromised

❌ **DON'T**:
- Send JWT in URL parameters
- Log JWT values (security risk)
- Use X-User-Id in production
- Cache JWT longer than expiration
- Ignore signature validation

---

## See Also

- [PHASE6_AUTH_REALTIME.md](PHASE6_AUTH_REALTIME.md) — Full Phase 6 roadmap
- [DESIGN_DECISIONS.md](../DESIGN_DECISIONS.md) — Why Clerk?
- [Clerk Documentation](https://clerk.com/docs) — Official docs
