"""LLM error hierarchy + BaseHTTPProvider shared logic."""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests


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


class BaseHTTPProvider(ABC):
    """Shared HTTP/retry/timeout/error-classification for LLM providers.

    Subclasses MUST set: name, default_base_url, default_model.
    Subclasses MUST implement: _build_payload(), _build_headers().
    Subclasses MAY override: _parse_response() (default = OpenAI format).
    """

    name: str = "base"
    default_base_url: str = ""
    default_model: str = ""

    def __init__(self) -> None:
        raw_url = os.environ.get("AC_LLM_BASE_URL", "").rstrip("/")
        self.base_url: str = raw_url or self.default_base_url
        self.api_key: str = os.environ.get("AC_LLM_API_KEY", "")
        raw_model = os.environ.get("AC_LLM_MODEL", "")
        self.model: str = raw_model or self.default_model
        self.timeout: int = int(os.environ.get("AC_LLM_TIMEOUT", "60"))
        self.max_retries: int = int(os.environ.get("AC_LLM_MAX_RETRIES", "3"))

        if not self.api_key:
            raise AuthError(f"{self.name}: AC_LLM_API_KEY not set")
        if not self.base_url:
            raise ProviderError(
                f"{self.name}: AC_LLM_BASE_URL not set and no default for '{self.name}'"
            )

    @abstractmethod
    def _build_payload(self, system: str, user: str) -> dict: ...

    @abstractmethod
    def _build_headers(self) -> dict: ...

    def _parse_response(self, data: dict) -> str:
        """Default: OpenAI format. Override for Anthropic."""
        return data["choices"][0]["message"]["content"]

    def invoke(self, system: str, user: str) -> str:
        """Call LLM, return text. Retry transient errors with exponential backoff."""
        payload = self._build_payload(system, user)
        headers = self._build_headers()
        url = f"{self.base_url}/v1/chat/completions"
        last_err: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

                if resp.status_code in (401, 403):
                    raise AuthError(f"{self.name}: HTTP {resp.status_code}")

                if resp.status_code == 429:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise RateLimitError(f"{self.name}: HTTP 429 (max retries)")

                if resp.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise ProviderError(f"{self.name}: HTTP {resp.status_code}")

                if resp.status_code != 200:
                    raise ProviderError(
                        f"{self.name}: HTTP {resp.status_code} body={resp.text[:200]}"
                    )

                return self._parse_response(resp.json())

            except (requests.ConnectionError, requests.Timeout) as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise NetworkError(f"{self.name}: {type(e).__name__}: {e}")

        raise ProviderError(f"{self.name}: max retries exceeded: {last_err}")
