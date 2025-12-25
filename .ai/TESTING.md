# Testing Strategy & Gates

**Principle:** GREEN ALWAYS. Fast gates before local commits, full gates before pushes. No skipped tests. No `--no-verify`.

**Test Counts:**
- Backend: 617 tests (100%)
- Frontend: 388 tests (100%)
- **Total: 1005 tests**
- Status: All green, zero skips

## Quick Start

### Run Tests Locally

**Fast gate (changed files only):**
```powershell
# Frontend only
pnpm test:ui:changed --run

# Backend only  
pytest backend/tests -q --tb=no -k "test_*" --co | head -20

# Both (sequential, ~15 seconds)
./scripts/gate.ps1
```

**Full gate (all tests):**
```powershell
# Backend (617 tests, ~2 min)
pytest backend/tests -q --tb=no

# Frontend (388 tests, ~8 sec)
pnpm test -- --run

# Both (sequential, ~2.5 min)
./scripts/gate.ps1 -Full
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

### `./scripts/gate.ps1` (PowerShell)

**Fast gate (default):**
```powershell
./scripts/gate.ps1
```
- Runs tests on changed files only
- ~15–30 seconds
- Great for local verification before commit

**Full gate:**
```powershell
./scripts/gate.ps1 -Full
```
- Runs all backend + frontend tests
- ~2.5 minutes
- Required before push to main

**What it does:**
1. Stages changes if working directory is clean
2. Detects which files changed (Python modules → test files, TypeScript files → vitest files)
3. Runs subset of tests (fast gate) or all (full gate)
4. Reports PASS/FAIL
5. Provides clear summary

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
