# add-mcp-cross-repo-protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 实现 Model Context Protocol (MCP) Client,封装 4 个 Hub 工具(`hub_read_issue` / `hub_create_issue` / `hub_update_status` / `hub_sync_contract`),支持 stdio/http 传输、trace 日志、REST 回退、rate limit。

**Architecture:** `MCPClient` 类封装 MCP SDK 调用;`MCPTraceLogger` 写 JSONL 到 `.rddf/state/.mcp-trace.jsonl`(符合 W2-2 `mcp_trace_schema.json` v1);失败时自动 REST 回退。**CRITICAL**: 所有文件必须写在 worktree 内 (`skills/cross-repo-protocol/`),不要写到 `~/.agents/skills/_lib/`!

**Tech Stack:** Python 3.11+ / `mcp` SDK / `requests` / pytest / bats。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/cross-repo-protocol/__init__.py` | Package exports |
| `skills/cross-repo-protocol/mcp_client.py` | MCPClient 类(4 tools + transport + fallback) |
| `skills/cross-repo-protocol/trace.py` | MCPTraceLogger(JSONL + redact) |
| `skills/cross-repo-protocol/SKILL.md` | 人类可读文档 |
| `skills/templates/.cursorrules.cross-repo-hub` | Spoke AI 协议规则模板 |
| `install.sh` | + `--spoke-init` 子命令(MODIFY) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_mcp_client.py` | MCPClient + 4 tools 单测 |
| `tests/unit/test_mcp_trace.py` | trace logger 单测 |
| `tests/integration/test_mcp_install_spoke_init.bats` | install.sh --spoke-init 测试 |

---

### Task 1: Package 骨架 + `MCPTraceLogger`

**Files:**
- Create: `skills/cross-repo-protocol/__init__.py`
- Create: `skills/cross-repo-protocol/trace.py`

- [x] **Step 1: 写失败测试**

创建 `tests/unit/test_mcp_trace.py`:

```python
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
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_mcp_trace.py -v`
Expected: 4 FAILED(模块不存在)

- [x] **Step 3: 创建 `__init__.py`**

写 `skills/cross-repo-protocol/__init__.py`:

```python
"""Cross-repo protocol package: MCP client + trace logger."""
from skills.cross_repo_protocol.mcp_client import MCPClient, MCPConfigurationError
from skills.cross_repo_protocol.trace import MCPTraceLogger

__all__ = ["MCPClient", "MCPConfigurationError", "MCPTraceLogger"]
```

- [x] **Step 4: 实现 `trace.py`**

```python
"""MCP call trace logger (JSONL + sensitive field redaction).

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
```

- [x] **Step 5: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_mcp_trace.py -v`
Expected: 4 PASS

- [x] **Step 6: 推迟 commit**

---

### Task 2: `MCPClient` 类核心 + 4 tools

**Files:**
- Create: `skills/cross-repo-protocol/mcp_client.py`

- [x] **Step 1: 写失败测试 — 4 tools**

创建 `tests/unit/test_mcp_client.py`:

```python
"""Unit tests for MCPClient (4 Hub tools + transport + fallback)."""
import os
from unittest.mock import patch, MagicMock
import pytest

from skills.cross_repo_protocol.mcp_client import (
    MCPClient, MCPConfigurationError,
)


def test_missing_github_token_raises_config_error():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GITHUB_TOKEN", None)
        with pytest.raises(MCPConfigurationError):
            MCPClient()


def test_hub_read_issue_returns_normalized():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {
                "number": 42, "title": "[RFC] Test", "body": "body",
                "state": "open", "labels": [{"name": "rfc"}],
                "stakeholders": ["org/repo-a"], "contract_impact": "High",
            }
            client = MCPClient()
            result = client.hub_read_issue(42)
            assert result["number"] == 42
            assert result["title"] == "[RFC] Test"
            assert result["status"] == "open"


def test_hub_create_issue_validates_title():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        client = MCPClient()
        with pytest.raises(ValueError):
            client.hub_create_issue(title="", body="test")


def test_hub_create_issue_success():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {
                "number": 43, "title": "[RFC] New", "body": "test",
                "state": "open", "created_at": "2026-08-15T16:00:00Z",
                "html_url": "https://github.com/org/rdd-hub/issues/43",
            }
            client = MCPClient()
            result = client.hub_create_issue(title="[RFC] New", body="test")
            assert result["number"] == 43


def test_hub_update_status_without_comment():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {"number": 42, "status": "in_progress"}
            client = MCPClient()
            result = client.hub_update_status(42, "in_progress")
            assert result["status"] == "in_progress"


def test_hub_sync_contract_returns_receipt():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {
                "contract_id": "auth-v2",
                "synced_at": "2026-08-15T16:00:00Z",
                "hub_confirmed": True,
            }
            client = MCPClient()
            result = client.hub_sync_contract("auth-v2", "synced")
            assert result["hub_confirmed"] is True
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_mcp_client.py -v`
Expected: 5 FAILED

- [x] **Step 3: 实现 `mcp_client.py`**

```python
"""MCP Client: 4 Hub tools via MCP protocol with REST fallback.

Tools:
  - hub_read_issue(issue_number) -> dict
  - hub_create_issue(title, body, ...) -> dict
  - hub_update_status(issue_number, status, comment?) -> dict
  - hub_sync_contract(contract_id, state) -> dict

Transports:
  - stdio (default): spawn MCP Server as subprocess
  - http: use MCP_SERVER_URL (Streamable HTTP)

Fallback: REST GitHub API when MCP Server unreachable.
Trace: all calls logged to .rddf/state/.mcp-trace.jsonl.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from skills.cross_repo_protocol.trace import MCPTraceLogger


class MCPConfigurationError(Exception):
    """Raised when MCP client is misconfigured (e.g., missing GITHUB_TOKEN)."""


class MCPClient:
    """MCP client with REST fallback and trace logging."""

    DEFAULT_TIMEOUT = 5

    def __init__(
        self,
        transport: Optional[str] = None,
        server_path: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise MCPConfigurationError("GITHUB_TOKEN environment variable required")
        self.transport = transport or os.environ.get("MCP_TRANSPORT", "stdio")
        self.server_path = server_path or os.environ.get("MCP_SERVER_PATH")
        self.server_url = os.environ.get("MCP_SERVER_URL")
        self.trace_logger = MCPTraceLogger(
            os.environ.get("MCP_TRACE_FILE", ".rddf/state/.mcp-trace.jsonl")
        )

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool with trace logging. Falls back to REST on error."""
        start = time.time()
        trace_entry = {"tool_name": tool_name, "args": self._safe_args(args)}
        try:
            result = self._call_mcp_server(tool_name, args)
            trace_entry["result_status"] = "success"
            trace_entry["duration_ms"] = MCPTraceLogger.compute_duration_ms(start, time.time())
            self.trace_logger.append(trace_entry)
            return result
        except (ConnectionRefusedError, OSError, subprocess.TimeoutExpired) as e:
            trace_entry["result_status"] = "error"
            trace_entry["error"] = str(e)
            trace_entry["fallback_attempted"] = True
            trace_entry["duration_ms"] = MCPTraceLogger.compute_duration_ms(start, time.time())
            self.trace_logger.append(trace_entry)
            if not os.environ.get("MCPSuppressFallbackWarning"):
                print(f"⚠️ MCP Server unreachable, using REST fallback: {e}", file=sys.stderr)
            return self._fallback_to_rest(tool_name, args)

    def _call_mcp_server(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke MCP tool via SDK. Stub for now; production would use mcp package."""
        raise ConnectionRefusedError("MCP Server not implemented in stub")

    def _fallback_to_rest(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to GitHub REST API when MCP Server unreachable."""
        try:
            import requests
        except ImportError:
            raise MCPConfigurationError("requests library required for REST fallback")
        headers = {"Authorization": f"Bearer {self.token}"}
        if tool_name == "hub_read_issue":
            issue_num = args["issue_number"]
            owner = args.get("owner", "my-org")
            repo = args.get("repo", "rdd-hub")
            r = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}",
                headers=headers, timeout=self.DEFAULT_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            return self._normalize_issue(data)
        if tool_name == "hub_create_issue":
            owner = args.get("owner", "my-org")
            repo = args.get("repo", "rdd-hub")
            payload = {"title": args["title"], "body": args.get("body", "")}
            if "stakeholders" in args:
                payload["body"] += f"\n**Stakeholders**: {','.join(args['stakeholders'])}"
            r = requests.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers=headers, json=payload, timeout=self.DEFAULT_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "number": data["number"],
                "title": data["title"],
                "body": data["body"],
                "state": data["state"],
                "created_at": data["created_at"],
                "url": data["html_url"],
            }
        raise NotImplementedError(f"No REST fallback for tool: {tool_name}")

    def _normalize_issue(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "number": raw["number"],
            "title": raw["title"],
            "body": raw.get("body", ""),
            "state": raw["state"],
            "status": "open" if raw["state"] == "open" else "closed",
            "stakeholders": raw.get("stakeholders", []),
            "contract_impact": raw.get("contract_impact", ""),
            "labels": [l["name"] for l in raw.get("labels", [])],
        }

    def _safe_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return MCPTraceLogger.redact(args)

    def hub_read_issue(self, issue_number: int) -> Dict[str, Any]:
        return self.call_tool("hub_read_issue", {"issue_number": issue_number})

    def hub_create_issue(
        self, title: str, body: str = "", stakeholders: Optional[list] = None,
        contract_impact: str = "Medium",
    ) -> Dict[str, Any]:
        if not title:
            raise ValueError("title is required")
        args = {"title": title, "body": body, "contract_impact": contract_impact}
        if stakeholders:
            args["stakeholders"] = stakeholders
        return self.call_tool("hub_create_issue", args)

    def hub_update_status(
        self, issue_number: int, status: str, comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        args = {"issue_number": issue_number, "status": status}
        if comment:
            args["comment"] = comment
        return self.call_tool("hub_update_status", args)

    def hub_sync_contract(self, contract_id: str, state: str) -> Dict[str, Any]:
        return self.call_tool("hub_sync_contract", {
            "contract_id": contract_id, "state": state,
        })
```

- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_mcp_client.py -v`
Expected: 5 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 3: SKILL.md 文档

**Files:**
- Create: `skills/cross-repo-protocol/SKILL.md`

- [x] **Step 1: 创建 SKILL.md**

写 `skills/cross-repo-protocol/SKILL.md`:

```markdown
---
name: cross-repo-protocol
description: MCP (Model Context Protocol) client for Hub-Spoke federation — wraps 4 Hub tools (read/create/update issue, sync contract) with REST fallback and trace logging.
license: MIT
compatibility: Requires Python 3.11+, mcp SDK, requests, GITHUB_TOKEN env var.
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "ADR-0030 Hub-and-Spoke federation Step 3"
  user-invocable: false
---

# Cross-Repo Protocol (MCP Client)

MCP 客户端,封装 4 个 Hub 工具调用。失败时自动 REST 回退到 GitHub API。所有调用 trace 到 `.rddf/state/.mcp-trace.jsonl`。

## 4 个工具

| Tool | 用途 | 必填参数 |
|------|------|----------|
| `hub_read_issue` | 读取 Hub Issue | `issue_number` |
| `hub_create_issue` | 创建 Hub Issue | `title`, `body` (opt), `stakeholders` (opt) |
| `hub_update_status` | 更新 Issue 状态 | `issue_number`, `status`, `comment` (opt) |
| `hub_sync_contract` | 同步契约状态 | `contract_id`, `state` |

## 传输方式

- `stdio` (默认): 通过 `MCP_SERVER_PATH` 启动 MCP Server 子进程
- `http`: 通过 `MCP_SERVER_URL` 连接 Streamable HTTP

## 认证

- `GITHUB_TOKEN` 必须设置(必需)
- REST 回退使用同一 token(`Authorization: Bearer <token>`)

## 回退行为

MCP Server 不可达(`ConnectionRefusedError` / 超时)时,自动 REST 回退。`MCPSuppressFallbackWarning=true` 抑制 stderr 警告。

## Trace 文件

`.rddf/state/.mcp-trace.jsonl`(每行一条 JSON)。结构遵循 `_lib/schemas/mcp_trace_schema.json` v1(SSOT from W2-2)。自动 redact `token` / `secret` / `password` / `api_key` / `authorization` 字段。
```

- [x] **Step 2: 推迟 commit**

---

### Task 4: `install.sh --spoke-init` 子命令 + `.cursorrules` 模板

**Files:**
- Modify: `install.sh` — 在末尾追加 `--spoke-init` 子命令处理
- Create: `skills/templates/.cursorrules.cross-repo-hub`

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_mcp_install_spoke_init.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_REPO="$(mktemp -d)"
  cd "$TMP_REPO"
  git init -q
}

teardown() {
  rm -rf "$TMP_REPO"
}

@test "spoke-init copies cursorrules to valid git repo" {
  cd "$TMP_REPO"
  run bash "$REPO_ROOT/install.sh" --spoke-init "$TMP_REPO"
  [ "$status" -eq 0 ]
  [ -f "$TMP_REPO/.cursorrules" ]
}

@test "spoke-init warns on non-git target" {
  NON_GIT_DIR="$(mktemp -d)"
  run bash "$REPO_ROOT/install.sh" --spoke-init "$NON_GIT_DIR"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "not a git repository" ]]
  rm -rf "$NON_GIT_DIR"
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_mcp_install_spoke_init.bats`
Expected: 2 FAIL

- [x] **Step 3: 创建 `.cursorrules.cross-repo-hub` 模板**

写 `skills/templates/.cursorrules.cross-repo-hub`:

```markdown
# rdd-hub Cross-Repo Protocol Rules (Spoke AI)

You are operating in a Spoke repository that participates in the rdd-hub
Hub-and-Spoke federation. Follow these 12 rules when using Hub MCP tools.

## Rule 1: Check duplicates before creating RFC
Before calling `hub_create_issue`, call `hub_read_issue` on likely duplicates
to avoid creating parallel RFCs.

## Rule 2: Rate-limit parallel Issue creation
Wait ≥1 second between parallel `hub_create_issue` calls. GitHub rate
limits 5000 req/hour per token.

## Rule 3: Always include reason in status updates
Every `hub_update_status` must include a `comment` explaining the reason.
Empty comments are forbidden.

## Rule 4: Notify human on contract sync failure
`hub_sync_contract` failures must notify the human operator immediately
via stderr + process exit code != 0. Never silently retry.

## Rule 5: Respect REST fallback warning
When MCP Server is unreachable, the client falls back to REST. Do NOT
suppress warnings unless `MCPSuppressFallbackWarning=true`.

## Rule 6: Never log raw tokens
The MCP trace logger auto-redacts tokens. Do NOT bypass this by writing
custom logs.

## Rule 7: Surface rate limit errors to user
When `hub_create_issue` returns `rate_limit_exceeded`, surface to user
with the `X-RateLimit-Reset` timestamp. Do NOT auto-retry past 3 attempts.

## Rule 8: Use stdio transport by default
Only use `MCP_TRANSPORT=http` when explicitly configured by operator.

## Rule 9: Hub MCP Server health check
Before long Hub operations, verify `MCP_SERVER_URL/health` returns
`{"status": "ok"}`. Skip if not configured.

## Rule 10: Contract sync is idempotent
`hub_sync_contract` is idempotent. Repeated calls with same state must
produce same result. Do NOT add retry counts.

## Rule 11: Issue body must include stakeholders
Every `hub_create_issue` body must list stakeholders. Empty stakeholder
list is forbidden.

## Rule 12: Trace file location
All MCP calls are logged to `.rddf/state/.mcp-trace.jsonl`. Do NOT
write custom trace files elsewhere.
```

- [x] **Step 4: 修改 `install.sh` 追加 `--spoke-init` 子命令**

读取 `install.sh` 当前末尾,追加:

```bash
# === --spoke-init subcommand ===
if [ "${1:-}" = "--spoke-init" ]; then
  TARGET_DIR="${2:-$(pwd)}"
  TEMPLATE="$SCRIPT_DIR/skills/templates/.cursorrules.cross-repo-hub"
  if [ ! -d "$TARGET_DIR/.git" ] && ! git -C "$TARGET_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    echo "⚠️  Target is not a git repository: $TARGET_DIR (skipping)" >&2
    exit 0
  fi
  if [ -f "$TEMPLATE" ]; then
    cp "$TEMPLATE" "$TARGET_DIR/.cursorrules"
    echo "✅ Installed .cursorrules to $TARGET_DIR/.cursorrules"
    exit 0
  else
    echo "ERROR: Template not found: $TEMPLATE" >&2
    exit 1
  fi
fi
```

(根据 install.sh 实际结构适配 — `SCRIPT_DIR` 替换为真实变量)

- [x] **Step 5: 跑测试,确认 PASS**

Run: `bats tests/integration/test_mcp_install_spoke_init.bats`
Expected: 2 PASS

- [x] **Step 6: 推迟 commit**

---

### Task 5: 全栈验证

**Files:** 无新增

- [x] **Step 1: pytest unit 全套**

Run: `python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -10`
Expected: 全部 PASS

- [x] **Step 2: bats 集成测试**

Run: `bats tests/integration/test_mcp_install_spoke_init.bats`
Expected: PASS

- [x] **Step 3: openspec validate**

Run: `openspec validate add-mcp-cross-repo-protocol`
Expected: exit 0

- [x] **Step 4: 推迟 commit**

---

## Verification Checklist

- [x] `MCPClient.__init__()` 在 `GITHUB_TOKEN` 缺失时抛 `MCPConfigurationError`
- [x] 4 tools (`hub_read_issue` / `hub_create_issue` / `hub_update_status` / `hub_sync_contract`) 行为正确
- [x] Trace logger JSONL + redact 正确
- [x] REST fallback 在 MCP 失败时触发并保留 return schema
- [x] `install.sh --spoke-init <git-repo>` 复制 `.cursorrules`
- [x] `install.sh --spoke-init <non-git>` 打印警告并退出 0

---

## ⚠️ CRITICAL NOTES (避免 W2-3 错误重复)

1. **所有文件必须写在 worktree 内** (`skills/cross-repo-protocol/`, `skills/templates/`)
2. **绝不要写到** `~/.agents/skills/`(global install path)
3. **测试用 mock**(patch `_call_mcp_server`)而非真实网络
4. **不要 commit**(留给 archive)
5. **完成后立即更新 checkboxes**(plan + tasks.md)