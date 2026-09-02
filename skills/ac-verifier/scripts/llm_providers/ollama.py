"""Ollama provider — OpenAI-compatible endpoint at localhost:11434.

Ollama ignores the Authorization header; we still require AC_LLM_API_KEY
to be set because BaseHTTPProvider's __init__ rejects empty keys. Users
can pass any non-empty placeholder (e.g. "ollama").
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
