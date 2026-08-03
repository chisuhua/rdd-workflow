# add-rddf-session-workflow-group 实施计划

> **P2 workflow**: 跨多次 guide-ship 调用关联同一批次 (workflow_group)。
>
> **TDD 5 步纪律**。
>
> **依据**: `improvements/add-rddf-session-workflow-group.md` + `openspec/changes/add-rddf-session-workflow-group/{proposal,design,tasks}.md`
>
> **预期修改文件**:
> 1. `skills/rddf-session/scripts/rddf_session_hooks.sh` (entry hook 支持 RDDF_WORKFLOW_GROUP)
> 2. `tests/integration/test_rddf_session_workflow_group.bats` (新增)
> 3. `tests/unit/test_rddf_session_workflow_group.py` (新增)
>
> **强约束**:
> - Schema v2 已在 `add-rddf-session-sub-phase-heartbeat` 中添加 `workflow_group` 字段 ✅
> - `RDDF_WORKFLOW_GROUP` 未设置时, 首次 entry 自动生成 UUID v4 并 export (后续 hooks 继承)
> - 设置时, 跨多次 entry 共享同一 group
> - **不修改** entry hook 的 kind / owner 解析逻辑

---

### Task 1: Hook entry 接受 RDDF_WORKFLOW_GROUP

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh`
- Create: `tests/integration/test_rddf_session_workflow_group.bats`

- [ ] **Step 1: Write the failing test**

```bats
#!/usr/bin/env bats
# tests/integration/test_rddf_session_workflow_group.bats

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    export OPENCODE_SESSION_ID="test-wg-$(date +%s%N)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "workflow-group: explicit env var shared across entries" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    export RDDF_WORKFLOW_GROUP="batch-2026-08-02"

    # First entry
    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        export RDDF_WORKFLOW_GROUP='batch-2026-08-02'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all
    " 2>/dev/null

    # Second entry (different kind)
    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        export RDDF_WORKFLOW_GROUP='batch-2026-08-02'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all-2
    " 2>/dev/null

    # Both sessions share workflow_group
    count=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
matching = [s for s in data['sessions'] if s.get('workflow_group') == 'batch-2026-08-02']
print(len(matching))
")
    [ "$count" -eq 2 ] || {
        echo "FAIL: Expected 2 sessions with workflow_group='batch-2026-08-02', got $count"
        return 1
    }
}

@test "workflow-group: auto-generates UUID when env var unset" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"
    unset RDDF_WORKFLOW_GROUP

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        unset RDDF_WORKFLOW_GROUP
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all
    " 2>/dev/null

    wg=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(data['sessions'][0].get('workflow_group', ''))
")
    # UUID v4 format: 8-4-4-4-12 hex chars
    if [[ ! "$wg" =~ ^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[a-f0-9]{4}-[a-f0-9]{12}$ ]]; then
        echo "FAIL: Expected UUID v4, got '$wg'"
        return 1
    fi
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_workflow_group.bats`
Expected: 2 tests FAIL (entry hook doesn't set workflow_group)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/scripts/rddf_session_hooks.sh`

修改 `rddf_session_hook_entry`:
1. 在 `_rddf_resolve_owner` 之前, 添加 RDDF_WORKFLOW_GROUP 处理 (auto-generate if unset):

```bash
# Auto-generate workflow_group if not set
if [ -z "${RDDF_WORKFLOW_GROUP:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    RDDF_WORKFLOW_GROUP=$(python3 -c "import uuid; print(uuid.uuid4())")
  else
    RDDF_WORKFLOW_GROUP="auto-$(date +%s%N)"
  fi
  export RDDF_WORKFLOW_GROUP
fi
```

2. 在 heredoc `KIND="$kind" \\` 之后添加:
```bash
  WORKFLOW_GROUP="$RDDF_WORKFLOW_GROUP" \
```

3. 在 Python heredoc 内 `coord.create_session(...)` 调用之前, 修改 session_data 写入:
```python
        workflow_group = os.environ.get("WORKFLOW_GROUP", "").strip() or None
        sid = coord.create_session(
            kind=kind,
            owner_opencode_session_id=opencode_sid,
            goal={"intent": intent, "subject": subject, "expected_outcome": expected_outcome},
            parent_session_id=parent_id,
            context_pointer=context_pointer,
        )
        # Inject workflow_group
        if workflow_group:
            data = coord._store.read_unlocked()
            for s in data.get("sessions", []):
                if s.get("session_id") == sid:
                    s["workflow_group"] = workflow_group
                    break
            coord._store.atomic_write(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rddf_session_workflow_group.bats`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session_hooks.sh \
        tests/integration/test_rddf_session_workflow_group.bats
git commit -m "feat(rddf-session): entry hook auto-generates + records workflow_group"
```

---

### Task 2: Spec + 验证

- [ ] **Step 1: 添加 spec**

创建 `openspec/changes/add-rddf-session-workflow-group/specs/rddf-session-workflow-group/spec.md`:

```markdown
# rddf-session-workflow-group — Capability Spec

## ADDED Requirements

### Requirement: workflow_group Links Multiple Sessions

The rddf-session entry hook SHALL record a `workflow_group` identifier on each session, derived from `RDDF_WORKFLOW_GROUP` env var (auto-generated UUID v4 when unset). Two entries sharing the same group form one logical workflow batch.

#### Scenario: Explicit env var shared

- GIVEN `RDDF_WORKFLOW_GROUP=batch-2026-08-02` set across two `rddf_session_hook_entry` calls
- WHEN both entries complete
- THEN both sessions have `workflow_group="batch-2026-08-02"`

#### Scenario: Auto-generated UUID v4

- GIVEN `RDDF_WORKFLOW_GROUP` is unset on first entry
- WHEN entry completes
- THEN the session has `workflow_group` matching UUID v4 format (8-4-4-4-12 hex chars, version digit = 4)
```

- [ ] **Step 2: 验证 + 提交**

```bash
cd "$PROJECT_ROOT"
sed -i 's/- \[ \]/- [x]/g' openspec/changes/add-rddf-session-workflow-group/tasks.md
openspec validate add-rddf-session-workflow-group --strict
bats tests/integration/test_rddf_session_workflow_group.bats
bats tests/integration/test_rddf_session_hooks_extraction.bats  # 回归
git add openspec/changes/add-rddf-session-workflow-group/specs/ \
        openspec/changes/add-rddf-session-workflow-group/tasks.md
git commit -m "docs(rddf-session): workflow_group spec + mark tasks complete"
```

---

## 自检清单

1. Spec 覆盖: workflow_group ✅ | auto UUID ✅ | shared ✅
2. 占位符扫描: 无
3. 类型一致性: workflow_group string | null

## 执行交接

按 Task 1 → 2 顺序直接执行。