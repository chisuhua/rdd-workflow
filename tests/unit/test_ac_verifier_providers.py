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
