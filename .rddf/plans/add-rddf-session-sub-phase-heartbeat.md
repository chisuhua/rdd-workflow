# add-rddf-session-sub-phase-heartbeat 实施计划

> **P1 observability**: 为 rddf-session 跟踪 sub_phase (guide-ship 内部 6 子阶段)。
>
> **TDD 5 步纪律** (来自 rdd-workflow v2.0 execute skill)。
>
> **依据**: `improvements/add-rddf-session-sub-phase-heartbeat.md` + `openspec/changes/add-rddf-session-sub-phase-heartbeat/{proposal,design,tasks}.md`
>
> **预期修改文件**:
> 1. `skills/_lib/schemas/sessions_schema.json` (v1 → v2, 添加 `sub_phase` + `workflow_group` optional 字段)
> 2. `skills/rddf-session/scripts/rddf_session_hooks.sh` (entry/heartbeat 调用 sub_phase)
> 3. `tests/unit/test_rddf_session_sub_phase.py` (新增 — 单元测试)
> 4. `tests/integration/test_rddf_session_sub_phase.bats` (新增 — 集成测试)
>
> **强约束**:
> - **必须与 `add-rddf-session-workflow-group` 合并为单一 schema v1→v2 bump** (per proposal: 避免 v1.5 中间态)
> - **依赖 P0 `fix-rddf-session-owner-stability`** 已实施 ✅
> - 不修改 schema 现有必填字段 (向后兼容)
> - 复用 `RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS` 阈值, 不新增 env var

---

### Task 1: Schema v1 → v2 (添加 sub_phase + workflow_group optional 字段)

**Files:**
- Modify: `skills/_lib/schemas/sessions_schema.json` (v1 → v2 + 新字段)
- Create: `tests/unit/test_session_schema_v2.py` (schema bump 兼容性测试)

- [ ] **Step 1: Write the failing test**

```python
"""Verify sessions_schema.json v2 accepts optional sub_phase + workflow_group."""
import json
from pathlib import Path
import jsonschema

SCHEMA = json.loads(Path("skills/_lib/schemas/sessions_schema.json").read_text())


def test_schema_version_is_2():
    """After this change, schema version is 2."""
    assert SCHEMA["properties"]["version"]["const"] == 2


def test_sub_phase_field_optional():
    """Session has optional sub_phase field (string or null)."""
    session_props = SCHEMA["$defs"]["Session"]["properties"]
    assert "sub_phase" in session_props
    assert session_props["sub_phase"]["type"] == "string"
    assert "null" in session_props["sub_phase"]["type"] or session_props["sub_phase"].get("nullable", False)


def test_workflow_group_field_optional():
    """Session has optional workflow_group field (string or null)."""
    session_props = SCHEMA["$defs"]["Session"]["properties"]
    assert "workflow_group" in session_props


def test_v1_sessions_still_validate():
    """v1 sessions (no sub_phase) still validate against v2 schema."""
    v1_session = {
        "session_id": "rds_aaaabbbbcccc",
        "kind": "stage_ship",
        "owner_opencode_session_id": "owner1",
        "state": "active",
        "started_at": "2026-08-02T15:00:00+00:00",
        "last_heartbeat": "2026-08-02T15:30:00+00:00",
    }
    jsonschema.validate(instance={"version": 2, "sessions": [v1_session]}, schema=SCHEMA)


def test_v2_sessions_with_sub_phase_validate():
    """v2 sessions with sub_phase validate correctly."""
    v2_session = {
        "session_id": "rds_ddddddddeeee",
        "kind": "stage_ship",
        "owner_opencode_session_id": "owner1",
        "state": "active",
        "started_at": "2026-08-02T15:00:00+00:00",
        "last_heartbeat": "2026-08-02T15:30:00+00:00",
        "sub_phase": "phase_3_archive_demo",
        "workflow_group": "rddf-session-batch",
    }
    jsonschema.validate(instance={"version": 2, "sessions": [v2_session]}, schema=SCHEMA)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_session_schema_v2.py -v`
Expected: FAIL (version=1, no sub_phase/workflow_group)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/_lib/schemas/sessions_schema.json`

修改 schema:
```diff
-    "version": {
-      "type": "integer",
-      "const": 1,
+    "version": {
+      "type": "integer",
+      "const": 2,
       "description": "Schema version. Bumped on breaking changes."
     },
```

并在 `Session.$defs.properties` 中追加:
```json
        "sub_phase": {
          "type": ["string", "null"],
          "description": "Optional sub-phase marker (e.g. 'phase_3_archive_demo'). Updated by hooks during long-running operations. P1: add-rddf-session-sub-phase-heartbeat."
        },
        "workflow_group": {
          "type": ["string", "null"],
          "description": "Optional workflow group identifier linking related rddf-sessions. P2: add-rddf-session-workflow-group."
        }
```

将 `Session.additionalProperties` 保持 `false`(允许新 optional 字段,但仍禁止未知字段)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_session_schema_v2.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add skills/_lib/schemas/sessions_schema.json \
        tests/unit/test_session_schema_v2.py
git commit -m "feat(sessions): schema v2 adds sub_phase + workflow_group optional fields"
```

---

### Task 2: Hooks 调用时记录 sub_phase

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` (rddf_session_hook_heartbeat + rddf_session_hook_entry 支持 sub_phase env var)
- Create: `tests/integration/test_rddf_session_sub_phase.bats` (端到端)

- [ ] **Step 1: Write the failing test**

**文件**: `tests/integration/test_rddf_session_sub_phase.bats`

```bats
#!/usr/bin/env bats
# tests/integration/test_rddf_session_sub_phase.bats
# Verify rddf_session_hook_heartbeat records sub_phase in sessions.json.

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    export OPENCODE_SESSION_ID="test-sp-$(date +%s%N)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "sub-phase: heartbeat records sub_phase from env var" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        export RDDF_SUB_PHASE='phase_3_archive_demo'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_heartbeat stage_ship demo
    " 2>/dev/null

    # Verify sessions.json has sub_phase
    sub_phase=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
s = data['sessions'][0]
print(s.get('sub_phase', ''))
")
    [ "$sub_phase" = "phase_3_archive_demo" ] || {
        echo "FAIL: Expected sub_phase='phase_3_archive_demo', got '$sub_phase'"
        return 1
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_sub_phase.bats`
Expected: FAIL (hooks don't record sub_phase)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/scripts/rddf_session_hooks.sh`

修改 `rddf_session_hook_heartbeat` 函数,在 `KIND="$kind" \\` 之后追加:
```bash
  CHANGE_NAME="$change_name" \
  RDDF_SUB_PHASE="${RDDF_SUB_PHASE:-}" \
```

并在 heredoc 内 `coord.refresh_heartbeat(sid)` 之前追加 Python 端 sub_phase 读取:
```python
        if change_name:
            coord.detach_change(sid, change_name)
        sub_phase = os.environ.get("RDDF_SUB_PHASE", "").strip() or None
        if sub_phase:
            # Re-read session, update sub_phase, atomic write
            data = coord._store.read_unlocked()
            for s in data.get("sessions", []):
                if s.get("session_id") == sid:
                    s["sub_phase"] = sub_phase
                    s["last_heartbeat"] = _now()
                    break
            coord._store.atomic_write(data)
        else:
            coord.refresh_heartbeat(sid)
```

注: `_now` 需要从 `rddf_session_pkg._types` import。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rddf_session_sub_phase.bats`
Expected: 1 test PASS

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add skills/rddf-session/scripts/rddf_session_hooks.sh \
        tests/integration/test_rddf_session_sub_phase.bats
git commit -m "feat(rddf-session): heartbeat records RDDF_SUB_PHASE env var"
```

---

### Task 3: 文档 + 最终验证

- [ ] **Step 1: 添加 openspec spec (满足 validate)**

创建 `openspec/changes/add-rddf-session-sub-phase-heartbeat/specs/rddf-session-sub-phase/spec.md` 含 ADDED Requirement。

- [ ] **Step 2: 验证**

```bash
cd "$WT_PATH"
pytest tests/unit/test_session_schema_v2.py tests/unit/test_rddf_session.py -v
bats tests/integration/test_rddf_session_sub_phase.bats
bats tests/integration/test_rddf_session_hooks_extraction.bats  # 回归
openspec validate add-rddf-session-sub-phase-heartbeat --strict
```

- [ ] **Step 3: 提交**

```bash
git add openspec/changes/add-rddf-session-sub-phase-heartbeat/specs/
git commit -m "docs(rddf-session): document sub_phase + add spec"
```

---

## 自检清单

1. Spec 覆盖: sub_phase ✅ | schema v2 ✅ | backward compat ✅
2. 占位符扫描: 无
3. 类型一致性: sub_phase string | null, workflow_group string | null

## 执行交接

按 Task 1 → 2 → 3 顺序直接执行。