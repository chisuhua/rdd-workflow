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
