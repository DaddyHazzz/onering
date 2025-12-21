# OneRing Testing Contract (For AI Agents)

Rules:
1. Every new API route MUST have:
   - 1 unauthenticated test
   - 1 validation error test
   - 1 success test

2. Backend tests:
   - Use pytest + pytest-asyncio
   - Use httpx.AsyncClient
   - Never mock Groq or external APIs unless required
   - Prefer integration-style tests

3. Frontend route tests:
   - Call route handlers directly
   - Do NOT spin up Next.js dev server
   - Mock Clerk using jest.fn()

4. Tests must be runnable with:
   - `pnpm test`
   - `pytest`

5. If a test fails:
   - Fix the implementation OR
   - Update the test to match real behavior
   - Never delete failing tests without explanation
