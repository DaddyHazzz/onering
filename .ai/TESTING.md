# Testing Strategy & Gates

**Principle:** GREEN ALWAYS. Fast gates while iterating, one full gate before the final commit/push. No skipped tests. No `--no-verify`.

**Test Counts (Dec 25, 2025):**
- Backend: 618 tests (100%)
- Frontend: 395 tests (100%)
- **Total: 1013 tests**
- Status: All green, zero skips

## Quick Start

### Run Tests Locally

**Fast gate (changed files only, default):**
```powershell
# Both (changed-only)
pnpm gate -- --mode fast
# or: ONERING_GATE=fast pnpm gate
```

**Full gate (all tests, run once before final commit/push):**
```powershell
pnpm gate -- --mode full
# or: ONERING_GATE=full pnpm gate
```

**Docs-only gate (skip tests):**
```powershell
ONERING_GATE=docs pnpm gate -- --mode docs
```

**Single file/test:**
```powershell
# Backend file
pytest backend/tests/test_insights_api.py -v

# Backend test
pytest backend/tests/test_insights_api.py::TestInsightsAPI::test_alerts_no_activity_and_long_hold -v

# Frontend file
pnpm test src/__tests__/insights-panel.spec.tsx -- --run

# Frontend test
pnpm test -- --run -t "calls onRefresh after action"
```

## Gate Scripts

### Git Hooks (core.hooksPath = .githooks/)

**Hooks are DISABLED by default.** Require explicit opt-in to prevent unexpected test runs.

**To enable hooks:**
```powershell
# Pre-commit hook
ONERING_HOOKS=1 ONERING_GATE=fast git commit ...

# Pre-push hook (full gate only)
ONERING_HOOKS=1 ONERING_GATE=full git push ...
```

**Hook behaviors (when enabled):**
- `pre-commit`: Runs gate in the mode specified by `ONERING_GATE` (fast, full, or docs)
- `pre-push`: Runs full gate only if `ONERING_GATE=full`; otherwise skips
- Recursion guard: If `ONERING_HOOK_RUNNING` env var is set, hook exits silently (prevents nested calls)

**Modes:**
- `docs` → skips all tests (safe for documentation work)
- `fast` → changed-only tests (default for development)
- `full` → all backend + frontend tests (required before final push)

### Everyday Loop & Commit Policy
- Iterate with `pnpm gate --mode fast` while coding (direct invocation, no hooks)
- For doc-only updates, use `pnpm gate --mode docs` (no tests needed)
- Before the final commit/push, run exactly one full gate: `pnpm gate --mode full`
- Keep commits atomic: one commit per task (docs-only commits are fine)
- Never use `--no-verify` to bypass hooks

### `./scripts/gate.ps1` (PowerShell)

**Mode switcher (env or arg):**
- `--mode fast` (default) → changed-only tests
- `--mode full` → full backend + frontend
- `--mode docs` → skip tests (for doc-only commits)

Examples:
```powershell
pnpm gate --mode fast          # default (direct call)
pnpm gate --mode full          # run once before final commit/push
pnpm gate --mode docs          # skip tests for doc-only updates
```

Behavior:
- Fast uses `scripts/test_changed.py` to map changed files → tests
- Full runs `python -m pytest backend/tests -q --tb=no` then `pnpm vitest run`
- Docs exits 0 immediately (use intentionally for doc-only changes)

### `scripts/test_changed.py` (Python Helper)

**Called by gate.ps1** to map changed files to test targets:
```python
python scripts/test_changed.py --backend --changed-files src/file1.py src/file2.ts
```

Returns list of test files to run.

## Flake Reduction

**UI Tests (Vitest + RTL):**
- ✅ Use role-based selectors: `getByRole("button", { name: /action/i })`
- ✅ Avoid text duplication (use labels/aria-label)
- ✅ Avoid hardcoded timeouts; use `waitFor(() => condition)`
- ✅ Mock external APIs consistently

**Backend Tests (Pytest):**
- ✅ Use fixtures for setup/teardown
- ✅ Avoid time-based assertions; use `now` parameter for deterministic testing
- ✅ Mock Groq API + external services
- ✅ Test both happy path + error cases

**Shared:**
- ✅ Never use `sleep()` in tests unless unavoidable
- ✅ Centralize common mocks in conftest / test setup files

## Troubleshooting

### Frontend Tests Fail with "act() warning"
```
Expected: wrap state updates in act(...)
```
**Fix:** Use `act()` from `@testing-library/react` when firing events:
```tsx
import { act } from "@testing-library/react";

act(() => {
  fireEvent.click(button);
});
```

### Backend Tests Time Out
```
FAILED ... Timeout
```
**Fix:** Check if tests are waiting on external APIs. Ensure mocks are set up:
```python
vi.mocked(collabApi.getDraftInsights).mockResolvedValue(mockData);
```

### Vitest Cannot Find Module
```
ERROR Cannot find module '@/lib/...'
```
**Fix:** Ensure `tsconfig.json` has path alias:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

### Test Works Locally, Fails in CI
**Common cause:** Unset environment variables.
- Ensure `.env.local` (frontend) and `backend/.env` (backend) have test values
- Use GitHub Secrets for real API keys
- Tests should mock external services (no real API calls)

## Coverage & Quality

**No metrics-based gates** (code coverage %): Quality > numbers.

**Instead:**
- All tests green (zero skips)
- All test files have clear intent comments
- All test assertions are meaningful (not just existence checks)
- Flaky tests get fixed/skipped with justification

## CI/CD Integration

(Optional, add to `.github/workflows/test.yml` when ready)

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v3
      
      - name: Install deps
        run: |
          pip install -r backend/requirements.txt
          pnpm install
      
      - name: Backend tests
        run: pytest backend/tests -q --tb=no
      
      - name: Frontend tests
        run: pnpm test -- --run
```

## Writing New Tests

### Backend (Pytest)

```python
# backend/tests/test_my_feature.py
import pytest
from datetime import datetime, timezone
from backend.features.my_feature.service import MyService

@pytest.fixture
def my_service():
    return MyService()

def test_my_feature_happy_path(my_service):
    """Should compute X when given Y."""
    result = my_service.process(input_data)
    assert result.status == "success"
    assert result.value == expected_value

def test_my_feature_with_now_parameter(my_service):
    """Should be deterministic with 'now' parameter."""
    now = datetime(2025, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
    result = my_service.process(input_data, now=now)
    assert result.computed_at == now
```

### Frontend (Vitest)

```tsx
// src/__tests__/my-component.spec.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import MyComponent from "@/components/MyComponent";

// Mock external APIs
vi.mock("@/lib/api");

describe("MyComponent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    render(<MyComponent />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders data when loaded", async () => {
    vi.mocked(api.getData).mockResolvedValue(mockData);
    
    render(<MyComponent />);
    
    await waitFor(() => {
      expect(screen.getByText(mockData.title)).toBeInTheDocument();
    });
  });
});
```

## Performance Benchmarks

| Gate | Time | Target |
|------|------|--------|
| Fast gate (changed) | 15–30s | < 1 min |
| Full gate (all) | ~2.5 min | < 5 min |
| Single test file | 3–8s | < 15s |

If any gate exceeds target, investigate:
- Are tests waiting unnecessarily?
- Can mocks speed this up?
- Can we parallelize?

## When to Skip a Test

**Only if:**
1. Test is inherently flaky (e.g., depends on network timing)
2. The flakiness is documented in a comment
3. An issue is opened to fix the root cause
4. Skip reason includes issue link: `@pytest.mark.skip(reason="Issue #123")`

Example:
```python
@pytest.mark.skip(reason="Flaky on CI due to timestamp precision; see Issue #42")
def test_timeline_sorting():
    ...
```

Never skip to make tests faster.

## Questions?

- **How do I run only insights tests?** `pytest backend/tests -k insights -q --tb=no`
- **How do I see test output?** Remove `--tb=no` to see full tracebacks
- **How do I debug a test?** Add `breakpoint()` in test, run with `pytest --pdb`
- **How do I mock Groq API?** See `backend/tests/conftest.py` for fixtures
