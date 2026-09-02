"""Anthropic provider — native Anthropic messages API.

Protocol differs from OpenAI:
- `system` is a top-level field (not a message)
- auth uses `x-api-key` + `anthropic-version` headers
- response is `{content: [{type: "text", text: "..."}]}`
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
        """Anthropic format: `{content: [{type: "text", text: "..."}]}`."""
        return data["content"][0]["text"]
