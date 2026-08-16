"""MCP call trace logger (JSONL + sensitive field redaction.

Writes one JSON line per MCP call to .rddf/state/.mcp-trace.jsonl.
Format conforms to _lib/schemas/mcp_trace_schema.json v1 (SSOT from W2-2).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]

_SENSITIVE_KEYS = {"token", "secret", "password", "api_key", "authorization"}


class MCPTraceLogger:
    """Append-only JSONL trace logger for MCP calls."""

    def __init__(self, path: PathLike):
        self.path = Path(path)

    def append(self, entry: Dict[str, Any]) -> None:
        """Append one JSON line. Auto-creates parent dir."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        record = self.redact(entry)
        with self.path.open("a") as f:
            f.write(json.dumps(record) + "\n")

    @staticmethod
    def redact(obj: Any) -> Any:
        """Recursively mask sensitive keys with ***REDACTED***."""
        if isinstance(obj, dict):
            return {
                k: ("***REDACTED***" if k.lower() in _SENSITIVE_KEYS else MCPTraceLogger.redact(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [MCPTraceLogger.redact(v) for v in obj]
        return obj

    @staticmethod
    def compute_duration_ms(start: float, end: float) -> int:
        """Compute duration in milliseconds between two time.time() values."""
        return int((end - start) * 1000)
