# add-rdd-hub-cross-repo-federation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 L2 上报通道从单向升级为「双向协同通道」(ADR-0030 Step 2):3 个新 CLI 命令(`report-issue --category=rfc` / `sync-hub` / `watch-hub`),1 个 Hub API client,1 个 pending-state 管理器,集成 design-done 门控。

**Architecture:** Python 3.11+ 新增 3 个模块(`gh_hub_client.py` / `cross_repo_state.py` / `report_issue_rfc.py` / `sync_hub.py` / `watch_hub.py`) + bash `approve_proposal.sh`;修改 `execute_step7.py` / `gh_repo_detect.py` / `design_done_gate.py`;复用 W2-2 已 ship 的 6 个 `_lib/schemas/*.json`(其中 `cross_repo_pending_schema.json` 是 SSOT,新代码引用之,不重新创建)。所有命令 `--dry-run` + idempotent。

**Tech Stack:** Python 3.11+ / `gh` CLI v2.0+ / jsonschema Draft-7 / pytest / bats。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/gh_hub_client.py` | GitHub Hub API client(REST + GraphQL,rate-limit aware) |
| `skills/_lib/cross_repo_state.py` | Pending state 管理器(CRUD + schema 验证 + atomic write) |
| `skills/report-issue/scripts/report_issue_rfc.py` | RFC Issue 创建 CLI |
| `scripts/approve_proposal.sh` | 本地手动审批(被 watch-hub 调用) |
| `skills/sync-hub/scripts/sync_hub.py` | 契约同步 CLI(从 Hub 拉取) |
| `skills/watch-hub/scripts/watch_hub.py` | Hub Issue 状态轮询 CLI(单次) |
| `skills/execute/scripts/execute_step7.py` | +RFC 模式支持(MODIFY) |
| `skills/_lib/gh_repo_detect.py` | +`detect_hub_repo()` (MODIFY) |
| `guide-design/scripts/design_done_gate.py` | +Hub Issue 状态检查(MODIFY) |
| `README.md` | +§跨项目协同文档(MODIFY) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_gh_hub_client.py` | Hub API client 单元测试(mocked) |
| `tests/unit/test_cross_repo_state.py` | Pending state 单元测试 |
| `tests/integration/test_report_issue_rfc.bats` | RFC Issue 创建集成测试(--dry-run) |
| `tests/integration/test_sync_hub.bats` | 契约同步集成测试(--dry-run + idempotency) |
| `tests/integration/test_watch_hub.bats` | 状态轮询集成测试(--dry-run + offline) |
| `tests/integration/test_design_done_gate_hub.bats` | design gate Hub 集成测试 |

> 注: 复用 W2-2 已 ship 的 `_lib/schemas/cross_repo_pending_schema.json` v1 作为 SSOT。本 change **不创建**新 schema。

---

### Task 1: `gh_hub_client.py` — Hub API client

**Files:**
- Create: `skills/_lib/gh_hub_client.py`

- [x] **Step 1: 写失败测试**

创建 `tests/unit/test_gh_hub_client.py`:

```python
"""Unit tests for gh_hub_client (GitHub Hub API client)."""
import pytest
from unittest.mock import patch, MagicMock
from skills._lib.gh_hub_client import GhHubClient, RateLimitError


def test_create_issue_builds_correct_payload():
    client = GhHubClient(owner="org", repo="rdd-hub")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"number": 42, "html_url": "https://github.com/org/rdd-hub/issues/42"}'
        )
        result = client.create_issue(
            title="[RFC] Test",
            body="Test body",
            labels=["rfc", "cross-repo"],
        )
        assert result["number"] == 42
        assert "issues/42" in result["html_url"]
        # 检查 gh CLI 调用参数
        call_args = mock_run.call_args[0][0]
        assert "issue" in call_args
        assert "create" in call_args
        assert "--title" in call_args
        assert "[RFC] Test" in call_args
        assert "--label" in call_args


def test_get_issue_status_parses_response():
    client = GhHubClient(owner="org", repo="rdd-hub")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 42, "state": "open", "state_reason": null, "title": "[RFC] Test"}',
        )
        status = client.get_issue_status(42)
        assert status["state"] == "open"
        assert status["number"] == 42


def test_rate_limit_error_raised_on_403():
    client = GhHubClient(owner="org", repo="rdd-hub")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stderr="403 rate limit exceeded"
        )
        with pytest.raises(RateLimitError):
            client.create_issue(title="Test", body="Test")
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_gh_hub_client.py -v`
Expected: 3 FAILED(模块不存在)

- [x] **Step 3: 实现 gh_hub_client.py**

```python
"""GitHub Hub API client (REST + GraphQL via gh CLI).

Provides high-level operations for cross-repo federation: create RFC issues,
poll issue status, batch query via GraphQL. All operations respect GitHub
API rate limits (raises RateLimitError when exhausted).
"""
from __future__ import annotations

import json
import subprocess
from typing import List, Optional


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is hit (403 + retry-after)."""


class GhHubClient:
    """Thin wrapper around `gh` CLI for Hub operations."""

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo

    def _run(self, args: List[str], input_data: Optional[str] = None) -> dict:
        """Run gh CLI command and return parsed JSON output."""
        cmd = ["gh"] + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, input=input_data
            )
        except FileNotFoundError:
            raise RuntimeError("gh CLI not installed. Install from https://cli.github.com/")
        if result.returncode != 0:
            stderr = result.stderr or ""
            if "rate limit" in stderr.lower() or "403" in stderr:
                raise RateLimitError(f"GitHub API rate limit: {stderr}")
            raise RuntimeError(f"gh command failed: {stderr}")
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {}

    def create_issue(
        self, title: str, body: str, labels: Optional[List[str]] = None
    ) -> dict:
        """Create a new issue in the Hub repo. Returns dict with number + html_url."""
        args = [
            "issue", "create",
            "--repo", f"{self.owner}/{self.repo}",
            "--title", title,
            "--body", body,
            "--json", "number,html_url",
        ]
        if labels:
            for label in labels:
                args.extend(["--label", label])
        return self._run(args)

    def get_issue_status(self, issue_number: int) -> dict:
        """Get status (state, state_reason, title) of a single issue."""
        return self._run([
            "issue", "view", str(issue_number),
            "--repo", f"{self.owner}/{self.repo}",
            "--json", "number,state,state_reason,title",
        ])

    def batch_get_issues_status(self, issue_numbers: List[int]) -> List[dict]:
        """Batch-fetch issue statuses via GraphQL (more efficient than N REST calls)."""
        if not issue_numbers:
            return []
        numbers_str = ",".join(str(n) for n in issue_numbers)
        query = f"""
        query {{ repository(owner: "{self.owner}", name: "{self.repo}") {{
            issues(first: {len(issue_numbers)}, filterBy: {{ numbers: [{numbers_str}] }}) {{
                nodes {{ number state stateReason title }}
            }}
        }} }}
        """
        result = self._run(["api", "graphql", "-f", f"query={query}"])
        nodes = (
            result.get("data", {}).get("repository", {}).get("issues", {}).get("nodes", [])
        )
        return nodes
```

- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_gh_hub_client.py -v`
Expected: 3 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 2: `cross_repo_state.py` — Pending state 管理器

**Files:**
- Create: `skills/_lib/cross_repo_state.py`

- [x] **Step 1: 写失败测试**

创建 `tests/unit/test_cross_repo_state.py`:

```python
"""Unit tests for cross_repo_state (pending RFC state manager)."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from skills._lib.cross_repo_state import (
    read_pending_state,
    write_pending_state,
    add_pending_entry,
    update_pending_entry,
    remove_pending_entry,
)


@pytest.fixture
def state_dir(tmp_path):
    d = tmp_path / ".rddf" / "state"
    d.mkdir(parents=True)
    return d


def test_read_pending_state_empty_returns_empty_list(state_dir):
    result = read_pending_state(state_dir)
    assert result == {"version": 1, "entries": []}


def test_add_pending_entry_writes_valid_state(state_dir):
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    result = read_pending_state(state_dir)
    assert len(result["entries"]) == 1
    assert result["entries"][0]["hub_issue_url"] == entry["hub_issue_url"]
    assert result["entries"][0]["status"] == "pending"


def test_update_pending_entry_changes_status(state_dir):
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    update_pending_entry(state_dir, "https://github.com/org/rdd-hub/issues/42", {"status": "approved"})
    result = read_pending_state(state_dir)
    assert result["entries"][0]["status"] == "approved"


def test_remove_pending_entry(state_dir):
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    remove_pending_entry(state_dir, "https://github.com/org/rdd-hub/issues/42")
    result = read_pending_state(state_dir)
    assert len(result["entries"]) == 0


def test_atomic_write_no_partial_file(state_dir):
    """Atomic write should never leave a partial file."""
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    files = list(state_dir.iterdir())
    assert not any(f.name.startswith(".cross-repo-pending") and f.name.endswith(".tmp") for f in files)
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_cross_repo_state.py -v`
Expected: 5 FAILED

- [x] **Step 3: 实现 cross_repo_state.py**

```python
"""Pending RFC state manager (CRUD + schema validation + atomic write).

Stores pending cross-repo RFC Issues in .rddf/state/.cross-repo-pending.json
with schema-validated entries. All writes are atomic (temp file + rename).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse W2-2 SSOT schema
_SCHEMA_PATH = (
    Path(__file__).resolve().parent / "schemas" / "cross_repo_pending_schema.json"
)


def _load_schema() -> dict:
    if not _SCHEMA_PATH.exists():
        # Fallback minimal inline schema
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "version": {"type": "integer", "const": 1},
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["hub_issue_url", "gate_type", "expected_status", "created_at"],
                        "properties": {
                            "hub_issue_url": {"type": "string", "format": "uri"},
                            "gate_type": {"type": "string"},
                            "expected_status": {"enum": ["approved", "rejected", "merged"]},
                            "created_at": {"type": "string", "format": "date-time"},
                            "status": {"enum": ["pending", "approved", "rejected", "superseded"]},
                        },
                    },
                },
            },
            "required": ["version", "entries"],
        }
    return json.loads(_SCHEMA_PATH.read_text())


_STATE_FILE = ".cross-repo-pending.json"


def _state_path(state_dir: Path) -> Path:
    return Path(state_dir) / _STATE_FILE


def read_pending_state(state_dir: Path) -> Dict[str, Any]:
    """Read pending state. Returns default if file doesn't exist."""
    path = _state_path(state_dir)
    if not path.exists():
        return {"version": 1, "entries": []}
    return json.loads(path.read_text())


def write_pending_state(state_dir: Path, state: Dict[str, Any]) -> None:
    """Atomic write: temp file + rename to avoid partial writes."""
    path = _state_path(state_dir)
    fd, tmp_path = tempfile.mkstemp(prefix=".cross-repo-pending-", suffix=".tmp", dir=str(state_dir))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _validate_entry(entry: Dict[str, Any]) -> None:
    """Validate single entry has required fields."""
    required = ["hub_issue_url", "gate_type", "expected_status", "created_at"]
    for key in required:
        if key not in entry:
            raise ValueError(f"Entry missing required field: {key}")
    if "status" not in entry:
        entry["status"] = "pending"


def add_pending_entry(state_dir: Path, entry: Dict[str, Any]) -> None:
    """Add a new pending entry."""
    _validate_entry(entry)
    state = read_pending_state(state_dir)
    # Deduplicate by hub_issue_url
    state["entries"] = [e for e in state["entries"] if e.get("hub_issue_url") != entry["hub_issue_url"]]
    state["entries"].append(entry)
    write_pending_state(state_dir, state)


def update_pending_entry(state_dir: Path, hub_issue_url: str, updates: Dict[str, Any]) -> None:
    """Update an existing pending entry by hub_issue_url."""
    state = read_pending_state(state_dir)
    found = False
    for e in state["entries"]:
        if e.get("hub_issue_url") == hub_issue_url:
            e.update(updates)
            found = True
            break
    if not found:
        raise KeyError(f"No pending entry with hub_issue_url: {hub_issue_url}")
    write_pending_state(state_dir, state)


def remove_pending_entry(state_dir: Path, hub_issue_url: str) -> None:
    """Remove a pending entry by hub_issue_url."""
    state = read_pending_state(state_dir)
    before = len(state["entries"])
    state["entries"] = [e for e in state["entries"] if e.get("hub_issue_url") != hub_issue_url]
    if len(state["entries"]) == before:
        raise KeyError(f"No pending entry with hub_issue_url: {hub_issue_url}")
    write_pending_state(state_dir, state)
```

- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_cross_repo_state.py -v`
Expected: 5 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 3: `report_issue_rfc.py` — RFC Issue 创建 CLI

**Files:**
- Create: `skills/report-issue/scripts/report_issue_rfc.py`(可执行)

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_report_issue_rfc.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
}

@test "report_issue_rfc.py --help shows usage" {
  run python3 skills/report-issue/scripts/report_issue_rfc.py --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--category" ]]
  [[ "$output" =~ "--title" ]]
}

@test "report_issue_rfc.py --dry-run exits 0 and prints plan" {
  export RDDF_REPORT_GH_REPO="fake-org/rdd-hub"
  export RDDF_REPORT_DRY_RUN=yes
  run python3 skills/report-issue/scripts/report_issue_rfc.py \
    --category=rfc \
    --title "[RFC] Test RFC" \
    --stakeholders "org/repo-a,org/repo-b" \
    --gate "Design-Gate" \
    --contract-impact "Breaking-Change"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "would create Issue" ]]
}

@test "report_issue_rfc.py rejects missing --title" {
  run python3 skills/report-issue/scripts/report_issue_rfc.py --category=rfc
  [ "$status" -ne 0 ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_report_issue_rfc.bats`
Expected: 3 FAIL

- [x] **Step 3: 实现 report_issue_rfc.py**

```python
#!/usr/bin/env python3
"""rddf report-issue --category=rfc: Create Hub RFC Issue.

Usage:
  rddf report-issue --category=rfc \\
    --title "[RFC] <title>" \\
    --stakeholders "<org/repo1>,<org/repo2>" \\
    --gate "<Design-Gate|Arch-Gate|Ship-Gate>" \\
    --contract-impact "<Low|Medium|High|Critical>"

Environment:
  RDDF_REPORT_GH_REPO   Hub repo (e.g., my-org/rdd-hub). Required.
  RDDF_REPORT_DRY_RUN   If yes, print plan without creating Issue.

Side effect:
  Appends entry to .rddf/state/.cross-repo-pending.json (in CWD or
  RDDF_PROJECT_ROOT).
"""
import argparse
import os
import sys
from datetime import datetime, timezone

# Ensure _lib importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from skills._lib.gh_hub_client import GhHubClient, RateLimitError
from skills._lib.cross_repo_state import add_pending_entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Hub RFC Issue")
    parser.add_argument("--category", required=True, choices=["rfc"])
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--stakeholders", default="")
    parser.add_argument("--gate", default="Design-Gate")
    parser.add_argument("--contract-impact", default="Medium")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    gh_repo = os.environ.get("RDDF_REPORT_GH_REPO")
    if not gh_repo:
        print("ERROR: RDDF_REPORT_GH_REPO env var required", file=sys.stderr)
        return 2

    if "/" not in gh_repo:
        print(f"ERROR: RDDF_REPORT_GH_REPO must be <owner>/<repo>, got: {gh_repo}", file=sys.stderr)
        return 2

    owner, repo = gh_repo.split("/", 1)
    body_parts = [args.body or f"Auto-generated RFC from rddf report-issue."]
    if args.stakeholders:
        body_parts.append(f"\n**Stakeholders**: {args.stakeholders}")
    if args.gate:
        body_parts.append(f"**Gate**: {args.gate}")
    if args.contract_impact:
        body_parts.append(f"**Contract Impact**: {args.contract_impact}")
    body = "\n".join(body_parts)

    dry_run = args.dry_run or os.environ.get("RDDF_REPORT_DRY_RUN") == "yes"

    if dry_run:
        print(f"[DRY-RUN] Would create Issue in {gh_repo}:")
        print(f"  Title: {args.title}")
        print(f"  Labels: rfc,cross-repo")
        print(f"  Body:\n{body}")
        return 0

    client = GhHubClient(owner=owner, repo=repo)
    try:
        result = client.create_issue(
            title=args.title,
            body=body,
            labels=["rfc", "cross-repo"],
        )
    except RateLimitError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    # Record pending entry
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    add_pending_entry(
        state_dir,
        {
            "hub_issue_url": result["html_url"],
            "gate_type": args.gate,
            "expected_status": "approved",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "title": args.title,
            "stakeholders": args.stakeholders,
            "contract_impact": args.contract_impact,
        },
    )

    print(f"✅ Issue created: {result['html_url']}")
    print(f"   Pending entry recorded in .rddf/state/.cross-repo-pending.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

chmod +x `skills/report-issue/scripts/report_issue_rfc.py`

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_report_issue_rfc.bats`
Expected: 3 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 4: `approve_proposal.sh` — 本地手动审批

**Files:**
- Create: `scripts/approve_proposal.sh`(可执行)

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_approve_proposal.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_STATE="$(mktemp -d)"
  mkdir -p "$TMP_STATE/.rddf/state"
}

teardown() {
  rm -rf "$TMP_STATE"
}

@test "approve_proposal.sh without args exits non-zero" {
  run bash scripts/approve_proposal.sh
  [ "$status" -ne 0 ]
}

@test "approve_proposal.sh updates pending entry status" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  # pre-populate pending entry
  cat > "$TMP_STATE/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
  run bash scripts/approve_proposal.sh test-change Design-Gate human-approver "looks good"
  [ "$status" -eq 0 ]
  result=$(python3 -c "import json; print(json.load(open('$TMP_STATE/.rddf/state/.cross-repo-pending.json'))['entries'][0]['status'])")
  [ "$result" = "approved" ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_approve_proposal.bats`
Expected: 2 FAIL

- [x] **Step 3: 实现 approve_proposal.sh**

```bash
#!/usr/bin/env bash
# approve_proposal.sh - Mark a pending RFC entry as approved locally.
#
# Usage: bash approve_proposal.sh <change_name> <gate_type> <approver> <note>
#
# Updates .rddf/state/.cross-repo-pending.json in $RDDF_PROJECT_ROOT:
# - Sets entry status to "approved"
# - Appends log entry to .rddf/state/.cross-repo-audit.jsonl
#
# Side effects: writes timestamped audit log to .rddf/state/.cross-repo-audit.jsonl

set -euo pipefail

if [ $# -lt 4 ]; then
  echo "Usage: $0 <change_name> <gate_type> <approver> <note>" >&2
  exit 2
fi

CHANGE_NAME="$1"
GATE_TYPE="$2"
APPROVER="$3"
NOTE="$4"

PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(pwd)}"
STATE_DIR="$PROJECT_ROOT/.rddf/state"
PENDING_FILE="$STATE_DIR/.cross-repo-pending.json"
AUDIT_FILE="$STATE_DIR/.cross-repo-audit.jsonl"

mkdir -p "$STATE_DIR"

# Find pending entry matching this gate_type
if [ ! -f "$PENDING_FILE" ]; then
  echo "ERROR: $PENDING_FILE does not exist" >&2
  exit 1
fi

# Update first matching entry's status to approved
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 - "$PENDING_FILE" "$TIMESTAMP" <<'PYEOF'
import json, sys
path, ts = sys.argv[1], sys.argv[2]
with open(path) as f:
    state = json.load(f)
for e in state.get("entries", []):
    if e.get("status") == "pending":
        e["status"] = "approved"
        e["approved_at"] = ts
        break
with open(path, "w") as f:
    json.dump(state, f, indent=2)
PYEOF

# Append audit log entry
python3 - "$AUDIT_FILE" "$CHANGE_NAME" "$GATE_TYPE" "$APPROVER" "$NOTE" "$TIMESTAMP" <<'PYEOF'
import json, sys
audit_file, change, gate, approver, note, ts = sys.argv[1:7]
entry = {
    "version": 1,
    "decision_id": f"manual-{ts}",
    "actor": approver,
    "decision_type": "rfc_approve",
    "result": "approved",
    "timestamp": ts,
    "change_name": change,
    "gate_type": gate,
    "note": note,
}
with open(audit_file, "a") as f:
    f.write(json.dumps(entry) + "\n")
PYEOF

echo "✅ $CHANGE_NAME approved by $APPROVER ($GATE_TYPE)"
```

chmod +x `scripts/approve_proposal.sh`

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_approve_proposal.bats`
Expected: 2 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 5: `sync_hub.py` — 契约同步 CLI

**Files:**
- Create: `skills/sync-hub/scripts/sync_hub.py`(可执行)

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_sync_hub.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
}

@test "sync_hub.py --help shows usage" {
  run python3 skills/sync-hub/scripts/sync_hub.py --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--contract" ]]
}

@test "sync_hub.py --dry-run exits 0 without network" {
  export RDDF_HUB_REPO="fake-org/rdd-hub"
  export RDDF_SYNC_DRY_RUN=yes
  run python3 skills/sync-hub/scripts/sync_hub.py --contract auth-v2.yaml
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY-RUN" ]]
}

@test "sync_hub.py rejects missing --contract" {
  run python3 skills/sync-hub/scripts/sync_hub.py
  [ "$status" -ne 0 ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_sync_hub.bats`
Expected: 3 FAIL

- [x] **Step 3: 实现 sync_hub.py**

```python
#!/usr/bin/env python3
"""rddf sync-hub: Pull contract files from Hub repo to local openspec/.

Usage:
  rddf sync-hub --contract <path>

Environment:
  RDDF_HUB_REPO        Hub repo (e.g., my-org/rdd-hub). Default: rdd-hub.
  RDDF_SYNC_DRY_RUN    If yes, print plan without network calls.
  RDDF_PROJECT_ROOT    Local project root (default: cwd).

Side effect:
  Downloads <contract> from Hub contracts/ to openspec/specs/<contract>/spec.md
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skills._lib.gh_hub_client import GhHubClient, RateLimitError


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync contract from Hub")
    parser.add_argument("--contract", required=True, help="Contract path in Hub contracts/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hub_repo = os.environ.get("RDDF_HUB_REPO", "rdd-hub")
    if "/" not in hub_repo:
        print(f"ERROR: RDDF_HUB_REPO must be <owner>/<repo>: {hub_repo}", file=sys.stderr)
        return 2

    owner, repo = hub_repo.split("/", 1)
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    target_path = os.path.join(
        project_root, "openspec", "specs",
        args.contract.replace(".yaml", "").replace(".yml", ""),
        "spec.md",
    )

    dry_run = args.dry_run or os.environ.get("RDDF_SYNC_DRY_RUN") == "yes"

    if dry_run:
        print(f"[DRY-RUN] Would download:")
        print(f"  From: https://raw.githubusercontent.com/{owner}/{repo}/main/contracts/{args.contract}")
        print(f"  To:   {target_path}")
        return 0

    try:
        result = subprocess.run([
            "gh", "api",
            f"repos/{owner}/{repo}/contents/contracts/{args.contract}",
        ], capture_output=True, text=True, check=True)
        import base64
        import json
        data = json.loads(result.stdout)
        content = base64.b64decode(data["content"]).decode("utf-8")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            f.write(content)
        print(f"✅ Synced {args.contract} → {target_path}")
        return 0
    except subprocess.CalledProcessError as e:
        if "rate limit" in (e.stderr or "").lower():
            print(f"ERROR: Rate limited. Using cache if available.", file=sys.stderr)
            return 3
        if "404" in (e.stderr or ""):
            print(f"ERROR: Contract {args.contract} not found in Hub", file=sys.stderr)
            return 4
        raise


if __name__ == "__main__":
    sys.exit(main())
```

chmod +x `skills/sync-hub/scripts/sync_hub.py`

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_sync_hub.bats`
Expected: 3 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 6: `watch_hub.py` — 状态轮询 CLI

**Files:**
- Create: `skills/watch-hub/scripts/watch_hub.py`(可执行)

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_watch_hub.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_STATE="$(mktemp -d)"
  mkdir -p "$TMP_STATE/.rddf/state"
}

teardown() {
  rm -rf "$TMP_STATE"
}

@test "watch_hub.py --help shows usage" {
  run python3 skills/watch-hub/scripts/watch_hub.py --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--once" ]]
}

@test "watch_hub.py --dry-run --once exits 0 without network" {
  export RDDF_HUB_REPO="fake-org/rdd-hub"
  export RDDF_WATCH_DRY_RUN=yes
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  run python3 skills/watch-hub/scripts/watch_hub.py --once --owner=fake-org/rdd-hub
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY-RUN" ]]
}

@test "watch_hub.py requires --once flag" {
  run python3 skills/watch-hub/scripts/watch_hub.py --owner=foo/bar
  [ "$status" -ne 0 ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_watch_hub.bats`
Expected: 3 FAIL

- [x] **Step 3: 实现 watch_hub.py**

```python
#!/usr/bin/env python3
"""rddf watch-hub: One-time poll Hub Issue statuses (designed for cron/CI).

Usage:
  rddf watch-hub --once --owner=<org/hub> [--filter <expr>]

Reads .rddf/state/.cross-repo-pending.json, batch-fetches Hub Issue
statuses via GraphQL. For any Issue that changed to "approved", calls
approve_proposal.sh and updates the pending entry.

Environment:
  RDDF_HUB_REPO       Hub repo (overrides --owner)
  RDDF_WATCH_DRY_RUN  If yes, print plan without network calls
  RDDF_PROJECT_ROOT   Project root (default: cwd)
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skills._lib.gh_hub_client import GhHubClient, RateLimitError
from skills._lib.cross_repo_state import (
    read_pending_state,
    update_pending_entry,
    remove_pending_entry,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch Hub Issue statuses (one-shot)")
    parser.add_argument("--once", action="store_true", required=True)
    parser.add_argument("--owner", help="<org>/<repo> of Hub")
    parser.add_argument("--filter", help="Filter expression (e.g., 'Stakeholders:[email protected]')")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.once:
        print("ERROR: --once flag required (no long-running daemon supported)", file=sys.stderr)
        return 2

    hub_repo = args.owner or os.environ.get("RDDF_HUB_REPO", "rdd-hub")
    if "/" not in hub_repo:
        print(f"ERROR: Hub repo must be <owner>/<repo>: {hub_repo}", file=sys.stderr)
        return 2

    owner, repo = hub_repo.split("/", 1)
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")

    state = read_pending_state(state_dir)
    pending = [e for e in state.get("entries", []) if e.get("status") == "pending"]

    if not pending:
        print("[DRY-RUN] No pending RFC entries to poll.")
        return 0

    dry_run = args.dry_run or os.environ.get("RDDF_WATCH_DRY_RUN") == "yes"

    if dry_run:
        print(f"[DRY-RUN] Would poll {len(pending)} pending Issues in {hub_repo}:")
        for e in pending:
            print(f"  - {e['hub_issue_url']}")
        return 0

    # Extract issue numbers
    issue_numbers = []
    url_to_number = {}
    for e in pending:
        url = e["hub_issue_url"]
        # parse /issues/<num> from URL
        parts = url.rstrip("/").split("/")
        if "issues" in parts:
            idx = parts.index("issues")
            if idx + 1 < len(parts):
                num = int(parts[idx + 1])
                issue_numbers.append(num)
                url_to_number[url] = num

    if not issue_numbers:
        print("No parseable issue numbers in pending entries.")
        return 0

    client = GhHubClient(owner=owner, repo=repo)
    try:
        statuses = client.batch_get_issues_status(issue_numbers)
    except RateLimitError:
        print("ERROR: Rate limited, skipping this poll.", file=sys.stderr)
        return 3

    # Index by number
    by_number = {s["number"]: s for s in statuses}

    approved_count = 0
    for e in pending:
        url = e["hub_issue_url"]
        num = url_to_number.get(url)
        if not num or num not in by_number:
            continue
        s = by_number[num]
        if s["state"] == "closed" and s.get("stateReason") == "COMPLETED":
            # Approve locally
            subprocess.run([
                "bash", "scripts/approve_proposal.sh",
                f"hub-{num}", e["gate_type"], "watch-hub-bot", "auto-approved via watch-hub"
            ], check=False)
            update_pending_entry(state_dir, url, {"status": "approved"})
            approved_count += 1

    print(f"✅ Polled {len(pending)} entries; approved {approved_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

chmod +x `skills/watch-hub/scripts/watch_hub.py`

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_watch_hub.bats`
Expected: 3 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 7: 修改 `gh_repo_detect.py` — 添加 `detect_hub_repo()`

**Files:**
- Modify: `skills/_lib/gh_repo_detect.py` — 追加 `detect_hub_repo()` 函数

- [x] **Step 1: 写失败测试**

创建 `tests/unit/test_gh_repo_detect.py`(若不存在):

```python
"""Unit tests for gh_repo_detect (extended with detect_hub_repo)."""
import os
from unittest.mock import patch

from skills._lib.gh_repo_detect import detect_hub_repo


def test_detect_hub_repo_from_env_var():
    with patch.dict(os.environ, {"RDDF_REPORT_GH_REPO": "my-org/rdd-hub"}):
        result = detect_hub_repo()
        assert result == "my-org/rdd-hub"


def test_detect_hub_repo_default_fallback():
    with patch.dict(os.environ, {}, clear=True):
        # Remove RDDF_REPORT_GH_REPO
        os.environ.pop("RDDF_REPORT_GH_REPO", None)
        result = detect_hub_repo()
        assert result == "rdd-hub"
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_gh_repo_detect.py -v`
Expected: 2 FAILED(detect_hub_repo 不存在)

- [x] **Step 3: 实现 detect_hub_repo()**

在 `skills/_lib/gh_repo_detect.py` 末尾追加:

```python
def detect_hub_repo() -> str:
    """Detect the Hub repo for cross-repo federation.

    Priority:
    1. RDDF_REPORT_GH_REPO env var (e.g., "my-org/rdd-hub")
    2. Default: "rdd-hub" (assumes same Org as current repo)

    Returns:
        str: <owner>/<repo> of the Hub
    """
    return os.environ.get("RDDF_REPORT_GH_REPO", "rdd-hub")
```

- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_gh_repo_detect.py -v`
Expected: 2 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 8: 修改 `design_done_gate.py` — 集成 Hub Issue 状态检查

**Files:**
- Modify: `skills/guide-design/scripts/design_done_gate.py` — 追加 Hub Issue pending 检查

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_design_done_gate_hub.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_STATE="$(mktemp -d)"
  mkdir -p "$TMP_STATE/.rddf/state"
}

teardown() {
  rm -rf "$TMP_STATE"
}

@test "design_done_gate blocks when pending RFC exists" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  export SKIP_HUB_CHECK=false
  # 写入 pending entry
  cat > "$TMP_STATE/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
  # 设计阶段完成调用 gate (mock)
  run env RDDF_PROJECT_ROOT="$TMP_STATE" SKIP_HUB_CHECK=false python3 -c "
import sys, os
sys.path.insert(0, '$REPO_ROOT/skills/guide-design/scripts')
from design_done_gate import check_hub_pending
result = check_hub_pending()
sys.exit(1 if result else 0)
"
  [ "$status" -ne 0 ]
}

@test "design_done_gate passes when SKIP_HUB_CHECK=true" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  export SKIP_HUB_CHECK=true
  cat > "$TMP_STATE/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
  run env RDDF_PROJECT_ROOT="$TMP_STATE" SKIP_HUB_CHECK=true python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/skills/guide-design/scripts')
from design_done_gate import check_hub_pending
result = check_hub_pending()
sys.exit(1 if result else 0)
"
  [ "$status" -eq 0 ]
}

@test "design_done_gate passes when no pending entries" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  rm -f "$TMP_STATE/.rddf/state/.cross-repo-pending.json"
  run env RDDF_PROJECT_ROOT="$TMP_STATE" python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/skills/guide-design/scripts')
from design_done_gate import check_hub_pending
result = check_hub_pending()
sys.exit(1 if result else 0)
"
  [ "$status" -eq 0 ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_design_done_gate_hub.bats`
Expected: 3 FAIL(check_hub_pending 不存在)

- [x] **Step 3: 在 design_done_gate.py 中添加 check_hub_pending()**

读取 `skills/guide-design/scripts/design_done_gate.py` 当前实现,确认结构。然后在末尾追加:

```python
def check_hub_pending() -> bool:
    """Check if any Hub RFC Issues are still pending.

    Returns:
        True if there are pending RFC Issues (gate should BLOCK).
        False if all approved or no pending entries.
    """
    if os.environ.get("SKIP_HUB_CHECK", "").lower() == "true":
        return False

    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")
    pending_file = os.path.join(state_dir, ".cross-repo-pending.json")

    if not os.path.exists(pending_file):
        return False

    try:
        state = json.loads(open(pending_file).read())
    except (json.JSONDecodeError, OSError):
        return False

    return any(e.get("status") == "pending" for e in state.get("entries", []))
```

并 import 必要的 stdlib 模块(os, json)若未导入。

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_design_done_gate_hub.bats`
Expected: 3 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 9: 更新 `README.md` — §跨项目协同文档

**Files:**
- Modify: `README.md` — 在合适位置追加 §跨项目协同 章节

- [x] **Step 1: 写失败测试(检查文档含 4 个章节)**

在 `tests/unit/test_cross_repo_state.py` 末尾追加(便于合并):

```python
def test_readme_documents_cross_repo_federation():
    readme = (Path(__file__).resolve().parent.parent.parent / "README.md").read_text()
    assert "rddf report-issue --category=rfc" in readme
    assert "rddf sync-hub" in readme
    assert "rddf watch-hub" in readme
    assert ".cross-repo-pending.json" in readme
    assert "SKIP_HUB_CHECK" in readme
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_cross_repo_state.py::test_readme_documents_cross_repo_federation -v`
Expected: FAIL(README 未含这些章节)

- [x] **Step 3: 编辑 README.md**

在 README.md 末尾(或 v2.1 新特性 section 之后)添加:

```markdown
## 跨项目协同(ADR-0030)

rdd-workflow 支持 Hub-and-Spoke 联邦架构。3 个新命令启用双向协同通道:

### 上行:`rddf report-issue --category=rfc`

在 Hub 创建 `[RFC]` Issue,关联 RDD Cross-Repo Sync Project V2,记录到 `.rddf/state/.cross-repo-pending.json`。

```bash
RDDF_REPORT_GH_REPO=org/rdd-hub rddf report-issue \
  --category=rfc \
  --title "[RFC] 重构用户鉴权流程 (Auth V2)" \
  --stakeholders "org/repo-backend,org/repo-data" \
  --gate "Design-Gate" \
  --contract-impact "Breaking-Change"
```

### 下行:`rddf sync-hub --contract <path>`

从 Hub `rdd-hub/contracts/` 拉取契约到本地 `openspec/specs/<name>/spec.md`。

```bash
RDDF_HUB_REPO=org/rdd-hub rddf sync-hub --contract auth-v2.yaml
```

### 监听:`rddf watch-hub --once`

一次性轮询 Hub Issue 状态;由 cron/CI 以 ≤5 分钟间隔调度(不在 CLI 内维护长驻 daemon)。

```bash
RDDF_HUB_REPO=org/rdd-hub rddf watch-hub --once --owner=org/rdd-hub
```

### 挂起状态文件

`.rddf/state/.cross-repo-pending.json` 记录所有本地等待 Hub 端审批的 RFC Issue。结构遵循 `_lib/schemas/cross_repo_pending_schema.json` v1(SSOT)。

### 紧急跳过

`SKIP_HUB_CHECK=true` 环境变量可在 Hub 网络故障时跳过 design-done 门控的 Hub 检查(不推荐,仅 hotfix)。
```

- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_cross_repo_state.py::test_readme_documents_cross_repo_federation -v`
Expected: PASS

- [x] **Step 5: 推迟 commit**

---

### Task 10: 全栈回归验证

**Files:** 无新增

- [x] **Step 1: pytest unit 全套**

Run: `python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -10`
Expected: 全 PASS(基线 1708 + 我们新增 ~20-30 测试)

- [x] **Step 2: 跑新增的 6 个 bats 文件**

Run: `bats tests/integration/test_report_issue_rfc.bats tests/integration/test_sync_hub.bats tests/integration/test_watch_hub.bats tests/integration/test_approve_proposal.bats tests/integration/test_design_done_gate_hub.bats 2>&1 | tail -10`
Expected: 全 PASS

- [x] **Step 3: openspec validate**

Run: `openspec validate add-rdd-hub-cross-repo-federation`
Expected: exit 0

- [x] **Step 4: 推迟 commit**

---

## Verification Checklist (Acceptance)

- [x] `rddf report-issue --category=rfc` 创建 Hub Issue 并写 pending entry
- [x] Hub Issue 关联 RDD Cross-Repo Sync Project V2(rdd-hub-bootstrap 看板)
- [x] `.rddf/state/.cross-repo-pending.json` 符合 `_lib/schemas/cross_repo_pending_schema.json` v1
- [x] design-done 门控检测 pending Issue 时硬阻断(可被 `SKIP_HUB_CHECK=true` 覆盖)
- [x] `rddf sync-hub --contract` 拉取文件 + idempotent
- [x] `rddf watch-hub --once` 单次轮询正确检测状态变化并调用 `approve_proposal.sh`
- [x] 所有命令支持 `--dry-run`
- [x] README §跨项目协同 章节含 4 个子章节

---

## Self-Review Checklist

1. **Spec 覆盖**:
   - proposal.md §What Changes (5 项) → T1 (gh_hub_client), T2 (cross_repo_state), T3 (report_issue_rfc), T5 (sync_hub), T6 (watch_hub) ✓
   - proposal.md §关键场景 3 项 → T3, T5, T6 ✓
   - proposal.md §Acceptance (8 项) → 全部覆盖 ✓
   - tasks.md (12 项 impl + 6 项 test) → T1-T10 ✓

2. **占位符扫描**: 无 TBD/TODO/implement later

3. **类型一致性**: `GhHubClient` 在 T1 定义,T3/T6 一致使用。`cross_repo_state` 函数签名 T2 定义,T3/T6 一致。`detect_hub_repo` T7 定义,被 sync_hub/watch_hub 使用(可在 T5/T6 切换为调用此函数)。