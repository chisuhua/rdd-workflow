# AC Verifier Multi-Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub `invoke_ai_agent()` in `skills/ac-verifier/scripts/ac_verifier.py` with a working multi-provider LLM invocation layer (openai / anthropic / ollama / minimax), keeping `AC_LLM_MOCK=yes` regression behavior identical.

**Architecture:** `BaseHTTPProvider` (shared HTTP/retry/timeout/error-classification) + 4 concrete provider subclasses implementing `_build_payload` / `_build_headers` / `_parse_response` hooks. `llm_providers/__init__.py` exposes a `PROVIDERS` registry and `get_provider()` factory. `ac_verifier.py::invoke_ai_agent` delegates to the registry after the mock short-circuit. Pure `requests>=2.28`, zero SDK dependencies.

**Tech Stack:** Python 3.11+, `requests>=2.28`, `pytest>=7.0`, `bats-core>=1.10`, jsonschema (existing).

**Spec:** `docs/superpowers/specs/2026-09-02-ac-verifier-multi-provider-design.md`

---

## File Structure

**New files** (created in this change):
| Path | Responsibility |
|------|----------------|
| `skills/ac-verifier/scripts/llm_providers/__init__.py` | `PROVIDERS` registry + `get_provider()` factory + `AcVerifierError`-compatible error re-export |
| `skills/ac-verifier/scripts/llm_providers/base.py` | `LLMError` hierarchy + `BaseHTTPProvider` abstract base (env-var parsing, retry, error classification) |
| `skills/ac-verifier/scripts/llm_providers/openai.py` | `OpenAIProvider` (native OpenAI chat completions) |
| `skills/ac-verifier/scripts/llm_providers/anthropic.py` | `AnthropicProvider` (native Anthropic messages API + custom payload + response parser) |
| `skills/ac-verifier/scripts/llm_providers/ollama.py` | `OllamaProvider` (OpenAI-compatible, no auth) |
| `skills/ac-verifier/scripts/llm_providers/minimax.py` | `MiniMaxProvider` (OpenAI-compatible placeholder; `default_base_url=""` forces env-var config) |
| `tests/unit/test_ac_verifier_providers.py` | ~30 unit tests covering BaseHTTPProvider retry/error paths, 4 provider payload/headers, dispatcher |
| `tests/integration/test_ac_verifier_http_live.bats` | bats test using local Python mock HTTP server; real `requests.post` |

**Modified files**:
| Path | Change |
|------|--------|
| `requirements.txt` | Add `requests>=2.28` |
| `skills/ac-verifier/scripts/ac_verifier.py` | Replace stub `invoke_ai_agent()` body with mock-short-circuit + `get_provider().invoke()` |
| `skills/ac-verifier/scripts/ac_verifier.sh` | Update header docs (new env vars) |
| `skills/ac-verifier/SKILL.md` | Add "Provider 配置" section with env-var matrix and examples |

**Unchanged**: `ac_verifier_mocks.py`, `parse_acs`, `build_agent_prompt`, `parse_verdict`, all existing tests.

---

## Task 1: Add `requests>=2.28` to `requirements.txt`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the dependency**

Open `requirements.txt` and add `requests>=2.28` after `croniter>=2.0`:

```diff
 PyYAML>=6.0
 jsonschema>=4.0
 pytest>=7.0
 croniter>=2.0
+requests>=2.28
 ruff>=0.1
 mypy>=1.8
```

- [ ] **Step 2: Verify install**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully (requests>=2.28 satisfied).

- [ ] **Step 3: Verify import**

Run: `python3 -c "import requests; print(requests.__version__)"`
Expected: prints a version `>=2.28`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): add requests>=2.28 (ac-verifier multi-provider + fix cross-repo-protocol lazy import)"
```

---

## Task 2: Create LLMError hierarchy

**Files:**
- Create: `skills/ac-verifier/scripts/llm_providers/__init__.py` (skeleton — final content in Task 10)
- Create: `skills/ac-verifier/scripts/llm_providers/base.py` (errors only in this task; HTTP class in Task 3)
- Test: `tests/unit/test_ac_verifier_providers.py` (skeleton — errors only)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_ac_verifier_providers.py` with:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestErrorHierarchy -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.ac_verifier.scripts.llm_providers.base'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/ac-verifier/scripts/llm_providers/__init__.py`:

```python
"""LLM provider layer for ac-verifier.

Exposes BaseHTTPProvider + 4 concrete providers + PROVIDERS registry.
"""
```

Create `skills/ac-verifier/scripts/llm_providers/base.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestErrorHierarchy -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/ tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): add LLMError hierarchy + provider package skeleton"
```

---

## Task 3: Create BaseHTTPProvider skeleton with env-var validation

**Files:**
- Modify: `skills/ac-verifier/scripts/llm_providers/base.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
import os
from unittest.mock import patch

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestEnvVarParsing -v`
Expected: FAIL with `TypeError: Can't instantiate abstract class BaseHTTPProvider`

- [ ] **Step 3: Implement BaseHTTPProvider skeleton (no invoke() yet)**

Append to `skills/ac-verifier/scripts/llm_providers/base.py`:

```python
import os
from abc import ABC, abstractmethod


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestEnvVarParsing -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/base.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): BaseHTTPProvider skeleton + env-var parsing + validation"
```

---

## Task 4: Implement BaseHTTPProvider.invoke() with retry loop

**Files:**
- Modify: `skills/ac-verifier/scripts/llm_providers/base.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
import requests


class TestInvokeRetry:
    """Verify retry-on-transient, no-retry-on-auth, error classification."""

    def _patch_post(self, monkeypatch, side_effects):
        """side_effects is a list of (response_or_exception) in order."""
        from unittest.mock import MagicMock
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
        monkeypatch.setattr("time.sleep", lambda s: None)  # skip real backoff
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestInvokeRetry -v`
Expected: FAIL with `AttributeError: 'BaseHTTPProvider' object has no attribute 'invoke'`

- [ ] **Step 3: Implement invoke() with retry**

Replace `skills/ac-verifier/scripts/llm_providers/base.py` with:

```python
"""LLM error hierarchy + BaseHTTPProvider shared logic."""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests


# ─── Error hierarchy ────────────────────────────────────────────────────────

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


# ─── Shared base class ──────────────────────────────────────────────────────

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestInvokeRetry -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/base.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): BaseHTTPProvider.invoke() with retry + error classification"
```

---

## Task 5: Create OpenAIProvider

**Files:**
- Create: `skills/ac-verifier/scripts/llm_providers/openai.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestOpenAIProvider -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.ac_verifier.scripts.llm_providers.openai'`

- [ ] **Step 3: Implement OpenAIProvider**

Create `skills/ac-verifier/scripts/llm_providers/openai.py`:

```python
"""OpenAI provider — native OpenAI chat completions protocol."""
from __future__ import annotations

from .base import BaseHTTPProvider


class OpenAIProvider(BaseHTTPProvider):
    name = "openai"
    default_base_url = "https://api.openai.com"
    default_model = "gpt-4o-mini"

    def _build_payload(self, system: str, user: str) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestOpenAIProvider -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/openai.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): OpenAIProvider with native OpenAI chat completions"
```

---

## Task 6: Create AnthropicProvider

**Files:**
- Create: `skills/ac-verifier/scripts/llm_providers/anthropic.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestAnthropicProvider -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.ac_verifier.scripts.llm_providers.anthropic'`

- [ ] **Step 3: Implement AnthropicProvider**

Create `skills/ac-verifier/scripts/llm_providers/anthropic.py`:

```python
"""Anthropic provider — native Anthropic messages API.

Note: Anthropic uses a different protocol than OpenAI:
- system is a top-level field (not a message)
- auth uses x-api-key + anthropic-version headers
- response is {content: [{type: "text", text: "..."}]}
"""
from __future__ import annotations

from .base import BaseHTTPProvider


class AnthropicProvider(BaseHTTPProvider):
    name = "anthropic"
    default_base_url = "https://api.anthropic.com"
    default_model = "claude-3-5-haiku-20241022"

    def _build_payload(self, system: str, user: str) -> dict:
        return {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": 1024,
        }

    def _build_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _parse_response(self, data: dict) -> str:
        """Anthropic format: {content: [{type: "text", text: "..."}]}"""
        return data["content"][0]["text"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestAnthropicProvider -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/anthropic.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): AnthropicProvider with native messages API"
```

---

## Task 7: Create OllamaProvider

**Files:**
- Create: `skills/ac-verifier/scripts/llm_providers/ollama.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
from skills.ac_verifier.scripts.llm_providers.ollama import OllamaProvider


class TestOllamaProvider:
    def test_payload_uses_openai_compat_format(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")  # ollama requires the field but ignores it
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestOllamaProvider -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.ac_verifier.scripts.llm_providers.ollama'`

- [ ] **Step 3: Implement OllamaProvider**

Create `skills/ac-verifier/scripts/llm_providers/ollama.py`:

```python
"""Ollama provider — OpenAI-compatible endpoint at localhost:11434.

Ollama ignores the Authorization header; we still set api_key via env to
satisfy BaseHTTPProvider's non-empty check.
"""
from __future__ import annotations

from .base import BaseHTTPProvider


class OllamaProvider(BaseHTTPProvider):
    name = "ollama"
    default_base_url = "http://localhost:11434"
    default_model = "llama3.1"

    def _build_payload(self, system: str, user: str) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    def _build_headers(self) -> dict:
        return {"Content-Type": "application/json"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestOllamaProvider -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/ollama.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): OllamaProvider (OpenAI-compat, no auth)"
```

---

## Task 8: Create MiniMaxProvider (placeholder)

**Files:**
- Create: `skills/ac-verifier/scripts/llm_providers/minimax.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
from skills.ac_verifier.scripts.llm_providers.minimax import MiniMaxProvider


class TestMiniMaxProvider:
    def test_default_base_url_is_empty_string(self):
        """MiniMax has no hardcoded endpoint — user MUST set AC_LLM_BASE_URL."""
        assert MiniMaxProvider.default_base_url == ""

    def test_payload_uses_openai_compat_format(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.setenv("AC_LLM_BASE_URL", "https://minimax.example.com")
        p = MiniMaxProvider()
        payload = p._build_payload("sys", "usr")
        assert payload["model"] == "MiniMax-M3"
        assert payload["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]

    def test_headers_use_bearer_auth(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "minimax-key")
        monkeypatch.setenv("AC_LLM_BASE_URL", "https://minimax.example.com")
        p = MiniMaxProvider()
        h = p._build_headers()
        assert h["Authorization"] == "Bearer minimax-key"

    def test_constructing_without_base_url_raises_provider_error(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        with pytest.raises(ProviderError, match="AC_LLM_BASE_URL"):
            MiniMaxProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestMiniMaxProvider -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.ac_verifier.scripts.llm_providers.minimax'`

- [ ] **Step 3: Implement MiniMaxProvider**

Create `skills/ac-verifier/scripts/llm_providers/minimax.py`:

```python
"""MiniMax provider — OpenAI-compatible PLACEHOLDER.

⚠️  No real MiniMax API endpoint is hardcoded. Users MUST set
    AC_LLM_BASE_URL to a real OpenAI-compatible endpoint (e.g. a local
    proxy or third-party gateway). Default base_url is intentionally
    empty so that __init__ raises ProviderError immediately if unset,
    preventing silent calls to a wrong endpoint.

This module is the integration point once official MiniMax API docs
are available: adjust default_base_url / default_model here.
"""
from __future__ import annotations

from .base import BaseHTTPProvider


class MiniMaxProvider(BaseHTTPProvider):
    name = "minimax"
    default_base_url = ""  # intentionally empty — no silent fallback
    default_model = "MiniMax-M3"

    def _build_payload(self, system: str, user: str) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestMiniMaxProvider -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/minimax.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): MiniMaxProvider placeholder (no hardcoded endpoint)"
```

---

## Task 9: Create PROVIDERS registry + get_provider() factory

**Files:**
- Modify: `skills/ac-verifier/scripts/llm_providers/__init__.py`
- Modify: `tests/unit/test_ac_verifier_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier_providers.py`:

```python
from skills.ac_verifier.scripts.llm_providers import (
    PROVIDERS,
    get_provider,
    BaseHTTPProvider,  # re-exported
)
from skills.ac_verifier.scripts.llm_providers.base import ProviderError


class TestRegistry:
    def test_all_four_providers_registered(self):
        assert set(PROVIDERS.keys()) == {"openai", "anthropic", "ollama", "minimax"}

    def test_get_provider_openai_returns_openai_provider(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = get_provider("openai")
        assert isinstance(p, BaseHTTPProvider)
        assert p.name == "openai"

    def test_get_provider_anthropic(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = get_provider("anthropic")
        assert p.name == "anthropic"

    def test_get_provider_ollama(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        p = get_provider("ollama")
        assert p.name == "ollama"

    def test_get_provider_minimax_requires_base_url(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        monkeypatch.delenv("AC_LLM_BASE_URL", raising=False)
        with pytest.raises(ProviderError):
            get_provider("minimax")

    def test_get_provider_unknown_raises_provider_error(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        with pytest.raises(ProviderError, match="Unknown provider 'bogus'"):
            get_provider("bogus")

    def test_provider_error_message_lists_valid_names(self, monkeypatch):
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        with pytest.raises(ProviderError) as exc_info:
            get_provider("nope")
        msg = str(exc_info.value)
        assert "openai" in msg
        assert "anthropic" in msg
        assert "ollama" in msg
        assert "minimax" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestRegistry -v`
Expected: FAIL with `ImportError: cannot import name 'PROVIDERS'`

- [ ] **Step 3: Implement the registry**

Replace `skills/ac-verifier/scripts/llm_providers/__init__.py` with:

```python
"""LLM provider layer for ac-verifier.

Public API:
    PROVIDERS       — name → provider class dict
    get_provider()  — factory: returns a configured provider instance
    BaseHTTPProvider — abstract base (re-exported)
"""
from __future__ import annotations

from .base import (
    AuthError,
    BaseHTTPProvider,
    LLMError,
    NetworkError,
    ProviderError,
    RateLimitError,
)
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .ollama import OllamaProvider
from .minimax import MiniMaxProvider


PROVIDERS: dict[str, type[BaseHTTPProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "minimax": MiniMaxProvider,
}


def get_provider(name: str) -> BaseHTTPProvider:
    """Instantiate the named provider.

    Raises ProviderError if the name is unknown. Provider construction may
    also raise AuthError (missing AC_LLM_API_KEY) or ProviderError (missing
    AC_LLM_BASE_URL for providers without a default).
    """
    cls = PROVIDERS.get(name)
    if cls is None:
        valid = sorted(PROVIDERS.keys())
        raise ProviderError(
            f"Unknown provider '{name}'. Valid: {valid}"
        )
    return cls()


__all__ = [
    "PROVIDERS",
    "get_provider",
    "BaseHTTPProvider",
    "LLMError",
    "AuthError",
    "RateLimitError",
    "NetworkError",
    "ProviderError",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_ac_verifier_providers.py::TestRegistry -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/llm_providers/__init__.py tests/unit/test_ac_verifier_providers.py
git commit -m "feat(ac-verifier): PROVIDERS registry + get_provider() factory"
```

---

## Task 10: Modify ac_verifier.py dispatcher (replace stub)

**Files:**
- Modify: `skills/ac-verifier/scripts/ac_verifier.py:123-148`
- Modify: `tests/unit/test_ac_verifier.py` (existing — must keep mock tests passing)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ac_verifier.py` (the existing file):

```python
import os
from unittest.mock import patch, MagicMock

from skills.ac_verifier.scripts import ac_verifier


class TestInvokeDispatcher:
    """Verify invoke_ai_agent() correctly dispatches to mock or provider."""

    def test_mock_mode_takes_priority_over_provider(self, monkeypatch):
        """AC_LLM_MOCK=yes must short-circuit even if AC_LLM_PROVIDER is set."""
        monkeypatch.setenv("AC_LLM_MOCK", "yes")
        monkeypatch.setenv("AC_LLM_PROVIDER", "openai")
        # Should NOT raise AcVerifierError; should use mock
        result = ac_verifier.invoke_ai_agent("sys", "usr")
        # mock_invoke returns canned data — assert it's a string
        assert isinstance(result, str)

    def test_real_mode_unknown_provider_raises(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_MOCK", raising=False)
        monkeypatch.setenv("AC_LLM_PROVIDER", "bogus")
        with pytest.raises(ac_verifier.AcVerifierError, match="AC_LLM_PROVIDER"):
            ac_verifier.invoke_ai_agent("sys", "usr")

    def test_real_mode_missing_provider_raises(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_MOCK", raising=False)
        monkeypatch.delenv("AC_LLM_PROVIDER", raising=False)
        with pytest.raises(ac_verifier.AcVerifierError, match="AC_LLM_PROVIDER not set"):
            ac_verifier.invoke_ai_agent("sys", "usr")

    def test_real_mode_dispatches_to_provider(self, monkeypatch):
        monkeypatch.delenv("AC_LLM_MOCK", raising=False)
        monkeypatch.setenv("AC_LLM_PROVIDER", "openai")
        monkeypatch.setenv("AC_LLM_API_KEY", "k")
        # Mock the provider's invoke
        fake_provider = MagicMock()
        fake_provider.invoke.return_value = "{\"ac_id\": \"AC-1\", \"status\": \"pass\"}"
        with patch.object(ac_verifier, "get_provider", return_value=fake_provider):
            result = ac_verifier.invoke_ai_agent("sys", "usr")
        assert "AC-1" in result
        fake_provider.invoke.assert_called_once_with("sys", "usr")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py::TestInvokeDispatcher -v`
Expected: FAIL — at least the `test_real_mode_dispatches_to_provider` will fail with `AttributeError` because the new code path doesn't exist yet.

- [ ] **Step 3: Replace invoke_ai_agent stub**

Open `skills/ac-verifier/scripts/ac_verifier.py` and replace lines 123-148 (`invoke_ai_agent` body) with:

```python
def invoke_ai_agent(system: str, user: str) -> str:
    """Call LLM with system + user prompts. Returns raw text.

    Priority:
      1. AC_LLM_MOCK=yes → return canned mock response
      2. AC_LLM_PROVIDER=<name> → dispatch to named provider via llm_providers

    Raises AcVerifierError on configuration errors. Provider construction
    failures (missing API key, missing base URL) bubble up as LLMError
    subclasses (AuthError / ProviderError).
    """
    if os.environ.get("AC_LLM_MOCK", "").lower() == "yes":
        import importlib.util
        _mock_path = Path(__file__).resolve().parent / "ac_verifier_mocks.py"
        _spec = importlib.util.spec_from_file_location("ac_verifier_mocks", _mock_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return _mod.mock_invoke(system, user)

    from skills.ac_verifier.scripts.llm_providers import get_provider

    name = os.environ.get("AC_LLM_PROVIDER", "").lower()
    if not name:
        raise AcVerifierError(
            "AC_LLM_PROVIDER not set and AC_LLM_MOCK != yes. "
            "Set AC_LLM_PROVIDER=openai|anthropic|ollama|minimax "
            "or use AC_LLM_MOCK=yes."
        )
    provider = get_provider(name)  # raises ProviderError if unknown
    return provider.invoke(system, user)
```

- [ ] **Step 4: Run all ac_verifier tests**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py tests/unit/test_ac_verifier_providers.py -v`
Expected: ALL tests pass (existing mock tests + new dispatcher tests + provider tests).

- [ ] **Step 5: Run bats regression for ac-verifier**

Run: `bats tests/integration/test_ac_verifier.bats`
Expected: 7 passed (or whatever the current count is — must be unchanged).

- [ ] **Step 6: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): dispatcher delegates AC_LLM_PROVIDER to llm_providers registry"
```

---

## Task 11: Update ac_verifier.sh header docs

**Files:**
- Modify: `skills/ac-verifier/scripts/ac_verifier.sh` (header comment block, lines 1-19)

- [ ] **Step 1: Edit the header**

Replace lines 12-18 of `skills/ac-verifier/scripts/ac_verifier.sh`:

```diff
 # Environment:
 #   STRICT_AC_GATE=yes          Promote AC fail → archive blocker
 #   SKIP_AC_VERIFICATION=yes    Skip verification entirely (exit 2)
 #   AC_LLM_MOCK=yes             Use mock LLM (testing only)
-#   AC_LLM_PROVIDER             openai | anthropic | local-ollama (default: auto-detect)
-#   AC_LLM_MODEL                Model name
-#   AC_LLM_TIMEOUT              Seconds per LLM call (default: 60)
+#   AC_LLM_PROVIDER             openai | anthropic | ollama | minimax (required if AC_LLM_MOCK != yes)
+#   AC_LLM_BASE_URL             Provider endpoint (required for minimax; optional override for others)
+#   AC_LLM_API_KEY              API key (set via env; never commit)
+#   AC_LLM_MODEL                Model name (provider-specific default)
+#   AC_LLM_TIMEOUT              Seconds per LLM call (default: 60)
+#   AC_LLM_MAX_RETRIES          Retry count on 429/5xx/network (default: 3, exponential backoff 1s/2s/4s)
```

- [ ] **Step 2: Verify shellcheck (if available)**

Run: `bash -n skills/ac-verifier/scripts/ac_verifier.sh && echo OK`
Expected: prints `OK` (no syntax errors).

- [ ] **Step 3: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.sh
git commit -m "docs(ac-verifier): document AC_LLM_BASE_URL/AC_LLM_MAX_RETRIES + minimax"
```

---

## Task 12: Update SKILL.md with Provider configuration section

**Files:**
- Modify: `skills/ac-verifier/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md to find insertion point**

Run: `grep -n "^##" skills/ac-verifier/SKILL.md | head -20`
Expected: List of section headers; insert the new section before "## Examples" or similar.

- [ ] **Step 2: Append a new "Provider Configuration" section**

Append to `skills/ac-verifier/SKILL.md`:

```markdown
## Provider Configuration

ac-verifier supports 4 LLM providers via `AC_LLM_PROVIDER`. All configuration
is env-var driven; no files are created or required.

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AC_LLM_MOCK` | No | unset | `yes` → use mock LLM (testing only) |
| `AC_LLM_PROVIDER` | Yes (if not mocking) | — | `openai` \| `anthropic` \| `ollama` \| `minimax` |
| `AC_LLM_BASE_URL` | Yes for `minimax`; optional for others | provider-specific default | Endpoint URL (no trailing slash) |
| `AC_LLM_API_KEY` | Yes | — | API key (set via env, never commit) |
| `AC_LLM_MODEL` | No | provider-specific default | Model name |
| `AC_LLM_TIMEOUT` | No | `60` | Seconds per LLM call |
| `AC_LLM_MAX_RETRIES` | No | `3` | Retries on 429/5xx/network with exponential backoff (1s/2s/4s) |

### Provider-specific defaults

| Provider | base_url | model |
|----------|----------|-------|
| `openai` | `https://api.openai.com` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com` | `claude-3-5-haiku-20241022` |
| `ollama` | `http://localhost:11434` | `llama3.1` |
| `minimax` | `""` ⚠️ **must set `AC_LLM_BASE_URL`** | `MiniMax-M3` |

### Examples

```bash
# OpenAI
export AC_LLM_PROVIDER=openai
export AC_LLM_API_KEY="<your-openai-key>"  # set in env, not committed
ac_verifier.sh my-change

# Anthropic
export AC_LLM_PROVIDER=anthropic
export AC_LLM_API_KEY="<your-anthropic-key>"
ac_verifier.sh my-change

# Local Ollama (no API key needed)
export AC_LLM_PROVIDER=ollama
export AC_LLM_API_KEY=ollama  # required by base class; Ollama ignores it
ac_verifier.sh my-change

# MiniMax (placeholder — requires real endpoint)
export AC_LLM_PROVIDER=minimax
export AC_LLM_BASE_URL="<minimax-endpoint>"
export AC_LLM_API_KEY="<your-key>"
ac_verifier.sh my-change

# Mock mode (testing only)
export AC_LLM_MOCK=yes
ac_verifier.sh my-change
```

### Error → exit code mapping

| Condition | Exit code |
|-----------|-----------|
| All ACs pass | 0 |
| Any AC fail | 1 (warning) — `STRICT_AC_GATE=yes` promotes to archive blocker |
| `--skip` or no proposal.md | 2 |
| LLM error (401/403/429/5xx/network after retries) | 3 |
```

- [ ] **Step 3: Verify the section was inserted correctly**

Run: `grep -n "^## Provider Configuration" skills/ac-verifier/SKILL.md`
Expected: prints a line number.

- [ ] **Step 4: Commit**

```bash
git add skills/ac-verifier/SKILL.md
git commit -m "docs(ac-verifier): SKILL.md provider configuration section"
```

---

## Task 13: bats integration test with live (mock) HTTP server

**Files:**
- Create: `tests/integration/test_ac_verifier_http_live.bats`

- [ ] **Step 1: Create the bats test**

Create `tests/integration/test_ac_verifier_http_live.bats`:

```bash
#!/usr/bin/env bats
#
# Integration test: real requests.post hits a local Python HTTP server
# that returns canned LLM responses. Verifies full invoke_ai_agent() path.
#

load test_helper

setup() {
    load_lib env
    setup_test_env

    # Find an available port
    MOCK_PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")
    MOCK_PID_FILE="$BATS_TEST_TMPDIR/mock_server.pid"
    MOCK_LOG="$BATS_TEST_TMPDIR/mock_server.log"

    # Start mock server in background
    python3 - <<PYEOF > "$MOCK_LOG" 2>&1 &
import http.server, json, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        # Default: return a 200 with OpenAI-compatible JSON
        response = {"choices": [{"message": {"content": "[\"ok\"]"}}]}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, *a, **k): pass  # silence

HTTPServer(('127.0.0.1', $MOCK_PORT), Handler).serve_forever()
PYEOF
    MOCK_PID=$!
    echo "$MOCK_PID" > "$MOCK_PID_FILE"

    # Wait for server to be ready
    for i in 1 2 3 4 5; do
        if curl -s "http://127.0.0.1:${MOCK_PORT}/" >/dev/null 2>&1; then break; fi
        sleep 0.2
    done
}

teardown() {
    if [ -f "$MOCK_PID_FILE" ]; then
        kill "$(cat "$MOCK_PID_FILE")" 2>/dev/null || true
        rm -f "$MOCK_PID_FILE"
    fi
}

@test "live: openai provider hits mock server and returns parsed text" {
    export AC_LLM_PROVIDER=openai
    export AC_LLM_API_KEY=sk-test
    export AC_LLM_BASE_URL="http://127.0.0.1:${MOCK_PORT}"
    unset AC_LLM_MOCK

    run python3 -c "
import sys
sys.path.insert(0, '.')
from skills.ac_verifier.scripts.llm_providers import get_provider
p = get_provider('openai')
result = p.invoke('sys', 'usr')
assert 'ok' in result, f'unexpected: {result}'
print('PASS')
"
    assert_success
    assert_output "PASS"
}

@test "live: 401 from server surfaces as AuthError" {
    # Restart server to return 401
    kill "$(cat "$MOCK_PID_FILE")" 2>/dev/null || true
    python3 - <<PYEOF > "$MOCK_LOG" 2>&1 &
import http.server
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(401); self.end_headers()
    def log_message(self, *a, **k): pass
HTTPServer(('127.0.0.1', $MOCK_PORT), H).serve_forever()
PYEOF
    echo $! > "$MOCK_PID_FILE"
    sleep 0.3

    export AC_LLM_PROVIDER=openai
    export AC_LLM_API_KEY=sk-test
    export AC_LLM_BASE_URL="http://127.0.0.1:${MOCK_PORT}"
    export AC_LLM_MAX_RETRIES=0

    run python3 -c "
import sys
sys.path.insert(0, '.')
from skills.ac_verifier.scripts.llm_providers import get_provider
from skills.ac_verifier.scripts.llm_providers.base import AuthError
try:
    get_provider('openai').invoke('s', 'u')
except AuthError as e:
    assert '401' in str(e); print('PASS')
"
    assert_success
    assert_output "PASS"
}
```

- [ ] **Step 2: Run bats test**

Run: `bats tests/integration/test_ac_verifier_http_live.bats`
Expected: 2 passed (or whatever count; no failures).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_ac_verifier_http_live.bats
git commit -m "test(ac-verifier): bats live HTTP test (mock server) for openai provider"
```

---

## Task 14: Final regression — full test suite + edge checks

**Files:** (no new files; verification only)

- [ ] **Step 1: Run full Python unit tests**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py tests/unit/test_ac_verifier_providers.py -v`
Expected: ALL pass. No new failures vs `main`.

- [ ] **Step 2: Run ac-verifier related bats tests**

Run: `bats tests/integration/test_ac_verifier.bats tests/integration/test_ac_verifier_http_live.bats`
Expected: ALL pass. No new failures.

- [ ] **Step 3: Run `./test.sh --full --regression` (MANDATORY before archive)**

Run: `./test.sh --full --regression`
Expected: Full green OR only `KNOWN_FAILURES.txt` baseline failures. NO new failures.

If new failures appear:
- Investigate the diff between known baseline and current run (output of `tests/scripts/report_regression.sh`)
- Fix root cause (not symptom)
- Re-run until clean

- [ ] **Step 4: Verify AC_LLM_MOCK regression — zero behavior change**

Run: `bats tests/integration/test_ac_verifier.bats`
Expected: Same test count as `main` branch, all pass.

- [ ] **Step 5: Confirm no real API key leaked anywhere**

Run:
```bash
git log --all --pretty=format: --name-only | sort -u | xargs -I{} grep -lE "sk-[a-zA-Z0-9_-]{20,}" {} 2>/dev/null || echo "✅ No key-shaped strings in tracked files"
```
Expected: prints `✅ No key-shaped strings in tracked files` (or no matches).

- [ ] **Step 6: Final summary commit (if any test infra adjustments)**

```bash
git status --short
# If clean, skip this step
# If any changes, commit with: git commit -m "chore(ac-verifier): test infra adjustments after full regression"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task(s) |
|--------------|---------|
| §3 Architecture (component diagram) | Task 2, 3, 4, 9, 10 |
| §4.1 BaseHTTPProvider | Tasks 3, 4 |
| §4.2 5 providers (openai, anthropic, ollama, minimax) | Tasks 5, 6, 7, 8 |
| §4.3 Dispatcher | Task 10 |
| §5 Data flow + error → exit code | Task 4, 10 |
| §6 Testing (unit + bats live) | Tasks 2-9 (unit), Task 13 (bats), Task 14 (regression) |
| §7 Migration path | Tasks 1, 10, 11, 12 |
| §8 Risks & mitigations (mock regression, requests dep, MiniMax empty URL, key leakage) | Task 1 (requests), Task 8 (MiniMax empty URL guard), Task 10 (mock short-circuit), Task 14.5 (key leak check) |
| §9 Dependencies (`requests>=2.28`) | Task 1 |
| §10 Out of scope (JSON mode, tool use, hook) | None — correctly omitted |
| §11 Acceptance Criteria | Verified by Task 14 |

**Placeholder scan:** No TBD/TODO/"similar to Task N"/vague steps. Every task has exact code, exact paths, exact commands, expected outputs.

**Type consistency:**
- `BaseHTTPProvider.__init__` signature consistent across all tests (Tasks 3-9)
- `invoke(system: str, user: str) -> str` consistent across all provider tests
- `_build_payload(system: str, user: str) -> dict` consistent
- `_build_headers() -> dict` consistent
- `_parse_response(data: dict) -> str` consistent (Anthropic overrides; OpenAI/Ollama/MiniMax use default)
- `PROVIDERS: dict[str, type[BaseHTTPProvider]]` matches registry lookup in `get_provider()`
- `LLMError` subclasses consistent (`AuthError`, `RateLimitError`, `NetworkError`, `ProviderError`)
- `AcVerifierError` (from existing `ac_verifier.py`) used for dispatcher-level config errors; `LLMError` subclasses used for provider-level errors — clear separation
