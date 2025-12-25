import json
import os
import subprocess
import sys
from pathlib import Path


def get_changed_files() -> list[str]:
    # Prefer staged changes; fall back to diff against HEAD
    try:
        out = subprocess.check_output(["git", "diff", "--name-only", "--cached"], text=True)
        files = [l.strip() for l in out.splitlines() if l.strip()]
        if files:
            return files
    except Exception:
        pass
    out = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], text=True)
    return [l.strip() for l in out.splitlines() if l.strip()]


def map_to_backend_tests(paths: list[str]) -> list[str]:
    tests = set()
    for p in paths:
        if p.startswith("backend/"):
            # Heuristic: if a file in backend/ changed, run all backend tests for speed/safety
            return ["backend/tests"]
    return []


def map_to_frontend_tests(paths: list[str]) -> list[str]:
    tests = []
    for p in paths:
        if p.startswith("src/"):
            # Try to find a colocated test first
            fp = Path(p)
            base = fp.stem
            parent = fp.parent
            # Consider __tests__ siblings
            tests_dir = parent / "__tests__"
            candidates = [
                tests_dir / f"{base}.spec.ts",
                tests_dir / f"{base}.spec.tsx",
                tests_dir / f"{base}.test.ts",
                tests_dir / f"{base}.test.tsx",
            ]
            for c in candidates:
                if c.exists():
                    tests.append(str(c))
    return sorted(set(tests))


def run_backend(test_targets: list[str]) -> int:
    if not test_targets:
        return 0
    cmd = ["pytest", "-q", "--tb=no", *test_targets]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


def run_frontend(test_files: list[str]) -> int:
    if not test_files:
        return 0
    cmd = ["pnpm", "vitest", "run", *test_files]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> int:
    changed = get_changed_files()
    if not changed:
        print("No changed files detected.")
        return 0
    be = map_to_backend_tests(changed)
    fe = map_to_frontend_tests(changed)

    code = 0
    code |= run_backend(be)
    code |= run_frontend(fe)
    return code


if __name__ == "__main__":
    sys.exit(main())
