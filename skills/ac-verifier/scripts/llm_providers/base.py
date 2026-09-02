"""LLM error hierarchy + BaseHTTPProvider shared logic."""
from __future__ import annotations


class LLMError(Exception):
    """Base error for all LLM provider operations."""


class AuthError(LLMError):
    """401/403 — fatal, no retry. API key wrong or missing."""


class RateLimitError(LLMError):
    """429 — retryable; provider is rate-limiting us."""


class NetworkError(LLMError):
    """Connection refused / timeout — retryable."""


class ProviderError(LLMError):
    """5xx server errors or malformed payloads. 5xx is retryable; 4xx payload errors are not."""
