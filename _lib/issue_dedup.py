"""Dedup hash computation for ADR-0027 issue reporter.

Cross-machine stability: same error on different machines/paths/timestamps
produces the same 8-char hash, so GitHub Issues are not duplicated by
environmental noise. Five normalization rules per ADR-0027 §4:

    1. Absolute paths → ``<REDACTED>/<basename>`` (user + project stripped)
    2. Line numbers (``\\d+`` after ``:``) stripped
    3. ISO + Unix-style timestamps → ``TS``
    4. Consecutive digits → ``N``
    5. Platform strings (``Linux 5.x`` / ``Darwin 2x``) stripped

Order matters: timestamp rules run before the digit-run rule so a 10-digit
unix timestamp collapses to a single ``TS`` token instead of ten ``N``s.

The dedup hash is ``sha256(category + ":" + normalized_text)[:8]`` — 32 bits
is enough for the per-project scale (≈4B collision space; same hash file is
kept multiple times on collision).
"""
from __future__ import annotations

import hashlib
import re


_DIGIT_RUN = re.compile(r"\d+")
_TIMESTAMP_ISO = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?")
_TIMESTAMP_UNIX = re.compile(r"\b1\d{9}\b")  # 10-digit unix seconds (2001-2286)
_LINENO = re.compile(r":\d+(?=\b)")
_PLATFORM = re.compile(r"\b(?:Linux|Darwin|Windows|FreeBSD|OpenBSD)\s+[\w.\-]+")
_ABS_PATH = re.compile(r"(?:/(?:home|Users|root)/[^/\s\"'<>]+/)+(?:[^/\s\"'<>]+/)*([^/\s\"'<>:\[]+)(?::\d+)?")


def normalize_for_hash(text: str) -> str:
    """Apply the 5 normalization rules in fixed order; return a stable string for hashing."""
    normalized = text

    normalized = _ABS_PATH.sub(lambda m: f"<REDACTED>/{m.group(1)}", normalized)
    normalized = _TIMESTAMP_ISO.sub("TS", normalized)
    normalized = _TIMESTAMP_UNIX.sub("TS", normalized)
    normalized = _LINENO.sub("", normalized)
    normalized = _DIGIT_RUN.sub("N", normalized)
    normalized = _PLATFORM.sub("", normalized)

    return normalized


def compute_dedup_hash(category: str, error_message: str, stack_frames: list[str]) -> str:
    """Return the first 8 hex chars of ``sha256(category + ':' + normalized_text)``.

    Args:
        category: One of the ADR-0027 §1 categories (e.g. ``doctor-critical``).
        error_message: The error string (usually first line of traceback).
        stack_frames: First N stack frames (default 3 per ADR-0027 §4).

    Returns:
        8-character lowercase hex string.
    """
    normalized_frames = [normalize_for_hash(frame) for frame in stack_frames[:3]]
    payload = f"{category}:{normalize_for_hash(error_message)}:" + "|".join(normalized_frames)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]
