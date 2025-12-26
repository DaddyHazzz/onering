Source: ../AUTH.md

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

... (full canonical content preserved) ...
