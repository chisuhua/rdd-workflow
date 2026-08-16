"""Unit tests for MCPTraceLogger (JSONL + redact)."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from skills.cross_repo_protocol.trace import MCPTraceLogger


@pytest.fixture
def trace_path(tmp_path):
    return tmp_path / ".rddf" / "state" / ".mcp-trace.jsonl"


def test_append_creates_directory_if_missing(trace_path):
    logger = MCPTraceLogger(trace_path)
    logger.append({"tool_name": "test", "args_hash": "abc"})
    assert trace_path.parent.exists()


def test_appends_jsonl_format(trace_path):
    logger = MCPTraceLogger(trace_path)
    logger.append({"tool_name": "hub_read_issue", "duration_ms": 50})
    logger.append({"tool_name": "hub_create_issue", "duration_ms": 100})
    lines = trace_path.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert "timestamp" in record
        assert "tool_name" in record
        assert "duration_ms" in record


def test_redact_masks_sensitive_fields():
    entry = {"token": "secret-abc", "args": {"password": "hunter2"}}
    redacted = MCPTraceLogger.redact(entry)
    assert redacted["token"] == "***REDACTED***"
    assert redacted["args"]["password"] == "***REDACTED***"


def test_compute_duration():
    start = 100.0
    end = 100.25
    assert MCPTraceLogger.compute_duration_ms(start, end) == 250
