"""MiniMax provider — OpenAI-compatible PLACEHOLDER.

⚠️  No real MiniMax API endpoint is hardcoded. Users MUST set
    AC_LLM_BASE_URL to a real OpenAI-compatible endpoint (e.g. a local
    proxy or third-party gateway). Default base_url is intentionally
    empty so __init__ raises ProviderError immediately if unset,
    preventing silent calls to a wrong endpoint.

This module is the integration point once official MiniMax API docs
are available: adjust default_base_url / default_model here.
"""
from __future__ import annotations

from .base import BaseHTTPProvider


class MiniMaxProvider(BaseHTTPProvider):
    name = "minimax"
    default_base_url = ""
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
