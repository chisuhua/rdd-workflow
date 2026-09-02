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


# ──────────────────────────────────────────────────────────────────────────────
# T4: BaseHTTPProvider.invoke() with retry + error classification
# ──────────────────────────────────────────────────────────────────────────────

import requests
from unittest.mock import MagicMock


class TestInvokeRetry:
    """Verify retry-on-transient, no-retry-on-auth, error classification."""

    def _patch_post(self, monkeypatch, side_effects):
        """side_effects is a list of (response_or_exception) in order."""
        calls = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            effect = side_effects[len(calls) - 1]
            if isinstance(effect, BaseException):
                raise effect
            return effect

        monkeypatch.setattr(requests, "post", fake_post)
        return calls

    def test_successful_200_returns_parsed_text(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
        self._patch_post(monkeypatch, [resp])
        p = _FakeProvider()
        assert p.invoke("sys", "usr") == "hi"

    def test_401_raises_auth_error_no_retry(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        resp = MagicMock(status_code=401)
        calls = self._patch_post(monkeypatch, [resp])
        p = _FakeProvider()
        with pytest.raises(AuthError, match="HTTP 401"):
            p.invoke("sys", "usr")
        assert len(calls) == 1  # no retry

    def test_403_raises_auth_error_no_retry(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        resp = MagicMock(status_code=403)
        calls = self._patch_post(monkeypatch, [resp])
        p = _FakeProvider()
        with pytest.raises(AuthError, match="HTTP 403"):
            p.invoke("sys", "usr")
        assert len(calls) == 1

    def test_429_retries_3x_then_raises(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "3")
        monkeypatch.setattr("time.sleep", lambda s: None)
        resp = MagicMock(status_code=429)
        calls = self._patch_post(monkeypatch, [resp, resp, resp, resp])
        p = _FakeProvider()
        with pytest.raises(RateLimitError, match="HTTP 429"):
            p.invoke("sys", "usr")
        assert len(calls) == 4  # initial + 3 retries

    def test_500_retries_then_raises(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "3")
        monkeypatch.setattr("time.sleep", lambda s: None)
        resp = MagicMock(status_code=500)
        calls = self._patch_post(monkeypatch, [resp, resp, resp, resp])
        p = _FakeProvider()
        with pytest.raises(ProviderError, match="HTTP 500"):
            p.invoke("sys", "usr")
        assert len(calls) == 4

    def test_500_then_200_succeeds(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "3")
        monkeypatch.setattr("time.sleep", lambda s: None)
        bad = MagicMock(status_code=500)
        good = MagicMock(status_code=200)
        good.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        calls = self._patch_post(monkeypatch, [bad, good])
        p = _FakeProvider()
        assert p.invoke("sys", "usr") == "ok"
        assert len(calls) == 2

    def test_400_no_retry_raises_provider_error(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        resp = MagicMock(status_code=400, text="bad payload")
        calls = self._patch_post(monkeypatch, [resp])
        p = _FakeProvider()
        with pytest.raises(ProviderError, match="HTTP 400"):
            p.invoke("sys", "usr")
        assert len(calls) == 1

    def test_connection_error_retries_then_raises(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "3")
        monkeypatch.setattr("time.sleep", lambda s: None)
        calls = self._patch_post(monkeypatch, [
            requests.ConnectionError("refused"),
            requests.ConnectionError("refused"),
            requests.ConnectionError("refused"),
            requests.ConnectionError("refused"),
        ])
        p = _FakeProvider()
        with pytest.raises(NetworkError, match="ConnectionError"):
            p.invoke("sys", "usr")
        assert len(calls) == 4

    def test_timeout_retries_then_raises(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "3")
        monkeypatch.setattr("time.sleep", lambda s: None)
        calls = self._patch_post(monkeypatch, [
            requests.Timeout("slow"),
            requests.Timeout("slow"),
            requests.Timeout("slow"),
            requests.Timeout("slow"),
        ])
        p = _FakeProvider()
        with pytest.raises(NetworkError, match="Timeout"):
            p.invoke("sys", "usr")
        assert len(calls) == 4

    def test_max_retries_0_no_retry(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MAX_RETRIES", "0")
        resp = MagicMock(status_code=429)
        calls = self._patch_post(monkeypatch, [resp])
        p = _FakeProvider()
        with pytest.raises(RateLimitError):
            p.invoke("sys", "usr")
        assert len(calls) == 1


# ──────────────────────────────────────────────────────────────────────────────
# T5: OpenAIProvider
# ──────────────────────────────────────────────────────────────────────────────

from skills.ac_verifier.scripts.llm_providers.openai import OpenAIProvider


class TestOpenAIProvider:
    def test_payload_uses_openai_messages_format(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "sk-test")
        p = OpenAIProvider()
        payload = p._build_payload("be terse", "what is 2+2?")
        assert payload["model"] == "gpt-4o-mini"
        assert payload["messages"] == [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "what is 2+2?"},
        ]

    def test_headers_use_bearer_auth(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "sk-test")
        p = OpenAIProvider()
        h = p._build_headers()
        assert h["Authorization"] == "Bearer sk-test"
        assert h["Content-Type"] == "application/json"

    def test_default_base_url_is_openai(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = OpenAIProvider()
        assert p.base_url == "https://api.openai.com"

    def test_model_override(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_MODEL", "gpt-4o")
        p = OpenAIProvider()
        assert p.model == "gpt-4o"


# ──────────────────────────────────────────────────────────────────────────────
# T6: AnthropicProvider
# ──────────────────────────────────────────────────────────────────────────────

from skills.ac_verifier.scripts.llm_providers.anthropic import AnthropicProvider


class TestAnthropicProvider:
    def test_payload_uses_anthropic_messages_format(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "sk-ant-test")
        p = AnthropicProvider()
        payload = p._build_payload("be terse", "what is 2+2?")
        assert payload["model"] == "claude-3-5-haiku-20241022"
        assert payload["system"] == "be terse"
        assert payload["messages"] == [{"role": "user", "content": "what is 2+2?"}]
        assert payload["max_tokens"] == 1024

    def test_headers_use_anthropic_auth(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "sk-ant-test")
        p = AnthropicProvider()
        h = p._build_headers()
        assert h["x-api-key"] == "sk-ant-test"
        assert h["anthropic-version"] == "2023-06-01"
        assert h["Content-Type"] == "application/json"

    def test_parse_response_extracts_content_text(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = AnthropicProvider()
        data = {"content": [{"type": "text", "text": "4"}]}
        assert p._parse_response(data) == "4"

    def test_default_base_url_is_anthropic(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = AnthropicProvider()
        assert p.base_url == "https://api.anthropic.com"


# ──────────────────────────────────────────────────────────────────────────────
# T7: OllamaProvider
# ──────────────────────────────────────────────────────────────────────────────

from skills.ac_verifier.scripts.llm_providers.ollama import OllamaProvider


class TestOllamaProvider:
    def test_payload_uses_openai_compat_format(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = OllamaProvider()
        payload = p._build_payload("sys", "usr")
        assert payload["model"] == "llama3.1"
        assert payload["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]

    def test_headers_have_no_auth(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = OllamaProvider()
        h = p._build_headers()
        assert "Authorization" not in h
        assert h["Content-Type"] == "application/json"

    def test_default_base_url_is_localhost_11434(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = OllamaProvider()
        assert p.base_url == "http://localhost:11434"
