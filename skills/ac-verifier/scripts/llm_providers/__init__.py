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

