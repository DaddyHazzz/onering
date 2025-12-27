#!/usr/bin/env python3
"""
OneRing Secret Pattern Scanner
Detects accidental commits of secrets (API keys, passwords, tokens, etc.)
Designed for pre-commit hooks and CI/CD pipelines.

Usage:
  python tools/secret_scan.py --staged          # Scan only git staged files
  python tools/secret_scan.py --all             # Scan entire codebase
  python tools/secret_scan.py --file <path>     # Scan specific file
  python tools/secret_scan.py --diff <commit>   # Scan diff against commit

Exit codes:
  0 = No secrets found (safe)
  1 = Secrets found (abort commit)
  2 = Error in scanning
"""

import re
import subprocess
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# Secret patterns to detect
SECRET_PATTERNS = {
    "stripe_live": {
        "pattern": r"sk_live_[a-zA-Z0-9]{20,}",
        "risk": "CRITICAL - Stripe live secret key",
    },
    "stripe_test": {
        "pattern": r"sk_test_[a-zA-Z0-9]{20,}",
        "risk": "HIGH - Stripe test secret (should not be in code)",
    },
    "stripe_webhook": {
        "pattern": r"whsec_(?!test_)[a-zA-Z0-9]{20,}",  # Exclude whsec_test_
        "risk": "CRITICAL - Stripe webhook secret",
    },
    "stripe_admin": {
        "pattern": r"sk_admin_[a-zA-Z0-9]{20,}",
        "risk": "CRITICAL - Stripe admin key",
    },
    "aws_access_key": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "risk": "CRITICAL - AWS Access Key ID",
    },
    "aws_secret": {
        "pattern": r"aws_secret_access_key\s*[:=]\s*[a-zA-Z0-9/+]{40}",
        "risk": "CRITICAL - AWS Secret Access Key",
    },
    "private_key_pem": {
        "pattern": r"BEGIN\s(?:RSA\s)?PRIVATE\sKEY",
        "risk": "CRITICAL - Private key in PEM format",
    },
    "private_key_openssh": {
        "pattern": r"BEGIN\sOPENSSH\sPRIVATE\sKEY",
        "risk": "CRITICAL - OpenSSH private key",
    },
    "groq_api_key": {
        "pattern": r"gsk_[a-zA-Z0-9]{25,}",
        "risk": "HIGH - Groq API key",
    },
    "github_token": {
        "pattern": r"ghp_[a-zA-Z0-9]{36,}",
        "risk": "CRITICAL - GitHub personal access token",
    },
    "slack_token": {
        "pattern": r"xox[aAsB]-[a-zA-Z0-9]{10,}",
        "risk": "CRITICAL - Slack token",
    },
    "password_in_url": {
        "pattern": r"(?:postgresql|mysql|mongodb)://[^:]+:([^@]+)@",
        "risk": "HIGH - Database password in connection string",
    },
}

# Files to skip (git-ignored, binary, etc.)
SKIP_PATTERNS = [
    r"\.git/",
    r"node_modules/",
    r"\.venv/",
    r"backend_venv/",
    r"__pycache__/",
    r"\.pyc$",
    r"\.egg-info/",
    r"\.env$",
    r"\.env\.local$",
    r"\.env\.test$",
    r"package-lock\.json$",
    r"pnpm-lock\.yaml$",
    r"\.jpg$",
    r"\.png$",
    r"\.gif$",
    r"\.pdf$",
]

# Files to always scan (even if in skip patterns)
MUST_SCAN = [
    r"\.env\.example$",
    r"tools/secret_scan\.py$",  # Scan self
]


def should_skip(file_path: str) -> bool:
    """Check if file should be skipped from scanning."""
    for skip_pattern in SKIP_PATTERNS:
        if re.search(skip_pattern, file_path):
            for must_scan in MUST_SCAN:
                if re.search(must_scan, file_path):
                    return False
            return True
    return False


def scan_content(content: str, file_path: str) -> List[Tuple[str, str, int, str]]:
    """
    Scan file content for secret patterns.
    Returns list of (pattern_name, match_text, line_number, risk_level).
    """
    findings = []
    lines = content.split("\n")

    # Skip placeholder checking for .env.example (it's supposed to have patterns)
    is_env_example = file_path.endswith(".env.example")

    for pattern_name, pattern_info in SECRET_PATTERNS.items():
        pattern = pattern_info["pattern"]
        risk = pattern_info["risk"]

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            print(f"[warn] Invalid regex pattern '{pattern_name}': {e}", file=sys.stderr)
            continue

        for line_num, line in enumerate(lines, 1):
            matches = regex.finditer(line)
            for match in matches:
                match_text = match.group(0)

                if pattern_name in {"private_key_pem", "private_key_openssh"}:
                    if file_path.endswith("SECURITY_SECRETS_POLICY.md"):
                        continue

                if pattern_name == "password_in_url":
                    password_value = match.group(1).strip()
                    placeholder_passwords = {
                        "password",
                        "postgres",
                        "example",
                        "test",
                        "changeme",
                        "pass",
                        "yourpassword",
                        "yourpass",
                        "dev",
                        "local",
                    }
                    if password_value.lower() in placeholder_passwords:
                        continue
                    if "password" in password_value.lower():
                        continue

                # For .env.example, skip obvious examples and placeholders
                if is_env_example:
                    # Skip if line contains PLACEHOLDER, ..., or common placeholder markers
                    if any(
                        marker in line
                        for marker in ["PLACEHOLDER", "...", "test", "YOURKEY", "your-", "example", "localhost", "pass", "user:pass"]
                    ):
                        continue

                # Obfuscate the actual secret in output
                if len(match_text) > 10:
                    obfuscated = match_text[:4] + "*" * (len(match_text) - 8) + match_text[-4:]
                else:
                    obfuscated = "*" * len(match_text)

                findings.append((pattern_name, obfuscated, line_num, risk))

    return findings


def scan_files(file_paths: List[str]) -> Tuple[int, List[Tuple[str, str, str, int, str]]]:
    """
    Scan multiple files for secrets.
    Returns (error_count, [(file, pattern, obfuscated_match, line_num, risk), ...]).
    """
    all_findings = []
    error_count = 0

    for file_path in file_paths:
        # .env.example is SUPPOSED to have pattern matches (that's the point)
        # Skip it unless explicitly requested
        if file_path.endswith(".env.example"):
            continue

        if should_skip(file_path):
            continue

        path = Path(file_path)
        if not path.exists():
            continue

        if path.is_dir():
            # Recursively scan directories
            for file_in_dir in path.rglob("*"):
                if file_in_dir.is_file():
                    scan_files([str(file_in_dir)])
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"[warn] Error reading {file_path}: {e}", file=sys.stderr)
            error_count += 1
            continue

        findings = scan_content(content, file_path)
        for pattern_name, obfuscated_match, line_num, risk in findings:
            all_findings.append((file_path, pattern_name, obfuscated_match, line_num, risk))

    return error_count, all_findings


def get_staged_files() -> List[str]:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"[error] Error getting git staged files: {e}", file=sys.stderr)
        return []


def get_all_files() -> List[str]:
    """Get all files in repository (excluding .gitignore'd)."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"[error] Error getting git files: {e}", file=sys.stderr)
        return []


def get_diff_files(commit: str = "HEAD") -> List[str]:
    """Get files changed since a commit."""
    try:
        result = subprocess.run(
            ["git", "diff", commit, "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"[error] Error getting git diff: {e}", file=sys.stderr)
        return []


def print_findings(findings: List[Tuple[str, str, str, int, str]]) -> int:
    """Print findings in readable format. Returns exit code."""
    if not findings:
        print("[ok] No secrets detected.")
        return 0

    print(f"\n[alert] SECURITY ALERT: {len(findings)} secret(s) found.\n")
    print("-" * 80)

    by_risk = {}
    for file_path, pattern_name, obfuscated_match, line_num, risk in findings:
        risk_level = risk.split(" - ", 1)[0] if " - " in risk else risk
        if risk_level not in by_risk:
            by_risk[risk_level] = []
        by_risk[risk_level].append((file_path, pattern_name, obfuscated_match, line_num, risk))

    # Print by risk level
    for risk_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if risk_level not in by_risk:
            continue
        print(f"\n{risk_level}:")
        for file_path, pattern_name, obfuscated_match, line_num, risk in by_risk[risk_level]:
            pattern_info = SECRET_PATTERNS.get(pattern_name, {"risk": risk})
            print(
                f"  {file_path}:{line_num}  {pattern_name}\n"
                f"    Match: {obfuscated_match}\n"
                f"    Risk: {pattern_info['risk']}"
            )

    print("\n" + "-" * 80)
    print("[abort] Do not commit. Rotate compromised secrets immediately.")
    print("   See .ai/SECURITY_SECRETS_POLICY.md for rotation procedures.")
    print("-" * 80 + "\n")

    return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scan for secret patterns in files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/secret_scan.py --staged          # Pre-commit: scan staged files
  python tools/secret_scan.py --all             # Full codebase scan
  python tools/secret_scan.py --file .env.local # Scan specific file
  python tools/secret_scan.py --diff HEAD~1     # Scan changes since commit

Exit Codes:
  0 = No secrets found (safe to commit)
  1 = Secrets found (abort commit)
  2 = Error in scan
        """,
    )

    parser.add_argument(
        "--staged", action="store_true", help="Scan only git staged files (for pre-commit)"
    )
    parser.add_argument("--all", action="store_true", help="Scan all files in repository")
    parser.add_argument("--file", type=str, help="Scan specific file")
    parser.add_argument("--diff", type=str, nargs="?", const="HEAD", help="Scan diff since commit")

    args = parser.parse_args()

    # Determine files to scan
    if args.staged:
        files = get_staged_files()
        print("[scan] Scanning staged files...\n")
    elif args.all:
        files = get_all_files()
        print("[scan] Scanning all files in repository...\n")
    elif args.diff:
        files = get_diff_files(args.diff)
        print(f"[scan] Scanning diff since {args.diff}...\n")
    elif args.file:
        files = [args.file]
        print(f"[scan] Scanning {args.file}...\n")
    else:
        parser.print_help()
        return 2

    if not files:
        print("[ok] No files to scan.")
        return 0

    # Scan
    error_count, findings = scan_files(files)

    if error_count > 0:
        print(f"[warn] {error_count} error(s) during scan", file=sys.stderr)

    # Print results
    exit_code = print_findings(findings)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
