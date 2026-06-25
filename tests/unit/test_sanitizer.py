"""Tests for skills._lib.sanitizer — redaction of API keys, passwords, sensitive paths."""
import time

import pytest


# ── API keys ─────────────────────────────────────────────────────────────


def test_sanitize_strips_api_key_sk_format():
    """API keys in sk-<20+ alnum chars> format (OpenAI-style) are redacted."""
    from skills._lib.sanitizer import sanitize

    text = "API key is sk-abc123def456ghi789jkl012mno and should be hidden"
    result = sanitize(text)

    assert "sk-abc123def456ghi789jkl012mno" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    assert result.had_sensitive_data is True


def test_sanitize_strips_bearer_token():
    """Bearer tokens in Authorization headers are redacted."""
    from skills._lib.sanitizer import sanitize

    text = (
        "Authorization: Bearer "
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
    )
    result = sanitize(text)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    assert result.had_sensitive_data is True


# ── Passwords ─────────────────────────────────────────────────────────────


def test_sanitize_strips_password_kvpair():
    """password=<value> key-value pairs are redacted."""
    from skills._lib.sanitizer import sanitize

    text = "config: password=hunter2secretvalue please hide"
    result = sanitize(text)

    assert "hunter2secretvalue" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    assert result.had_sensitive_data is True


def test_sanitize_strips_secret_env_var():
    """Env-var-style assignments whose name contains SECRET/TOKEN/KEY are redacted."""
    from skills._lib.sanitizer import sanitize

    text = "AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE leaked"
    result = sanitize(text)

    assert "AKIAIOSFODNN7EXAMPLE" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    assert result.had_sensitive_data is True


# ── Sensitive paths ───────────────────────────────────────────────────────


def test_sanitize_strips_sensitive_path_etc():
    """Paths under /etc/ are redacted."""
    from skills._lib.sanitizer import sanitize

    text = "Reading /etc/passwd for the audit"
    result = sanitize(text)

    assert "/etc/passwd" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    assert result.had_sensitive_data is True


def test_sanitize_strips_sensitive_path_ssh():
    """Paths under ~/.ssh/ are redacted."""
    from skills._lib.sanitizer import sanitize

    text = "Keys are stored at ~/.ssh/id_rsa on the host"
    result = sanitize(text)

    assert "~/.ssh/id_rsa" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    assert result.had_sensitive_data is True


# ── Whitelist ─────────────────────────────────────────────────────────────


def test_whitelist_path_not_redacted():
    """A whitelisted sensitive path is preserved (not redacted)."""
    from skills._lib.sanitizer import sanitize

    text = "Use /etc/passwd config and /etc/shadow too"
    result = sanitize(text, whitelist=["/etc/passwd"])

    # Whitelisted path survives verbatim.
    assert "/etc/passwd" in result.sanitized_text
    # Non-whitelisted sensitive path still redacted.
    assert "/etc/shadow" not in result.sanitized_text
    assert "<REDACTED>" in result.sanitized_text
    # At least one redaction happened (for /etc/shadow), so flag is True.
    assert result.had_sensitive_data is True


# ── Pass-through ──────────────────────────────────────────────────────────


def test_no_sensitive_data_unchanged():
    """Text with no sensitive content is returned untouched and has no redactions."""
    from skills._lib.sanitizer import sanitize

    text = "Just a regular sentence with no secrets here at all."
    result = sanitize(text)

    assert result.sanitized_text == text
    assert result.had_sensitive_data is False
    assert result.redactions == []


# ── Redactions list ───────────────────────────────────────────────────────


def test_redactions_list_populated():
    """The redactions list carries (pattern_name, original) tuples for every match."""
    from skills._lib.sanitizer import sanitize

    text = "first api_key=secret123 here and second password=hunter2 there"
    result = sanitize(text)

    assert len(result.redactions) >= 2
    for pattern_name, original in result.redactions:
        assert isinstance(pattern_name, str)
        assert pattern_name  # non-empty
        assert isinstance(original, str)
        assert original  # non-empty


# ── Performance ───────────────────────────────────────────────────────────


def test_performance_under_10ms():
    """A single sanitize() call on typical input completes in under 10ms."""
    from skills._lib.sanitizer import sanitize

    text = (
        "API key sk-abc123def456ghi789jkl012mno and "
        "/etc/passwd and password=hunter2 and "
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    )

    # Warm up so any one-time regex compilation does not skew the first sample.
    sanitize(text)

    iterations = 10
    start = time.perf_counter()
    for _ in range(iterations):
        sanitize(text)
    elapsed_per_call_ms = (time.perf_counter() - start) * 1000 / iterations

    assert elapsed_per_call_ms < 10, (
        f"sanitize() took {elapsed_per_call_ms:.3f} ms/call (budget 10 ms)"
    )