"""Tests for ac-verifier LLM provider layer."""
from __future__ import annotations

import pytest

from skills.ac_verifier.scripts.llm_providers.base import (
    LLMError,
    AuthError,
    RateLimitError,
    NetworkError,
    ProviderError,
)


class TestErrorHierarchy:
    def test_auth_error_is_llm_error(self):
        assert issubclass(AuthError, LLMError)

    def test_rate_limit_is_llm_error(self):
        assert issubclass(RateLimitError, LLMError)

    def test_network_is_llm_error(self):
        assert issubclass(NetworkError, LLMError)

    def test_provider_is_llm_error(self):
        assert issubclass(ProviderError, LLMError)

    def test_error_can_carry_provider_prefix(self):
        e = AuthError("openai: HTTP 401")
        assert "openai" in str(e)
        assert "401" in str(e)

    def test_errors_are_distinct(self):
        assert AuthError is not RateLimitError
        assert NetworkError is not ProviderError


# ──────────────────────────────────────────────────────────────────────────────
# T3: BaseHTTPProvider skeleton + env-var validation
# ──────────────────────────────────────────────────────────────────────────────

import os
from skills.ac_verifier.scripts.llm_providers.base import BaseHTTPProvider


class _FakeProvider(BaseHTTPProvider):
    """Concrete subclass used only for testing env-var handling."""
    name = "fake"
    default_base_url = "https://fake.example.com"
    default_model = "fake-model-v1"

    def _build_payload(self, system, user):  # pragma: no cover - tested elsewhere
        return {}

    def _build_headers(self):  # pragma: no cover
        return {}


class TestEnvVarParsing:
    def test_defaults_used_when_no_overrides(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        monkeypatch.delenv("AC_LLM_API_KEY", raising=False)
        monkeypatch.delenv("AC_LLM_MODEL", raising=False)
        monkeypatch.setenv("AC_LLM_API_KEY", "test-key")
        p = _FakeProvider()
        assert p.base_url == "https://fake.example.com"
        assert p.api_key == "test-key"
        assert p.model == "fake-model-v1"
        assert p.timeout == 60
        assert p.max_retries == 3

    def test_env_overrides_win(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_BASE_URL", "https://override.example.com/v1/")
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MODEL", "override-model")
        monkeypatch.setenv("AC_LLM_TIMEOUT", "120")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "5")
        p = _FakeProvider()
        assert p.base_url == "https://override.example.com/v1"  # trailing slash stripped
        assert p.model == "override-model"
        assert p.timeout == 120
        assert p.max_retries == 5

    def test_missing_api_key_raises_auth_error(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_API_KEY", raising=False)
        with pytest.raises(AuthError, match="AC_LLM_API_KEY"):
            _FakeProvider()

    def test_missing_base_url_raises_provider_error(self, monkeypatch):
        # Build a provider with empty default_base_url
        class _NoDefault(BaseHTTPProvider):
            name = "nodef"
            default_base_url = ""
            default_model = "x"
            def _build_payload(self, s, u): return {}
            def _build_headers(self): return {}
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        with pytest.raises(ProviderError, match="AC_LLM_BASE_URL"):
            _NoDefault()
