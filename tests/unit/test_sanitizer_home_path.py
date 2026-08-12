"""Tests for ADR-0027 §C3 sanitizer extension: $HOME path + project name redaction.

ADR-0027 §C3 / In Scope line 487: extend _lib/loop/sanitizer.py with:
- $HOME absolute paths (/home/<user>/..., /Users/<user>/..., /root/...)
- Project name redaction (configurable sensitive_names parameter)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure _lib/ is importable (project layout per AGENTS.md)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

# Import via the canonical path (NOT the shim)
from loop.sanitizer import sanitize  # type: ignore[import-not-found]


# ── $HOME path redaction (TDD 1.1-1.3 in tasks.md) ────────────────────────


def test_home_linux_user_path_redacted_to_basename():
    """`/home/<user>/<project>/<file>` → `<REDACTED>/<file>` preserving basename + line number."""
    text = "Error in /home/alice/myproj/src/main.py:42"
    result = sanitize(text)
    # The whole `/home/alice/myproj/...:42` should be replaced.
    # We expect the basename (main.py) to be preserved with line number.
    assert "<REDACTED>" in result.sanitized_text
    assert "alice" not in result.sanitized_text  # username gone
    assert "myproj" not in result.sanitized_text  # project name gone
    assert "main.py" in result.sanitized_text  # basename preserved
    assert result.had_sensitive_data is True


def test_home_macos_user_path_redacted_to_basename():
    """`/Users/<user>/<project>/<file>` → `<REDACTED>/<file>` (macOS convention)."""
    text = "Traceback in /Users/bob/repo/lib/handler.py"
    result = sanitize(text)
    assert "<REDACTED>" in result.sanitized_text
    assert "bob" not in result.sanitized_text
    assert "repo" not in result.sanitized_text
    assert "handler.py" in result.sanitized_text
    assert result.had_sensitive_data is True


def test_home_root_user_path_redacted():
    """`/root/<project>/<file>` → `<REDACTED>/<file>` (root user)."""
    text = "Failed at /root/etc/config.toml"
    result = sanitize(text)
    assert "<REDACTED>" in result.sanitized_text
    assert "root" not in result.sanitized_text
    assert result.had_sensitive_data is True


# ── Backward compatibility (TDD 1.9 — no regression) ─────────────────────


def test_existing_etc_path_still_redacted():
    """Existing /etc/... pattern continues to work (no regression)."""
    text = "Config in /etc/passwd"
    result = sanitize(text)
    assert "<REDACTED>" in result.sanitized_text
    assert "/etc/passwd" not in result.sanitized_text


def test_existing_ssh_path_still_redacted():
    """Existing ~/.ssh/... pattern continues to work."""
    text = "Key at ~/.ssh/id_rsa"
    result = sanitize(text)
    assert "<REDACTED>" in result.sanitized_text
    assert "id_rsa" not in result.sanitized_text


def test_non_home_path_unchanged():
    """Path NOT under /home/, /Users/, or /root/ is not touched."""
    text = "Reading /var/log/syslog for /opt/myapp/config.yaml"
    result = sanitize(text)
    # /var/log and /opt/ are NOT in any sensitive pattern
    assert "/var/log/syslog" in result.sanitized_text
    assert "/opt/myapp/config.yaml" in result.sanitized_text
    assert result.had_sensitive_data is False


# ── Project name redaction (TDD 1.4 in tasks.md) ──────────────────────────


def test_project_name_redacted_when_sensitive_names_provided():
    """When sensitive_names=['myproj'] is passed, project name is redacted even from /opt/."""
    text = "Build /opt/myproj/bin/build.sh completed"
    result = sanitize(text, sensitive_names=["myproj"])
    assert "myproj" not in result.sanitized_text
    assert "build.sh" in result.sanitized_text  # basename preserved


# ── Performance budget (regression check) ─────────────────────────────────


def test_sanitize_stays_under_10ms_for_typical_input():
    """ADR-0008: <10ms per call. Verify extension doesn't blow budget."""
    import time
    text = "Error in /home/alice/myproj/src/main.py:42 also at /Users/bob/repo/lib.py and /etc/passwd" * 5
    start = time.perf_counter()
    sanitize(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f"Slow: {elapsed_ms:.2f}ms"  # 5x budget for the larger input
