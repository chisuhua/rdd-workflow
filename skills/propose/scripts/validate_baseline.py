#!/usr/bin/env python3
"""validate_baseline.py - Verify .openspec.yaml baseline claims.

Catches fabricated baseline claims (e.g., claiming a static symbol exists
when it doesn't) before they propagate to implementation.

Exit codes:
  0 = pass (all verifiable claims hold; unverifiable skipped with warning)
  1 = hard fail (at least one verifiable claim is false)
  2 = soft warn (no failures, but unverifiable claims present)

Supported claim prefixes (baseline values starting with):
  file-exists:<path>     — file must exist at <path> (relative to change-root)
  symbol-exists:<path>:<regex> — file at <path> must match <regex>
  git-history:<symbol>   — `git log -S "<symbol>"` must return ≥1 commit
  (no prefix)            — free-text, treated as unverifiable, passed with warning
"""
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml


def find_change_dir(change_name: str, search_root: Path) -> Path:
    """Find the change directory by name."""
    changes_root = search_root / "openspec/changes"
    if not changes_root.exists():
        print(f"❌ Change '{change_name}' not found (no openspec/changes/ in {search_root})", file=sys.stderr)
        sys.exit(1)
    cand = changes_root / change_name
    if cand.is_dir():
        return cand
    print(f"❌ Change '{change_name}' not found in {changes_root}/", file=sys.stderr)
    sys.exit(1)


def verify_file_exists(rel_path: str, change_root: Path) -> tuple[bool, str]:
    """Verify file exists. Return (pass, message)."""
    full = (change_root / rel_path).resolve()
    if full.exists() and full.is_file():
        return True, f"file-exists:{rel_path} OK ({full})"
    return False, f"file-exists:{rel_path} FAILED (not found: {full})"


def verify_symbol_exists(rel_path: str, pattern: str, change_root: Path) -> tuple[bool, str]:
    """Verify file contains symbol matching regex. Return (pass, message)."""
    full = (change_root / rel_path).resolve()
    if not full.exists():
        return False, f"symbol-exists:{rel_path}:{pattern} FAILED (file not found: {full})"
    try:
        content = full.read_text()
    except Exception as e:
        return False, f"symbol-exists:{rel_path}:{pattern} FAILED (read error: {e})"
    if re.search(pattern, content):
        return True, f"symbol-exists:{rel_path}:{pattern} OK"
    return False, f"symbol-exists:{rel_path}:{pattern} FAILED (pattern not found)"


def verify_git_history(symbol: str, change_root: Path, timeout: int = 10) -> tuple[bool, str]:
    """Verify symbol exists in git history. Return (pass, message)."""
    try:
        proc = subprocess.run(
            ["git", "log", "-S", symbol, "--all", "--oneline"],
            capture_output=True, text=True, timeout=timeout, cwd=change_root,
        )
    except subprocess.TimeoutExpired:
        return False, f"git-history:{symbol} FAILED (git log timeout after {timeout}s)"
    except FileNotFoundError:
        return False, f"git-history:{symbol} FAILED (git not installed)"
    if proc.returncode != 0:
        return False, f"git-history:{symbol} FAILED (git error: {proc.stderr.strip()})"
    commits = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(commits) >= 1:
        return True, f"git-history:{symbol} OK ({len(commits)} commits)"
    return False, f"git-history:{symbol} FAILED (no commits found)"


def validate_baseline(change_name: str, search_root: Optional[Path] = None) -> int:
    """Validate .openspec.yaml baseline claims. Return exit code."""
    if search_root is None:
        search_root = Path.cwd()
    change_dir = find_change_dir(change_name, search_root)
    openspec_yaml = change_dir / ".openspec.yaml"
    if not openspec_yaml.exists():
        print(f"❌ {change_name}: .openspec.yaml not found at {openspec_yaml}", file=sys.stderr)
        return 1

    try:
        with openspec_yaml.open() as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"❌ {change_name}: .openspec.yaml parse error: {e}", file=sys.stderr)
        return 1

    baseline = data.get("baseline")
    if not baseline or not isinstance(baseline, dict):
        print(f"ℹ️  {change_name}: no baseline claims (pass)", file=sys.stderr)
        return 0

    project_root = change_dir.parent.parent.parent
    failures = []
    warnings = []
    for claim_key, claim_value in baseline.items():
        if not isinstance(claim_value, str):
            warnings.append(f"  ⚠️  baseline.{claim_key}: non-string value (skipped)")
            continue
        if claim_value.startswith("file-exists:"):
            path = claim_value[len("file-exists:"):].strip()
            ok, msg = verify_file_exists(path, project_root)
            if not ok:
                failures.append(f"  ❌ baseline.{claim_key}: {msg}\n     Fix: create the file or correct the path")
            else:
                print(f"  ✅ {msg}")
        elif claim_value.startswith("symbol-exists:"):
            rest = claim_value[len("symbol-exists:"):].strip()
            parts = rest.split(":", 1)
            if len(parts) != 2:
                failures.append(f"  ❌ baseline.{claim_key}: malformed symbol-exists (expected path:regex)")
                continue
            path, pattern = parts
            ok, msg = verify_symbol_exists(path, pattern, project_root)
            if not ok:
                failures.append(f"  ❌ baseline.{claim_key}: {msg}\n     Fix: add symbol to file or correct pattern")
            else:
                print(f"  ✅ {msg}")
        elif claim_value.startswith("git-history:"):
            symbol = claim_value[len("git-history:"):].strip()
            ok, msg = verify_git_history(symbol, project_root)
            if not ok:
                failures.append(f"  ❌ baseline.{claim_key}: {msg}\n     Fix: add the symbol or remove this claim")
            else:
                print(f"  ✅ {msg}")
        else:
            warnings.append(f"  ⚠️  baseline.{claim_key}: unverifiable free-text (skipped)")

    if failures:
        print(f"\n❌ {change_name}: {len(failures)} baseline claim(s) failed:", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        if warnings:
            print(f"\n⚠️  {len(warnings)} unverifiable claim(s) (not failures):", file=sys.stderr)
            for w in warnings:
                print(w, file=sys.stderr)
        return 1

    if warnings:
        print(f"\n⚠️  {change_name}: pass with {len(warnings)} unverifiable claim(s):", file=sys.stderr)
        for w in warnings:
            print(w, file=sys.stderr)

    print(f"✅ {change_name}: all baseline claims verified")
    return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_baseline.py <change-name>", file=sys.stderr)
        sys.exit(2)
    sys.exit(validate_baseline(sys.argv[1]))


if __name__ == "__main__":
    main()
