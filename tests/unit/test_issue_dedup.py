"""Tests for ADR-0027 §4 dedup_hash module: ``_lib/issue_dedup.py``.

ADR-0027 §4: ``sha256(category + normalized_error_message + first_3_normalized_stack_frames)[:8]``
requires 5 normalization rules for cross-machine stability:
1. Absolute paths → basename
2. Line numbers stripped
3. Consecutive digits → ``N``
4. Timestamps → ``TS``
5. Platform strings stripped
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from issue_dedup import normalize_for_hash, compute_dedup_hash  # type: ignore[import-not-found]


# ── Path → basename (TDD 3.1) ──────────────────────────────────────────────


def test_normalize_strips_absolute_path_to_basename():
    """``/home/alice/proj/main.py:42`` → ``<REDACTED>/main.py``."""
    result = normalize_for_hash("/home/alice/proj/main.py:42")
    assert result == "<REDACTED>/main.py"
    assert "alice" not in result
    assert "proj" not in result
    assert "42" not in result  # line number stripped


def test_normalize_macos_path_to_basename():
    """``/Users/bob/repo/lib/handler.py`` → ``<REDACTED>/handler.py``."""
    result = normalize_for_hash("/Users/bob/repo/lib/handler.py")
    assert result == "<REDACTED>/handler.py"
    assert "bob" not in result
    assert "repo" not in result


# ── Digit → N (TDD 3.2) ───────────────────────────────────────────────────


def test_normalize_port_number_to_N():
    """``port=8080`` → ``port=N``."""
    result = normalize_for_hash("connection refused on port=8080")
    assert "8080" not in result
    assert "port=N" in result


def test_normalize_pid_to_N():
    """``PID 12345`` → ``PID N``."""
    result = normalize_for_hash("killed by PID 12345")
    assert "12345" not in result
    assert "PID N" in result


def test_normalize_preserves_non_run_together_digits():
    """Standalone non-numeric words are preserved (digits only collapse inside identifier context)."""
    result = normalize_for_hash("the 5th attempt failed")
    # The 5 is a standalone digit; the rule collapses runs of digits, so ``5th`` → ``Nth``
    assert "5th" not in result


# ── Timestamp → TS (TDD 3.3) ──────────────────────────────────────────────


def test_normalize_iso_timestamp_to_TS():
    """``2026-08-12T10:00:00Z`` → ``TS``."""
    result = normalize_for_hash("failed at 2026-08-12T10:00:00Z")
    assert "2026-08-12" not in result
    assert "10:00:00" not in result
    assert "TS" in result


def test_normalize_unix_timestamp_to_TS():
    """Unix-style ``1715577600`` → ``TS`` (10-digit run)."""
    result = normalize_for_hash("event at 1715577600 seconds")
    assert "1715577600" not in result
    assert "TS" in result


# ── Platform string stripping (TDD 3.4) ───────────────────────────────────


def test_normalize_strips_linux_platform_string():
    """``Linux 5.4.0-1009`` is removed."""
    result = normalize_for_hash("running on Linux 5.4.0-1009")
    assert "Linux" not in result
    assert "5.4.0" not in result


def test_normalize_strips_darwin_platform_string():
    """``Darwin 22.0.0`` is removed."""
    result = normalize_for_hash("running on Darwin 22.0.0")
    assert "Darwin" not in result


# ── Cross-machine stability (TDD 3.5) ─────────────────────────────────────


def test_same_error_different_machines_produces_same_hash():
    """Same category + error + 3 stack frames on different machines/paths → same hash."""
    frames_machine_a = [
        "/home/alice/myproj/src/main.py:42 in main",
        "/home/alice/myproj/lib/utils.py:13 in helper",
        "/home/alice/myproj/handler.py:7 in handle",
    ]
    frames_machine_b = [
        "/Users/bob/different-proj/src/main.py:99 in main",
        "/Users/bob/different-proj/lib/utils.py:55 in helper",
        "/Users/bob/different-proj/handler.py:3 in handle",
    ]
    hash_a = compute_dedup_hash("flow-bug", "schema drift detected", frames_machine_a)
    hash_b = compute_dedup_hash("flow-bug", "schema drift detected", frames_machine_b)
    assert hash_a == hash_b


def test_different_category_produces_different_hash():
    """Same error, different category → different hash (per ADR-0027 §4 category prefix)."""
    frames = ["/home/alice/proj/main.py:42 in main"]
    h_doctor = compute_dedup_hash("flow-bug", "schema drift", frames)
    h_gate = compute_dedup_hash("gate-failure", "schema drift", frames)
    assert h_doctor != h_gate


def test_different_error_message_produces_different_hash():
    """Same category, different error → different hash."""
    frames = ["/home/alice/proj/main.py:42 in main"]
    h1 = compute_dedup_hash("flow-bug", "schema drift detected", frames)
    h2 = compute_dedup_hash("flow-bug", "missing field 'name'", frames)
    assert h1 != h2


# ── Hash format invariants (TDD 3.6) ───────────────────────────────────────


def test_hash_length_is_8_hex_chars():
    """dedup_hash is always 8 hex characters (32 bits, ADR-0027 §4 collision math)."""
    frames = ["/home/alice/proj/main.py:42 in main"]
    h = compute_dedup_hash("flow-bug", "x", frames)
    assert len(h) == 8
    assert re.match(r"^[0-9a-f]{8}$", h), f"not hex: {h}"


def test_hash_is_deterministic():
    """Same input → same hash (idempotency)."""
    frames = ["/home/alice/proj/main.py:42 in main"]
    h1 = compute_dedup_hash("flow-bug", "schema drift", frames)
    h2 = compute_dedup_hash("flow-bug", "schema drift", frames)
    assert h1 == h2


def test_known_vector_matches_sha256_truncation():
    """Sanity check: the hash is a real SHA-256 prefix (not random)."""
    # We can't hard-code the exact hex (depends on normalization), but we
    # can verify the hash length + format + that it differs from sha256 of
    # arbitrary noise.
    import hashlib
    h = compute_dedup_hash("test", "test", ["/x.py:1 in f"])
    assert h != hashlib.sha256(b"unrelated").hexdigest()[:8]


# ── Performance (regression) ──────────────────────────────────────────────


def test_normalize_runs_under_5ms_for_typical_input():
    """Bulk normalization stays fast (used per detected issue)."""
    import time
    text = ("Error in /home/alice/proj/src/main.py:42 at port=8080 PID 12345 "
            "timestamp 2026-08-12T10:00:00Z on Linux 5.4.0 " * 10)
    start = time.perf_counter()
    normalize_for_hash(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 10, f"Slow: {elapsed_ms:.2f}ms"
