"""Sanitize text by redacting API keys, passwords, and sensitive paths.

Implements data sanitization for cross-model verification per ADR-0008
(`docs/adr/ADR-0008-tribunal-committee.md` §4 "数据隐私保护"). The Tribunal
(v2-advanced-features) calls this before forwarding context to Executor /
Reviewer agents so secrets never leak across model boundaries.

Detection categories:

- API keys — ``sk-<20+ alnum>`` (OpenAI-style), ``api_key=…``, ``Bearer …``
- Passwords — ``password=…``, ``passwd=…``, env-var names containing
  ``SECRET`` / ``TOKEN`` / ``KEY`` / ``PASSWORD`` (uppercase convention)
- Sensitive filesystem paths:
  - ``/etc/…``, ``~/.ssh/…``, ``~/.aws/…`` (replaced with literal ``<REDACTED>``)
  - ``/home/<user>/…``, ``/Users/<user>/…``, ``/root/…`` (replaced with
    ``<REDACTED>/<basename>`` preserving the file name so stack traces
    stay diagnosable — added per ADR-0027 §C3 issue-reporter prereq)
- Configurable project names — caller passes ``sensitive_names=[...]`` to
  redact project directory names even from non-standard locations like
  ``/opt/`` (also per ADR-0027 §C3)

Each match is replaced with the literal placeholder ``<REDACTED>`` (paths
preserve the trailing basename as described above; project names are
fully replaced). Callers may pass a ``whitelist`` of substrings; if a matched
sensitive value contains any whitelist entry it is preserved verbatim
(e.g. an audited ``/etc/passwd`` reference that the caller has explicitly
approved).

The whole pipeline is pure-stdlib (``re`` + ``dataclasses``) and pre-compiles
every pattern at import time so a single ``sanitize()`` call stays well under
the 10 ms budget enforced by ``test_performance_under_10ms``.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ── Pattern definitions (raw regex strings) ───────────────────────────────
#
# Exposed as module-level lists so callers can inspect / extend the rules
# without re-importing private constants. Order within each list is the
# scan order; earlier patterns win ties on overlapping matches.

API_KEY_PATTERNS: List[str] = [
    # OpenAI-style sk-… keys (20+ trailing alnum chars).
    r"sk-[a-zA-Z0-9]{20,}",
    # Lower-case api_key assignments (query-string, json, ini, etc.).
    r"api_key=[^\s&\"']+",
    # HTTP Authorization: Bearer <token>.
    r"Bearer\s+\S+",
]

PASSWORD_PATTERNS: List[str] = [
    # Explicit credential key-value pairs.
    r"password=[^\s&\"']+",
    r"passwd=[^\s&\"']+",
    # Env-var style: NAME=value where NAME is UPPER_SNAKE_CASE containing
    # SECRET / TOKEN / KEY / PASSWORD. Non-greedy prefix so the keyword can
    # appear anywhere inside the identifier (e.g. AWS_SECRET_ACCESS_KEY).
    r"\b[A-Z][A-Z0-9_]*?(?:SECRET|TOKEN|KEY|PASSWORD)[A-Z0-9_]*[=:]\s*[^\s&\"']+",
]

SENSITIVE_PATH_PATTERNS: List[str] = [
    # $HOME paths come first so the ``/etc/`` pattern below doesn't greedily
    # match the ``/etc/`` substring inside ``/root/etc/...``.
    r"/home/[^/\s\"'<>]+/(?:[^/\s\"'<>]+/)*[^/\s\"'<>:\[]+(?::\d+)?",
    r"/Users/[^/\s\"'<>]+/(?:[^/\s\"'<>]+/)*[^/\s\"'<>:\[]+(?::\d+)?",
    r"/root/(?:[^/\s\"'<>]+/)+[^/\s\"'<>:\[]+(?::\d+)?",
    r"/etc/[^\s\"'<>]+",
    r"~/.ssh/[^\s\"'<>]+",
    r"~/.aws/[^\s\"'<>]+",
]

# $HOME patterns occupy the first 3 positions in SENSITIVE_PATH_PATTERNS, so
# their absolute indices in _PATTERN_GROUPS are
# (api_key_count + password_count + 0..2). Compute rather than hard-code so
# the slice stays correct if API/PASSWORD pattern lists grow.
_API_KEY_COUNT = len(API_KEY_PATTERNS)
_PASSWORD_COUNT = len(PASSWORD_PATTERNS)
_HOME_PATH_COUNT = 3
_HOME_PATH_GROUP_INDICES = frozenset(
    range(_API_KEY_COUNT + _PASSWORD_COUNT, _API_KEY_COUNT + _PASSWORD_COUNT + _HOME_PATH_COUNT)
)


# ── Public dataclass ──────────────────────────────────────────────────────


@dataclass
class SanitizationResult:
    """Outcome of a :func:`sanitize` call.

    Attributes:
        sanitized_text: Input text with every non-whitelisted sensitive match
            replaced by the literal ``<REDACTED>`` placeholder.
        redactions: Ordered list of ``(pattern_name, original)`` tuples, one
            per redaction actually applied (whitelisted matches excluded).
            ``pattern_name`` is one of ``"api_key"``, ``"password"``,
            ``"sensitive_path"``.
        had_sensitive_data: Convenience flag — ``True`` iff at least one
            redaction was applied. Useful for log/UI decisions without
            inspecting ``redactions`` directly.
    """

    sanitized_text: str
    redactions: List[Tuple[str, str]] = field(default_factory=list)
    had_sensitive_data: bool = False


# ── Internal compiled patterns ────────────────────────────────────────────
#
# Built once at import time so the per-call cost is just re.finditer + replace.
# Each entry is (pattern_name, compiled_pattern) preserving the order of the
# raw lists above.

_PATTERN_GROUPS: List[Tuple[str, "re.Pattern[str]"]] = [
    *[( "api_key", re.compile(p) ) for p in API_KEY_PATTERNS],
    *[( "password", re.compile(p) ) for p in PASSWORD_PATTERNS],
    *[( "sensitive_path", re.compile(p) ) for p in SENSITIVE_PATH_PATTERNS],
]


# Placeholder emitted in place of every redacted sensitive value.
_REDACTED_PLACEHOLDER = "<REDACTED>"


def sanitize(
    text: str,
    whitelist: Optional[List[str]] = None,
    sensitive_names: Optional[List[str]] = None,
) -> SanitizationResult:
    """Redact API keys, passwords, sensitive paths, and project names from ``text``.

    Args:
        text: Input text potentially containing sensitive data.
        whitelist: Optional list of strings. If a sensitive match contains
            any whitelist entry as a substring, it is preserved verbatim
            (not redacted). Default: ``None`` (empty whitelist → redact
            every match).
        sensitive_names: Optional list of project / directory names to
            redact even when they appear outside the standard sensitive-path
            patterns (e.g. ``/opt/myproj/...``). Each name is matched as a
            whole word. Default: ``None`` (no project-name redaction).

    Returns:
        :class:`SanitizationResult` carrying the redacted text, the list of
        ``(pattern_name, original)`` tuples for every redaction that was
        actually applied, and a ``had_sensitive_data`` convenience flag.

    Notes:
        - Detection is purely regex-based; a false negative is preferable to
          a false positive that mangles legitimate text.
        - Whitelist matching is substring containment (case-sensitive), which
          keeps the API simple for path-style overrides like
          ``whitelist=["/etc/passwd"]``.
        - Performance budget: <10 ms per call on typical input
          (``test_performance_under_10ms``).
    """
    if whitelist is None:
        whitelist = []
    if sensitive_names is None:
        sensitive_names = []

    sanitized = text
    redactions: List[Tuple[str, str]] = []

    for idx, (pattern_name, compiled) in enumerate(_PATTERN_GROUPS):
        for match in list(compiled.finditer(sanitized)):
            original = match.group(0)
            if _is_whitelisted(original, whitelist):
                continue
            redactions.append((pattern_name, original))
            replacement = (
                _replace_with_basename(original)
                if idx in _HOME_PATH_GROUP_INDICES
                else _REDACTED_PLACEHOLDER
            )
            sanitized = sanitized.replace(original, replacement, 1)

    for name in sensitive_names:
        if not name:
            continue
        name_pattern = re.compile(rf"\b{re.escape(name)}\b")
        for match in list(name_pattern.finditer(sanitized)):
            original = match.group(0)
            if _is_whitelisted(original, whitelist):
                continue
            redactions.append(("sensitive_name", original))
            sanitized = sanitized.replace(original, _REDACTED_PLACEHOLDER, 1)

    return SanitizationResult(
        sanitized_text=sanitized,
        redactions=redactions,
        had_sensitive_data=bool(redactions),
    )


def _is_whitelisted(matched: str, whitelist: List[str]) -> bool:
    """Return True if any non-empty whitelist entry is contained in ``matched``."""
    return any(entry and entry in matched for entry in whitelist)


def _replace_with_basename(path: str) -> str:
    """Return ``<REDACTED>/<basename>[:lineno]`` preserving the trailing file name.

    Examples:
        ``/home/alice/myproj/src/main.py:42`` → ``<REDACTED>/main.py:42``
        ``/Users/bob/repo/lib.py`` → ``<REDACTED>/lib.py``
        ``/root/etc/config.toml`` → ``<REDACTED>/config.toml``
    """
    path_part, lineno = path, ""
    if ":" in path:
        idx = path.rfind(":")
        if path[idx + 1:].isdigit():
            path_part, lineno = path[:idx], path[idx:]
    basename = os.path.basename(path_part.rstrip("/"))
    if not basename:
        return _REDACTED_PLACEHOLDER
    return f"{_REDACTED_PLACEHOLDER}/{basename}{lineno}"