# add-cross-repo-state-schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 验证 6 个新增 `_lib/schemas/*.json` 满足提案规范、补齐缺失字段、扩展 rdd-doctor 检测、补充单元测试和文档,确保跨项目 federation 6 个 state 文件有 SSOT schema。

**Architecture:** 6 个 JSON schema 文件已在 `_lib/schemas/` 中(`cross_repo_pending/audit/deps_cache`、`mcp_trace`、`contract_cache`、`hub_metrics`)。本 change 做 4 件事:(1) 补齐 2 个 schema 缺失的 `version` 字段(对齐 ADR-0016 模式);(2) 创建 `tests/unit/test_cross_repo_schemas.py`(6 schema × 3 验证 = 18 测试);(3) 扩展 `rdd-doctor` 的 `_STATE_FILES` 映射;(4) 创建 `docs/schemas/cross-repo-schemas.md` 字段语义文档。不创建新 schema(已存在),不修改 11 个旧 schema。

**Tech Stack:** Python 3.11+ / jsonschema (Draft-7) / pytest / bash (rdd-doctor)。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/schemas/cross_repo_audit_schema.json` | 跨项目决策审计(已存在,补 `version`) |
| `_lib/schemas/mcp_trace_schema.json` | MCP 调用追踪(已存在,补 `version`) |
| `skills/rdd-doctor/scripts/checks/state_schema_check.py` | 扩展 `_STATE_FILES` 包含 6 个新映射 |
| `docs/schemas/cross-repo-schemas.md` | 6 个 schema 字段语义文档 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_cross_repo_schemas.py` | 6 schema × 3 验证(valid / invalid-field / missing-field) |

---

### Task 1: 补齐 2 个 schema 缺失的 `version` 字段

**Files:**
- Modify: `_lib/schemas/cross_repo_audit_schema.json` — 在 `properties` 加 `version`,在 `required` 数组加 `"version"`
- Modify: `_lib/schemas/mcp_trace_schema.json` — 同上

- [x] **Step 1: 写失败测试 — 验证 version 字段存在**

创建 `tests/unit/test_cross_repo_schemas.py`(后续 task 会扩展):

```python
"""Unit tests for 6 cross-repo schemas (ADR-0030 + 7 related proposals).

Verifies ADR-0016 contract: each schema MUST have version (const:1) and $id.
"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "_lib" / "schemas"

SCHEMA_NAMES = [
    "cross_repo_pending_schema.json",
    "cross_repo_audit_schema.json",
    "mcp_trace_schema.json",
    "contract_cache_schema.json",
    "cross_repo_deps_cache_schema.json",
    "hub_metrics_schema.json",
]


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_schema_has_version_const_1(schema_name):
    """Each schema MUST pin version: 1 per ADR-0016 contract."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    assert "version" in schema["properties"], f"{schema_name} missing version property"
    assert schema["properties"]["version"]["const"] == 1
    assert "version" in schema["required"], f"{schema_name} missing version in required"
```

- [x] **Step 2: 运行测试,确认 2 个失败**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py::test_schema_has_version_const_1 -v`
Expected: 2 FAILED(cross_repo_audit + mcp_trace)

- [x] **Step 3: 给 cross_repo_audit_schema.json 加 version**

在 `properties` 块内添加:

```json
"version": {
  "type": "integer",
  "const": 1,
  "description": "Schema version. v1 introduces cross-repo decision audit records."
},
```

并在 `required` 数组添加 `"version"`。

- [x] **Step 4: 给 mcp_trace_schema.json 加 version**

同样在 `properties` 和 `required` 添加 `version` 字段,description 为 `"Schema version. v1 introduces MCP call trace records."`。

- [x] **Step 5: 运行测试,确认全部 PASS**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py::test_schema_has_version_const_1 -v`
Expected: 6/6 PASS

- [x] **Step 6: 推迟 commit**

---

### Task 2: 验证 $id 唯一标识 + schema dialect

**Files:**
- Modify: `tests/unit/test_cross_repo_schemas.py` — 追加 $id 测试

- [x] **Step 1: 写失败测试(若 $id 缺失或重复)**

在 `tests/unit/test_cross_repo_schemas.py` 追加:

```python
def test_all_schemas_have_unique_id():
    """Each schema MUST have unique $id (per ADR-0016 contract)."""
    ids = []
    for schema_name in SCHEMA_NAMES:
        schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
        sid = schema.get("$id")
        assert sid is not None, f"{schema_name} missing $id"
        ids.append(sid)
    assert len(ids) == len(set(ids)), f"Duplicate $id: {ids}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_schema_uses_draft7(schema_name):
    """Each schema MUST use JSON Schema Draft-7 (project standard)."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
```

- [x] **Step 2: 运行测试,确认通过(预期所有 6 个 schema 已有 $id 和 Draft-7)**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py -v -k "test_schema_uses_draft7 or test_all_schemas_have_unique_id"`
Expected: 7/7 PASS(若任何 schema 缺 $id 或重复,先修复)

- [x] **Step 3: 推迟 commit**

---

### Task 3: 为每个 schema 写 3 个验证测试(valid / invalid-field / missing-field)

**Files:**
- Modify: `tests/unit/test_cross_repo_schemas.py` — 追加 valid/invalid/missing 测试

- [x] **Step 1: 写 cross_repo_pending valid payload 测试**

在 `tests/unit/test_cross_repo_schemas.py` 追加:

```python
VALID_PAYLOADS = {
    "cross_repo_pending_schema.json": {
        "version": 1,
        "proposal_id": "my-org/rdd-workflow#42",
        "hub_issue_ref": "my-org/rdd-hub#7",
        "status": "pending_hub_approval",
        "created_at": "2026-08-15T16:00:00Z",
        "updated_at": "2026-08-15T16:00:00Z",
    },
    "cross_repo_audit_schema.json": {
        "version": 1,
        "decision_id": "dec-001",
        "actor": "agent-x",
        "decision_type": "rfc_propose",
        "result": "approved",
        "timestamp": "2026-08-15T16:00:00Z",
    },
    "mcp_trace_schema.json": {
        "version": 1,
        "timestamp": "2026-08-15T16:00:00Z",
        "direction": "spoke-to-hub",
        "tool_name": "hub_create_issue",
        "actor_repo": "org/repo-frontend",
        "args_hash": "abc123",
        "result_status": "success",
    },
    "contract_cache_schema.json": {
        "version": 1,
        "contract_name": "auth-v2",
        "contract_version": "2.0.0",
        "fetched_at": "2026-08-15T16:00:00Z",
        "source_hub": "my-org/rdd-hub",
        "sha256": "deadbeef0001",
    },
    "cross_repo_deps_cache_schema.json": {
        "version": 1,
        "repo_a": "org/repo-frontend",
        "repo_b": "org/repo-backend",
        "dep_type": "blocks",
        "reason": "auth-v2 contract",
        "last_synced": "2026-08-15T16:00:00Z",
    },
    "hub_metrics_schema.json": {
        "version": 1,
        "snapshot_at": "2026-08-15T16:00:00Z",
        "active_rfcs": 3,
        "merged_rfcs_30d": 12,
        "spoke_repos_count": 5,
    },
}


@pytest.mark.parametrize("schema_name,payload", list(VALID_PAYLOADS.items()))
def test_valid_payload_passes(schema_name, payload):
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(payload))
    assert not errors, f"Valid payload failed for {schema_name}: {[e.message for e in errors]}"
```

- [x] **Step 2: 写 invalid-field 测试(每个 schema)**

追加:

```python
@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_invalid_field_value_fails(schema_name):
    """Wrong-type field value must fail validation."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    validator = Draft7Validator(schema)
    # 把 version 改为字符串(应失败)
    payload = dict(VALID_PAYLOADS[schema_name])
    payload["version"] = "not-an-int"
    errors = list(validator.iter_errors(payload))
    assert errors, f"{schema_name} should fail with wrong version type"
```

- [x] **Step 3: 写 missing-field 测试(每个 schema)**

追加:

```python
@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_missing_required_field_fails(schema_name):
    """Removing required version must fail validation."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    validator = Draft7Validator(schema)
    payload = dict(VALID_PAYLOADS[schema_name])
    del payload["version"]
    errors = list(validator.iter_errors(payload))
    assert errors, f"{schema_name} should fail without version"
    assert any("version" in e.message for e in errors)
```

- [x] **Step 4: 运行测试,确认 18+ 全部 PASS**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py -v --tb=short`
Expected: 至少 18 PASS(6 schemas × 3 cases = 18) — 可能因为 `test_schema_uses_draft7` 等加上几个,总数 20+

- [x] **Step 5: 推迟 commit**

---

### Task 4: 扩展 rdd-doctor `_STATE_FILES` 映射

**Files:**
- Modify: `skills/rdd-doctor/scripts/checks/state_schema_check.py` — 在 `_STATE_FILES` dict 追加 6 个映射

- [x] **Step 1: 写失败测试 — rdd-doctor 检测 6 个 schema**

创建 `tests/unit/test_state_schema_check.py`(或追加到现有 `test_state_schema_check.py`):

```python
"""Test that rdd-doctor state_schema_check detects the 6 new cross-repo schemas."""
from pathlib import Path
import json
import tempfile

# 临时创建 .rddf/state 目录 + 6 个空文件
def test_state_schema_check_includes_cross_repo_schemas():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        state_dir = project_root / ".rddf" / "state"
        state_dir.mkdir(parents=True)

        # 6 个新 state 文件(空也行,但只触发 schema 查找)
        for fname in [
            ".cross-repo-pending.json",
            ".cross-repo-audit.jsonl",
            ".mcp-trace.jsonl",
            ".contract-cache.json",
            ".cross-repo-deps-cache.json",
            ".hub-metrics.json",
        ]:
            (state_dir / fname).write_text("{}")

        from skills.rdd_doctor.scripts.checks.state_schema_check import _STATE_FILES
        assert ".cross-repo-pending.json" in _STATE_FILES
        assert ".cross-repo-audit.jsonl" in _STATE_FILES
        assert ".mcp-trace.jsonl" in _STATE_FILES
        assert ".contract-cache.json" in _STATE_FILES
        assert ".cross-repo-deps-cache.json" in _STATE_FILES
        assert ".hub-metrics.json" in _STATE_FILES
```

- [x] **Step 2: 运行测试,确认失败**

Run: `python3 -m pytest tests/unit/test_state_schema_check.py -v --tb=short`
Expected: FAIL(`_STATE_FILES` 缺 6 个新映射)

- [x] **Step 3: 修改 `_STATE_FILES` 添加 6 个映射**

修改 `skills/rdd-doctor/scripts/checks/state_schema_check.py` line 16-21:

```python
_STATE_FILES = {
    "state_vector.json": "state_vector_schema.json",
    "sessions.json": "sessions_schema.json",
    "iteration.json": "iteration_schema.json",
    "deps_analysis.json": "deps_analysis_schema.json",
    # 6 新增 cross-repo federation schemas (ADR-0030 + 7 proposals)
    ".cross-repo-pending.json": "cross_repo_pending_schema.json",
    ".cross-repo-audit.jsonl": "cross_repo_audit_schema.json",
    ".mcp-trace.jsonl": "mcp_trace_schema.json",
    ".contract-cache.json": "contract_cache_schema.json",
    ".cross-repo-deps-cache.json": "cross_repo_deps_cache_schema.json",
    ".hub-metrics.json": "hub_metrics_schema.json",
}
```

- [x] **Step 4: 运行测试,确认通过**

Run: `python3 -m pytest tests/unit/test_state_schema_check.py -v --tb=short`
Expected: PASS

- [x] **Step 5: 推迟 commit**

---

### Task 5: 创建 `docs/schemas/cross-repo-schemas.md` 字段语义文档

**Files:**
- Create: `docs/schemas/cross-repo-schemas.md`

- [x] **Step 1: 写失败测试 — 文档存在 + 含 6 个 schema 标题**

在 `tests/unit/test_cross_repo_schemas.py` 追加:

```python
import os
DOCS_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "schemas" / "cross-repo-schemas.md"


def test_docs_file_exists():
    assert DOCS_PATH.exists(), f"Missing docs file: {DOCS_PATH}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_docs_mentions_each_schema(schema_name):
    content = DOCS_PATH.read_text()
    assert schema_name in content, f"docs missing reference to {schema_name}"
```

- [x] **Step 2: 运行测试,确认失败**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py -v -k "test_docs"`
Expected: 7/7 FAIL(文档不存在)

- [x] **Step 3: 创建 `docs/schemas/cross-repo-schemas.md`**

写文档,内容:

```markdown
# Cross-Repo Federation Schemas (v1)

> SSOT schema 定义,适用于 ADR-0030 Hub-and-Spoke 联邦架构及 7 个相关提案。
> 所有 schema 位于 `_lib/schemas/` 并通过 jsonschema Draft-7 验证。

## 1. `cross_repo_pending_schema.json` v1

**用途**: Hub Issue 挂起状态 — 跟踪本地提案等待 Hub 端审批的状态。

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | integer (const:1) | ✓ | Schema 版本 |
| `proposal_id` | string | ✓ | 本地 proposal 引用(格式: `<org>/<repo>#<num>`) |
| `hub_issue_ref` | string | ✓ | Hub Issue 引用(格式: `<org>/<hub-repo>#<num>`) |
| `status` | enum | ✓ | `pending_hub_approval` / `hub_approved` / `hub_rejected` / `merged` |
| `created_at` | date-time | ✓ | ISO-8601 |
| `updated_at` | date-time | ✓ | ISO-8601 |

## 2. `cross_repo_audit_schema.json` v1

**用途**: 跨项目决策审计日志 — 记录所有 RFC 提案 / 批准 / 拒绝事件的不可篡改审计。

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | integer (const:1) | ✓ | Schema 版本 |
| `decision_id` | string | ✓ | 决策唯一 ID |
| `actor` | string | ✓ | 决策执行者(AI 代理 / 人类用户名) |
| `decision_type` | enum | ✓ | `rfc_propose` / `rfc_approve` / `rfc_reject` / `contract_sync` |
| `result` | enum | ✓ | `approved` / `rejected` / `pending` |
| `timestamp` | date-time | ✓ | ISO-8601 |

## 3. `mcp_trace_schema.json` v1

**用途**: MCP (Model Context Protocol) 调用追踪 — 记录所有 Spoke ↔ Hub 的 MCP 消息。

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | integer (const:1) | ✓ | Schema 版本 |
| `timestamp` | date-time | ✓ | ISO-8601 |
| `direction` | enum | ✓ | `spoke-to-hub` / `hub-to-spoke` |
| `tool_name` | string | ✓ | MCP 工具名(例如 `hub_create_issue`) |
| `actor_repo` | string | ✓ | 发起方仓库(格式: `<org>/<repo>`) |
| `args_hash` | string | ✓ | 参数 SHA-256(用于脱敏 + 可重放) |
| `result_status` | enum | ✓ | `success` / `error` / `timeout` |

## 4. `contract_cache_schema.json` v1

**用途**: 契约版本缓存 — Spoke 端本地缓存的 Hub 契约版本。

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | integer (const:1) | ✓ | Schema 版本 |
| `contract_name` | string | ✓ | 契约名(例如 `auth-v2`) |
| `contract_version` | string | ✓ | SemVer(例如 `2.0.0`) |
| `fetched_at` | date-time | ✓ | ISO-8601 |
| `source_hub` | string | ✓ | 来源 Hub(格式: `<org>/<hub-repo>`) |
| `sha256` | string | ✓ | 契约文件 SHA-256 |

## 5. `cross_repo_deps_cache_schema.json` v1

**用途**: 跨仓库依赖缓存 — Spoke 端缓存的跨仓库依赖图。

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | integer (const:1) | ✓ | Schema 版本 |
| `repo_a` | string | ✓ | 仓库 A(格式: `<org>/<repo>`) |
| `repo_b` | string | ✓ | 仓库 B(格式: `<org>/<repo>`) |
| `dep_type` | enum | ✓ | `blocks` / `requires` / `related` |
| `reason` | string | ✓ | 依赖原因(例如契约名 / RFC ID) |
| `last_synced` | date-time | ✓ | ISO-8601 |

## 6. `hub_metrics_schema.json` v1

**用途**: Hub 运行时指标 — Spoke 端从 Hub 拉取的运行时统计。

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | integer (const:1) | ✓ | Schema 版本 |
| `snapshot_at` | date-time | ✓ | ISO-8601 |
| `active_rfcs` | integer | ✓ | 当前活跃 RFC 数 |
| `merged_rfcs_30d` | integer | ✓ | 最近 30 天合并 RFC 数 |
| `spoke_repos_count` | integer | ✓ | 已注册 Spoke 仓库数 |

## 演进策略

- **v1 (当前)**: 不可变。Schema 文件一旦发布不再修改。
- **v2 (未来)**: 需要破坏性变更时:
  1. 创建 `_lib/schemas/<name>_schema_v2.json`
  2. 添加 `version: {"const": 2}`
  3. v1 文件保留 6 个月过渡期
  4. `rdd-doctor --category state` 在过渡期后警告 v1 文件

## 验证

- `tests/unit/test_cross_repo_schemas.py` 覆盖 6 schema × 3 验证(valid / invalid-field / missing-field)
- `rdd-doctor --category state` 检测 state 文件与 schema 的对齐

## 相关

- ADR-0016: Arch Artifact Discovery Contract
- ADR-0030: Hub-and-Spoke Federation Architecture
- ADR-0031: Human-in-Loop for Cross-Repo RFCs
```

- [x] **Step 4: 运行测试,确认 7/7 PASS**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py -v -k "test_docs"`
Expected: 7 PASS

- [x] **Step 5: 推迟 commit**

---

### Task 6: 验证 openspec validate + rdd-doctor 端到端

**Files:** 无新增,仅验证

- [x] **Step 1: 写失败测试(若 openspec CLI 不可用,skip)**

在 `tests/unit/test_cross_repo_schemas.py` 追加:

```python
import subprocess


def test_openspec_validate_change():
    """openspec validate must accept the add-cross-repo-state-schemas change."""
    result = subprocess.run(
        ["openspec", "validate", "add-cross-repo-state-schemas"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    assert result.returncode == 0, f"openspec validate failed: {result.stderr}"
```

- [x] **Step 2: 运行测试**

Run: `python3 -m pytest tests/unit/test_cross_repo_schemas.py::test_openspec_validate_change -v`
Expected: PASS(openspec validate 通过)

- [x] **Step 3: 手动 rdd-doctor state 检查**

Run: `python3 -m skills.rdd_doctor.scripts.doctor --category state --quiet`
Expected: 输出 "0 critical, 0 warnings" 或类似(因为 `.rddf/state/` 没有对应 state 文件,但 schema 都已声明)

- [x] **Step 4: 推迟 commit**

---

### Task 7: 全量回归门(零新增失败)

**Files:** 无新增

- [x] **Step 1: 运行 pytest unit 全套**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 1668+ passed, 1 skipped(从 W1-1 baseline + 我们新增的 ~20+ tests)

- [x] **Step 2: 运行 bats integration test_state_schema_check**

Run: `bats tests/integration/test_*.bats 2>&1 | tail -10`
Expected: 无新增失败

- [x] **Step 3: 推迟 commit**

---

## Verification Checklist (Acceptance)

- [x] 6 schema 文件存在且均含 `version` (const:1) + `$id` + Draft-7
- [x] `tests/unit/test_cross_repo_schemas.py` 18+ 测试全过
- [x] `rdd-doctor --category state` 检测 6 个新 schema(state 文件缺失时 WARNING 而非 CRITICAL)
- [x] `docs/schemas/cross-repo-schemas.md` 含字段语义表
- [x] `openspec validate add-cross-repo-state-schemas` exit 0
- [x] pytest unit 全套无回归(新增 ~20 测试通过,既有 1668 不变)

---

## Self-Review Checklist

1. **Spec 覆盖**:
   - proposal.md §What Changes (4 项) → T1 (diff review), T2 ($id 验证), T3 (18 测试), T4 (rdd-doctor), T5 (docs) ✓
   - design.md §Decisions (5 项) → 全部通过 schema 现有 + 增量修改 ✓
   - tasks.md T1.1-T1.6 + T2.1-T2.2 → T1-T7 全覆盖 ✓

2. **占位符扫描**: 无 "TBD" / "TODO" / "implement later"

3. **类型一致性**: 6 schema 的 `version` 都是 const:1,在 `properties` 和 `required` 中均存在。rdd-doctor 映射键名与 proposal.md 命名一致(`cross-repo-pending` 等)。