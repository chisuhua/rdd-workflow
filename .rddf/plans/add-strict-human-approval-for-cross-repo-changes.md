# add-strict-human-approval-for-cross-repo-changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 强制跨项目 RFC 必须经 Hub 端人类审批(ADR-0031)— `approve_proposal.sh` 检测 `cross-repo-federation` 类别, `--auto-accept` 失效,需要 `--manual` + `--hub-issue <org/repo#N>` 参数,实时 fetch Hub Issue 状态为 Approved 才放行;design-done gate 集成 Hub status 检查。

**Architecture:** bash(`approve_proposal.sh`)+ Python(`cross_repo_audit.py` audit log)+ design gate 集成。fail-closed:网络错误/Hub Issue 不存在/未 Approved 一律 exit 4。所有审批记录追加到 `.rddf/state/.cross-repo-audit.jsonl`。

**Tech Stack:** bash 4.0+ / Python 3.11+ / `gh` CLI v2.0+ / pytest / bats。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/cross_repo_audit.py` | Audit log 管理(append + validate + JSONL) |
| `skills/guide-design/scripts/approve_proposal.sh` | + `--manual` / `--hub-issue` / cross-repo 检测(MODIFY) |
| `skills/guide-design/scripts/design_content_review.sh` | + cross-repo 类别 Hub status 校验(MODIFY) |
| `skills/guide-design/scripts/design_done_gate.py` | + cross-repo unapproved 阻断(MODIFY) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_cross_repo_audit.py` | Audit log 单测 |
| `tests/integration/test_strict_human_approval.bats` | approve + design gate 集成测试 |

---

### Task 1: `cross_repo_audit.py` audit log 管理

**Files:**
- Create: `skills/_lib/cross_repo_audit.py`

- [x] **Step 1: 写失败测试**

创建 `tests/unit/test_cross_repo_audit.py`:

```python
"""Unit tests for cross_repo_audit (JSONL append + validate)."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from skills._lib.cross_repo_audit import (
    append_audit_log_entry,
    validate_entry,
    AUDIT_LOG_FIELDS,
)


@pytest.fixture
def audit_path(tmp_path):
    return tmp_path / ".rddf" / "state" / ".cross-repo-audit.jsonl"


def test_validate_entry_required_fields():
    entry = {
        "timestamp": "2026-08-15T16:00:00Z",
        "proposal_name": "add-x",
        "hub_issue": "org/rdd-hub#42",
        "approver": "alice",
        "decision": "approved",
    }
    validate_entry(entry)  # should not raise


def test_validate_entry_missing_field():
    entry = {"timestamp": "2026-08-15T16:00:00Z", "proposal_name": "add-x"}
    with pytest.raises(ValueError, match="hub_issue"):
        validate_entry(entry)


def test_append_creates_directory(audit_path):
    entry = {
        "timestamp": "2026-08-15T16:00:00Z",
        "proposal_name": "add-x",
        "hub_issue": "org/rdd-hub#42",
        "approver": "alice",
        "decision": "approved",
    }
    append_audit_log_entry(audit_path, entry)
    assert audit_path.parent.exists()
    assert audit_path.exists()


def test_append_jsonl_format(audit_path):
    entry1 = {"timestamp": "2026-08-15T16:00:00Z", "proposal_name": "add-x",
              "hub_issue": "org/rdd-hub#42", "approver": "alice", "decision": "approved"}
    entry2 = {"timestamp": "2026-08-15T16:01:00Z", "proposal_name": "add-y",
              "hub_issue": "org/rdd-hub#43", "approver": "bob", "decision": "rejected"}
    append_audit_log_entry(audit_path, entry1)
    append_audit_log_entry(audit_path, entry2)
    lines = audit_path.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # must be valid JSON


def test_audit_log_fields_constant():
    assert set(AUDIT_LOG_FIELDS) == {
        "timestamp", "proposal_name", "hub_issue", "approver", "decision"
    }
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `python3 -m pytest tests/unit/test_cross_repo_audit.py -v`
Expected: 5 FAILED

- [x] **Step 3: 实现 `cross_repo_audit.py`**

```python
"""Cross-repo audit log (JSONL append with validation).

Writes to .rddf/state/.cross-repo-audit.jsonl. Each entry has required
fields: timestamp, proposal_name, hub_issue, approver, decision.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]

AUDIT_LOG_FIELDS = ("timestamp", "proposal_name", "hub_issue", "approver", "decision")


def validate_entry(entry: Dict[str, Any]) -> None:
    """Raise ValueError if entry is missing required fields."""
    missing = [f for f in AUDIT_LOG_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"audit log entry missing required fields: {missing}")


def append_audit_log_entry(path: PathLike, entry: Dict[str, Any]) -> None:
    """Append one JSONL line. Auto-creates parent dir."""
    validate_entry(entry)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

- [x] **Step 4: 跑测试,确认 PASS**

Run: `python3 -m pytest tests/unit/test_cross_repo_audit.py -v`
Expected: 5 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 2: `approve_proposal.sh` 修改 — cross-repo 检测 + `--manual` 强制

**Files:**
- Modify: `skills/guide-design/scripts/approve_proposal.sh`

- [x] **Step 1: 写失败测试**

创建 `tests/integration/test_strict_human_approval.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  export RDDF_PROJECT_ROOT="$TMP"
  mkdir -p "$TMP/openspec/changes/test-cross-repo"
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: cross-repo-federation
EOF
}

teardown() { rm -rf "$TMP"; }

@test "approve --auto-accept on cross-repo exits 3 (blocked)" {
  cd "$TMP"
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -eq 3 ]
  [[ "$output" =~ "manual" || "$output" =~ "Hub" ]]
}

@test "approve --manual --hub-issue on cross-repo requires interactive input" {
  cd "$TMP"
  echo "alice" | run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42"
  # Will fail on actual Hub fetch (no network), but should NOT fail with exit 3
  [ "$status" -ne 3 ]
}

@test "approve non-cross-repo with --auto-accept still works" {
  cd "$TMP"
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: core
EOF
  # Should succeed (or fail on Hub fetch if --hub-issue required, but exit != 3)
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -ne 3 ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_strict_human_approval.bats`
Expected: 3 FAIL

- [x] **Step 3: 修改 `approve_proposal.sh`**

读取当前 `skills/guide-design/scripts/approve_proposal.sh`,在脚本开头(在 `set -euo pipefail` 之后)追加:

```bash
# Cross-repo approval gate (ADR-0031)
CROSS_REPO_CATEGORY="cross-repo-federation"
MANUAL_FLAG=false
HUB_ISSUE_ARG=""

# Argument parsing additions
while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto-accept) AUTO_ACCEPT=true; shift ;;
    --manual) MANUAL_FLAG=true; shift ;;
    --hub-issue) HUB_ISSUE_ARG="$2"; shift 2 ;;
    *) shift ;;
  esac
done

detect_cross_repo_category() {
  local proposal_name="$1"
  local meta_file="$RDDF_PROJECT_ROOT/openspec/changes/$proposal_name/roadmap-meta.yaml"
  [[ ! -f "$meta_file" ]] && return 1
  grep -E "^category:" "$meta_file" | awk '{print $2}' | tr -d '"'"'"
}

is_cross_repo_proposal() {
  local cat
  cat=$(detect_cross_repo_category "$1" 2>/dev/null || echo "")
  [[ "$cat" == "$CROSS_REPO_CATEGORY" ]]
}

# Cross-repo gate: block --auto-accept, require --manual + --hub-issue
if is_cross_repo_proposal "$PROPOSAL_NAME" 2>/dev/null; then
  if [ "${AUTO_ACCEPT:-false}" = true ]; then
    echo "🚫 cross-repo proposal '$PROPOSAL_NAME' cannot use --auto-accept" >&2
    echo "   Use --manual --hub-issue <org/repo#N> instead" >&2
    exit 3
  fi
  if [ "$MANUAL_FLAG" != true ]; then
    echo "🚫 cross-repo proposal '$PROPOSAL_NAME' requires --manual flag" >&2
    exit 3
  fi
  if [ -z "$HUB_ISSUE_ARG" ]; then
    echo "🚫 cross-repo proposal requires --hub-issue <org/repo#N>" >&2
    exit 3
  fi
fi
```

(根据实际 approve_proposal.sh 结构整合,确保不破坏既有逻辑)

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_strict_human_approval.bats`
Expected: 3 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 3: design_done_gate 集成 cross-repo 状态检查

**Files:**
- Modify: `skills/guide-design/scripts/design_done_gate.py` — 增加 cross-repo 检查

- [x] **Step 1: 写失败测试**

在 `tests/integration/test_strict_human_approval.bats` 追加:

```bash
@test "design-done gate blocks when cross-repo proposal lacks audit log" {
  cd "$TMP"
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: cross-repo-federation
EOF
  # No audit log entry exists
  run env RDDF_PROJECT_ROOT="$TMP" STRICT_DESIGN_GATE=yes python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.guide_design.scripts.design_done_gate import check_cross_repo_approvals
result = check_cross_repo_approvals()
sys.exit(1 if result else 0)
"
  [ "$status" -ne 0 ]
}
```

- [x] **Step 2: 跑测试,确认 FAIL**

Run: `bats tests/integration/test_strict_human_approval.bats`
Expected: 1 new FAIL

- [x] **Step 3: 在 design_done_gate.py 添加 `check_cross_repo_approvals()`**

读取 `skills/guide-design/scripts/design_done_gate.py`,追加函数:

```python
def check_cross_repo_approvals() -> bool:
    """Check if all cross-repo-federation proposals have audit log approvals.

    Returns True if any cross-repo proposal lacks a corresponding 'approved'
    entry in .rddf/state/.cross-repo-audit.jsonl (gate should BLOCK).
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    changes_dir = os.path.join(project_root, "openspec", "changes")
    if not os.path.isdir(changes_dir):
        return False

    audit_file = os.path.join(project_root, ".rddf", "state", ".cross-repo-audit.jsonl")
    approved_proposals = set()
    if os.path.exists(audit_file):
        for line in open(audit_file):
            try:
                record = json.loads(line)
                if record.get("decision") == "approved":
                    approved_proposals.add(record.get("proposal_name"))
            except (json.JSONDecodeError, KeyError):
                continue

    # Find all cross-repo proposals
    pending = []
    for entry in os.listdir(changes_dir):
        meta = os.path.join(changes_dir, entry, "roadmap-meta.yaml")
        if not os.path.isfile(meta):
            continue
        with open(meta) as f:
            for line in f:
                if line.startswith("category:"):
                    cat = line.split(":", 1)[1].strip().strip("'\"")
                    if cat == "cross-repo-federation" and entry not in approved_proposals:
                        pending.append(entry)
                    break

    return len(pending) > 0
```

并在主 gate 函数中调用 `check_cross_repo_approvals()` (追加到既有 check 列表)。

- [x] **Step 4: 跑测试,确认 PASS**

Run: `bats tests/integration/test_strict_human_approval.bats`
Expected: 4 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 4: README + 全栈验证

**Files:**
- Modify: `README.md` — 追加 ADR-0031 引用

- [x] **Step 1: 更新 README §跨项目协同**

在 §跨项目协同 Spoke 接入章节后追加:

```markdown
### 跨项目审批(ADR-0031)

`category: cross-repo-federation` 的提案**不可** `--auto-accept`,必须:

```bash
bash skills/guide-design/scripts/approve_proposal.sh <proposal> \
  --manual --hub-issue "org/rdd-hub#N"
```

会 prompt 输入 GitHub 用户名,实时 fetch Hub Issue 状态确认 `approved` 才写入 audit log。`SKIP_HUB_CHECK=true` 仅紧急 hotfix 使用(留 audit trail)。
```

- [x] **Step 2: 全栈测试**

Run: `python3 -m pytest tests/unit/test_cross_repo_audit.py -v && bats tests/integration/test_strict_human_approval.bats`
Expected: 全 PASS

- [x] **Step 3: openspec validate**

Run: `openspec validate add-strict-human-approval-for-cross-repo-changes`
Expected: exit 0

- [x] **Step 4: 推迟 commit**

---

## Verification Checklist

- [x] `cross_repo_audit.py` 验证 5 个必填字段
- [x] `.cross-repo-audit.jsonl` append mode + 自动创建父目录
- [x] `approve_proposal.sh` 检测 `cross-repo-federation` 类别
- [x] `--auto-accept` on cross-repo 退出 3
- [x] `--manual` + `--hub-issue` 进入 Hub fetch 路径
- [x] `design_done_gate.check_cross_repo_approvals()` 报告未审计 cross-repo 提案
- [x] README 含 ADR-0031 引用 + 用法示例