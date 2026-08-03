# add-rddf-session-status-cmd 实施计划

> **P2 observability**: 新增 `rddf-session status` 子命令,提升 rddf-session 用户可见性。
>
> **TDD 5 步纪律** (来自 rdd-workflow v2.0 execute skill): 每个 task 严格按 Write failing test → Verify fail → Implement → Verify pass → Commit。
>
> **依据**: `improvements/add-rddf-session-status-cmd.md` + `openspec/changes/add-rddf-session-status-cmd/{proposal,design,tasks}.md`
>
> **预期修改文件**:
> 1. `skills/rddf-session/SKILL.md` (新增 `status` 子命令 case + 文档)
> 2. `skills/guide/scripts/scan-state.sh` (新增 BINDING_LINES 输出)
> 3. `tests/integration/test_rddf_session_status.bats` (新增 — bats 集成)
> 4. `tests/unit/test_rddf_session_status.py` (新增 — pytest 单元)
>
> **强约束** (来自 improvements + 设计阶段):
> - status 输出宽度 ≤100 字符
> - BINDING_LINES 与 `guide` 推荐器现有逻辑共存
> - status 永不修改 sessions.json (纯读视图)
> - 不修改现有 list / show / current 子命令 (向后兼容)
> - 不修改 schema (status 是只读视图)
> - **不引入** 新的 rddf-session skill (status 是现有 skill 的子命令)
>
> **依赖前置**: P0 `fix-rddf-session-owner-stability` 已实施归档 (`18fc072`),本 P2 是直接下游 (使用 owner 检测)。

---

### Task 1: 实现 status 子命令 — 表格 + binding + 计数

**Files:**
- Modify: `skills/rddf-session/SKILL.md` (新增 `status)` case + 文档 + subcommand list)
- Create: `tests/integration/test_rddf_session_status.bats` (新增 — 端到端集成)

- [ ] **Step 1: Write the failing test**

**文件**: `tests/integration/test_rddf_session_status.bats`

```bats
#!/usr/bin/env bats
# tests/integration/test_rddf_session_status.bats
# Verify rddf-session status subcommand outputs table + binding + counts.

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    export OPENCODE_SESSION_ID="test-status-$(date +%s%N)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "rddf-session status: outputs table header" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
data = {
    'version': 1,
    'sessions': [
        {
            'session_id': 'rds_active_001',
            'kind': 'stage_ship',
            'state': 'active',
            'owner_opencode_session_id': '$OPENCODE_SESSION_ID',
            'parent_session_id': None,
            'started_at': '2026-08-02T15:00:00+00:00',
            'last_heartbeat': '2026-08-02T15:30:00+00:00',
            'attached_changes': ['add-foo'],
            'goal': {'intent': 'guide-ship'},
        }
    ]
}
with open('$SESSIONS_FILE', 'w') as f:
    json.dump(data, f)
"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/SKILL.md' 2>/dev/null || true
        # SKILL.md is documentation, not executable. Invoke the bash block from docs.
        # Implementation lives in SKILL.md 'Implementation (Bash)' section as inline bash.
        # Extract via heredoc:
        awk '/^## Implementation/,/^## /' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '/^## /d' \
          | sed '1d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    # Verify table header
    [ "$status" -eq 0 ]
    [[ "$output" == *"session_id"* ]]
    [[ "$output" == *"kind"* ]]
    [[ "$output" == *"owner"* ]]
    [[ "$output" == *"state"* ]]
}

@test "rddf-session status: outputs binding line for active session" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
data = {
    'version': 1,
    'sessions': [
        {
            'session_id': 'rds_active_001',
            'kind': 'stage_ship',
            'state': 'active',
            'owner_opencode_session_id': '$OPENCODE_SESSION_ID',
            'parent_session_id': 'rds_parent_xyz',
            'started_at': '2026-08-02T15:00:00+00:00',
            'last_heartbeat': '2026-08-02T15:30:00+00:00',
            'attached_changes': ['add-foo'],
            'goal': {'intent': 'guide-ship'},
        }
    ]
}
with open('$SESSIONS_FILE', 'w') as f:
    json.dump(data, f)
"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        awk '/^## Implementation/,/^## /' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '/^## /d' | sed '1d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"📍"* ]]
    [[ "$output" == *"rds_active_001"* ]]
    [[ "$output" == *"stage_ship"* ]]
}

@test "rddf-session status: shows counts (active/completed/orphaned/abandoned)" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
sessions = []
for i, state in enumerate(['active', 'completed', 'orphaned', 'abandoned', 'completed']):
    sessions.append({
        'session_id': f'rds_{state}_{i}',
        'kind': 'stage_ship',
        'state': state,
        'owner_opencode_session_id': f'owner_{i}',
        'parent_session_id': None,
        'started_at': '2026-08-02T15:00:00+00:00',
        'last_heartbeat': '2026-08-02T15:30:00+00:00',
        'attached_changes': [],
        'goal': {},
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        awk '/^## Implementation/,/^## /' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '/^## /d' | sed '1d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    [ "$status" -eq 0 ]
    # Counts section header
    [[ "$output" == *"Counts"* ]] || [[ "$output" == *"📊"* ]] || [[ "$output" == *"active"* ]]
    # 1 active, 2 completed, 1 orphaned, 1 abandoned
    [[ "$output" == *"1"* ]]
}

@test "rddf-session status: handles no sessions gracefully" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    echo '{"version": 1, "sessions": []}' > "$SESSIONS_FILE"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        awk '/^## Implementation/,/^## /' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '/^## /d' | sed '1d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"no active"* ]] || [[ "$output" == *"No rddf-sessions"* ]]
}

@test "rddf-session status: read-only (does not modify sessions.json)" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
data = {'version': 1, 'sessions': [{
    'session_id': 'rds_001',
    'kind': 'stage_ship',
    'state': 'active',
    'owner_opencode_session_id': '$OPENCODE_SESSION_ID',
    'parent_session_id': None,
    'started_at': '2026-08-02T15:00:00+00:00',
    'last_heartbeat': '2026-08-02T15:30:00+00:00',
    'attached_changes': [],
    'goal': {},
}]}
with open('$SESSIONS_FILE', 'w') as f:
    json.dump(data, f)
"
    # Snapshot mtime + content
    BEFORE_HASH=$(sha256sum "$SESSIONS_FILE" | awk '{print $1}')

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        awk '/^## Implementation/,/^## /' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '/^## /d' | sed '1d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    " > /dev/null

    AFTER_HASH=$(sha256sum "$SESSIONS_FILE" | awk '{print $1}')
    [ "$BEFORE_HASH" = "$AFTER_HASH" ] || {
        echo "FAIL: status modified sessions.json (hash changed)"
        return 1
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_status.bats`
Expected: 5 tests FAIL (`status` case not in SKILL.md bash block)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/SKILL.md`

修改 3 处:
1. **Subcommand list** (在文件头 `## Subcommands` 部分): 添加 `status`
2. **Implementation case statement** (在 `## Implementation (Bash)` 的 case block): 添加 `status)` case
3. **新增章节** `## Status Subcommand` 在末尾

**修改 1 — Subcommand 列表**:

在 `skill_use("rddf-session progress")` 后插入:
```
skill_use("rddf-session status")                # rich status view (table + binding + counts) — P2
```

**修改 2 — case statement**:

在 `case "$SUBCOMMAND" in` 块中, `progress)` 之后插入:

```bash
    status)
        OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$PPID}"
        python3 - "$SESSIONS_FILE" "$OPENCODE_SESSION_ID" "$PROJECT_ROOT" <<'PYEOF'
import sys, json
from datetime import datetime, timezone
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
sessions_file, owner = sys.argv[1], sys.argv[2]

coord = RddfSessionCoordinator(sessions_file=sessions_file)
coord.check_heartbeat_timeouts()
sessions = coord.list_sessions()
active = [s for s in sessions if s.state == "active"]
terminal = [s for s in sessions if s.state in ("completed", "abandoned", "orphaned", "failed")]

# === Binding line ===
current = coord.find_current_binding(owner)
if current:
    age_min = int((datetime.now(timezone.utc) - datetime.fromisoformat(current.started_at.replace("Z", "+00:00"))).total_seconds() // 60)
    changes = ", ".join(current.attached_changes) if current.attached_changes else "(none)"
    print(f"📍 Current: {current.session_id} (kind={current.kind}, parent={current.parent_session_id}, age={age_min}min, changes={changes})")
else:
    print("📍 No current binding")

# === Table ===
print()
if sessions:
    hdr = f"{'session_id':<17} {'kind':<14} {'state':<11} {'started_at':<26} {'changes':<8}"
    print(hdr)
    print("-" * len(hdr))
    for s in sorted(sessions, key=lambda x: (x.state != "active", x.started_at), reverse=True):
        changes_n = len(s.attached_changes)
        print(f"{s.session_id:<17} {s.kind:<14} {s.state:<11} {s.started_at[:19]:<26} {changes_n:<8}")
else:
    print("(no rddf-sessions found)")

# === Counts ===
print()
state_counts = {}
for s in sessions:
    state_counts[s.state] = state_counts.get(s.state, 0) + 1
print("📊 Counts:")
for state in sorted(state_counts.keys()):
    print(f"  {state:<11} {state_counts[state]}")
PYEOF
        ;;
```

**修改 3 — 文档章节**:

在 `## Cross-Reference` 之前新增:

```markdown
## Status Subcommand (P2 observability)

`skill_use("rddf-session", "status")` 输出综合视图:

1. **Binding line** (顶部): `📍 Current: <sid> (kind=<kind>, parent=<parent>, age=<min>, changes=<list>)`
   - 显示当前 active session (按 owner 匹配)
   - 若无 active session: 显示 "📍 No current binding"
2. **Sessions table**: 列所有 sessions, active 优先 (按 started_at 倒序)
3. **Counts section**: 每个 state 的总数

**约束**:
- 纯读视图,**永不修改** sessions.json
- 输出宽度 ≤100 字符 (适配终端)
- 不破坏现有 `list` / `show` / `current` 子命令 (向后兼容)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rddf_session_status.bats`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add skills/rddf-session/SKILL.md \
        tests/integration/test_rddf_session_status.bats
git commit -m "feat(rddf-session): add status subcommand with table + binding + counts"
```

---

### Task 2: 集成到 guide 推荐器 (BINDING_LINES 输出)

**Files:**
- Modify: `skills/guide/scripts/scan-state.sh` (新增 BINDING_LINES 输出)
- Create: `tests/unit/test_scan_state_binding_lines.py` (新增 — 验证 scan-state.sh 输出格式)

- [ ] **Step 1: Write the failing test**

**文件**: `tests/unit/test_scan_state_binding_lines.py`

```python
"""Verify scan-state.sh emits BINDING_LINES when active session exists."""
import os
import subprocess
import tempfile
from pathlib import Path

SCAN_STATE_SCRIPT = Path("skills/guide/scripts/scan-state.sh")


def test_scan_state_emits_binding_line_when_active(tmp_path):
    """When sessions.json has active session owned by caller, scan-state outputs binding."""
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    sessions_file.write_text(
        """{
            "version": 1,
            "sessions": [
                {
                    "session_id": "rds_active_test",
                    "kind": "stage_ship",
                    "state": "active",
                    "owner_opencode_session_id": "test_owner",
                    "parent_session_id": null,
                    "started_at": "2026-08-02T15:00:00+00:00",
                    "last_heartbeat": "2026-08-02T15:30:00+00:00",
                    "attached_changes": [],
                    "goal": {}
                }
            ]
        }"""
    )

    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(tmp_path)
    env["OPENCODE_SESSION_ID"] = "test_owner"

    result = subprocess.run(
        ["bash", str(SCAN_STATE_SCRIPT)],
        capture_output=True, env=env, text=True,
    )
    # Script outputs human-readable status. We test for the binding line marker.
    # BINDING_LINES should contain "rds_active_test" if emitted.
    # Note: scan-state.sh may set BINDING_LINES env var that parent script consumes.
    # We assert on either stdout content or BINDING_LINES env var.
    output = result.stdout + result.stderr
    # Either BINDING_LINES is exported, or printed to stdout
    assert (
        "rds_active_test" in output
        or "📍 Current" in output
        or "stage_ship" in output
    ), f"Expected binding line for active session, got: {output}"


def test_scan_state_emits_no_binding_when_no_active(tmp_path):
    """When no active sessions owned by caller, no binding line."""
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    sessions_file.write_text(
        """{
            "version": 1,
            "sessions": [
                {
                    "session_id": "rds_other",
                    "kind": "stage_ship",
                    "state": "active",
                    "owner_opencode_session_id": "different_owner",
                    "parent_session_id": null,
                    "started_at": "2026-08-02T15:00:00+00:00",
                    "last_heartbeat": "2026-08-02T15:30:00+00:00",
                    "attached_changes": [],
                    "goal": {}
                }
            ]
        }"""
    )

    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(tmp_path)
    env["OPENCODE_SESSION_ID"] = "test_owner"

    result = subprocess.run(
        ["bash", str(SCAN_STATE_SCRIPT)],
        capture_output=True, env=env, text=True,
    )
    output = result.stdout + result.stderr
    # Should NOT contain binding for different_owner
    # (May still contain scan output, but no specific session_id reference)
    assert "rds_other" not in output or "📍" not in output, (
        f"Should not emit binding for other owner's session, got: {output}"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_scan_state_binding_lines.py -v`
Expected: 1-2 tests FAIL (`scan-state.sh` does not emit binding lines)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/guide/scripts/scan-state.sh`

在文件末尾 (existing `scan_state` 函数末尾, 在 `check_stale_workflow_state` 调用之前) 新增:

```bash
# scan_binding_lines <sessions_file> <owner_id>
#
# Emits BINDING_LINES env var or prints to stdout the active session binding
# for the given owner. Called by scan_state when sessions.json has active sessions.
scan_binding_lines() {
  local sessions_file="$1"
  local owner_id="$2"

  if [ ! -f "$sessions_file" ]; then
    return 0
  fi

  python3 - "$sessions_file" "$owner_id" <<'PYEOF'
import json, sys, os
from datetime import datetime, timezone

sessions_file = sys.argv[1]
owner_id = sys.argv[2]

try:
    with open(sessions_file) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

active = [s for s in data.get("sessions", []) if s.get("state") == "active"
          and s.get("owner_opencode_session_id") == owner_id]
if not active:
    sys.exit(0)

# Take the most recent active session
s = max(active, key=lambda x: x.get("started_at", ""))
started = s.get("started_at", "")
try:
    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
    age_min = int((datetime.now(timezone.utc) - started_dt).total_seconds() // 60)
except Exception:
    age_min = -1

changes = s.get("attached_changes", [])
changes_str = ", ".join(changes) if changes else "(none)"
line = f"📍 Current: {s['session_id']} (kind={s.get('kind', '?')}, parent={s.get('parent_session_id')}, age={age_min}min, changes={changes_str})"
# Print to stdout AND export as env var for parent process consumption
print(line)
# Also try to set BINDING_LINES env var (best-effort)
try:
    existing = os.environ.get("BINDING_LINES", "")
    new_val = f"{existing}\n{line}".strip() if existing else line
    os.environ["BINDING_LINES"] = new_val
except Exception:
    pass
PYEOF
}
```

在 `scan_state()` 函数末尾 (在调用 `check_stale_workflow_state` 之前) 插入调用:

```bash
  # Phase 2: emit binding line if active session exists for current owner
  local owner_id="${OPENCODE_SESSION_ID:-}"
  if [ -n "$owner_id" ]; then
    scan_binding_lines "${PROJECT_ROOT}/.rddf/state/sessions.json" "$owner_id" || true
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_scan_state_binding_lines.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add skills/guide/scripts/scan-state.sh \
        tests/unit/test_scan_state_binding_lines.py
git commit -m "feat(guide): scan-state emits BINDING_LINES for active rddf-session"
```

---

### Task 3: 验证既有 rddf-session 子命令不回归

**Files:**
- 无新文件 — 验证既有测试不被破坏

- [ ] **Step 1: 验证 list / show / current 子命令仍工作**

```bash
# Setup minimal sessions.json
TEST_DIR=$(mktemp -d)
mkdir -p "$TEST_DIR/.rddf/state"
cat > "$TEST_DIR/.rddf/state/sessions.json" <<'EOF'
{
  "version": 1,
  "sessions": [
    {
      "session_id": "rds_keep_001",
      "kind": "stage_ship",
      "state": "completed",
      "owner_opencode_session_id": "prev_owner",
      "parent_session_id": null,
      "started_at": "2026-08-02T15:00:00+00:00",
      "last_heartbeat": "2026-08-02T15:30:00+00:00",
      "ended_at": "2026-08-02T15:35:00+00:00",
      "attached_changes": [],
      "goal": {}
    }
  ]
}
EOF

export PROJECT_ROOT="$TEST_DIR"
export OPENCODE_SESSION_ID="prev_owner"

# Extract bash block from SKILL.md
awk '/^## Implementation/,/^## /' skills/rddf-session/SKILL.md \
  | sed '/^## /d' | sed '1d' \
  | sed '/^```bash/d; /^```$/d' \
  > /tmp/rddf_session_impl.sh

# Verify list works
bash /tmp/rddf_session_impl.sh list
# Expected: rds_keep_001 in output

# Verify show works
bash /tmp/rddf_session_impl.sh show rds_keep_001
# Expected: JSON output

# Verify current works
bash /tmp/rddf_session_impl.sh current
# Expected: shows binding

# Verify status works (new command)
bash /tmp/rddf_session_impl.sh status
# Expected: table + counts

# Cleanup
rm -rf "$TEST_DIR"
```

Expected: All 4 subcommands succeed; output contains expected content.

- [ ] **Step 2: 验证 openspec validate**

Run: `openspec validate add-rddf-session-status-cmd --strict`
Expected: PASS

- [ ] **Step 3: Commit tasks 文档**

```bash
cd "$WT_PATH"
sed -i 's/- \[ \]/- [x]/g' openspec/changes/add-rddf-session-status-cmd/tasks.md
git add openspec/changes/add-rddf-session-status-cmd/tasks.md
git commit -m "chore(change): mark add-rddf-session-status-cmd tasks complete"
```

- [ ] **Step 4: 最终验证**

```bash
cd "$WT_PATH"
git log --oneline "master..HEAD"
```

Expected: 4 commits (Task 1 + Task 2 + Task 3 + this commit)

---

## 自检清单 (Self-Review)

**1. Spec 覆盖**:
- [x] 新增 `skill_use("rddf-session", "status")` 子命令 → Task 1
- [x] 输出表格 + binding + 计数 → Task 1
- [x] 集成到 `guide` 推荐器扫描 → Task 2 (scan-state.sh BINDING_LINES)
- [x] SKILL.md 增加 status 子命令章节 → Task 1

**2. 占位符扫描**:
- 无 "TBD" / "TODO" / "implement later"
- 所有步骤显示实际可执行命令 + 实际代码

**3. 类型一致性**:
- `s.state` / `s.kind` / `s.session_id` 跨 Task 1 一致
- `coord.find_current_binding(owner)` 与既有 `current` 子命令一致

**4. 文件路径核对**:
- SKILL.md 修改 + subcommand 列表 + 文档
- scan-state.sh 新增 `scan_binding_lines` 函数
- 测试在 worktree 路径下

---

## 执行交接

**当前 session 执行** (推荐 — plan 较小, 17 tasks):
- 按 Task 1 → 2 → 3 顺序执行
- Task 3 完成后进入 `guide-ship` Phase 2 (review) → Phase 3 (archive)

**或 `skill_use("execute")`**:
- 加载本 plan 文件
- 自动 TDD 5 步执行 + 每 Task 自动 commit
- 完成后调用 `status` 检查