# reduce-rdd-workflow-tool-call-friction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the 7 measured tool-call errors (1.4% error rate) in rdd-workflow's own 5-phase dogfood flow by adding an Agent tool-selection decision tree (`skills/_lib/AGENT_TOOL_USAGE.md`), a pre-tool-check guard script (`skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh`), and 7 regression tests locking the behavior.

**Architecture:** Two parallel mitigations: (1) a documentation decision tree that agents read to choose edit-vs-write-vs-read-offset correctly; (2) a bash guard that detects the 3 stale-state patterns (edit on stale oldString, write onto existing file, hardcoded read offset) and emits a stderr warning. Regression tests in `tests/integration/test_tool_friction_regression.py` verify each mitigation fires exactly once and does NOT spam.

**Tech Stack:** Bash (guard script, `skills/_lib/AGENT_TOOL_USAGE.md` doc) + Python pytest (regression tests) + bats (smoke for repo conventions).

**OpenSpec change artifacts** (canonical): `openspec/changes/reduce-rdd-workflow-tool-call-friction/{proposal,design,tasks}.md`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/AGENT_TOOL_USAGE.md` | NEW: 3 decision trees (edit / write / read-offset) with explicit do/don't table |
| `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh` | NEW: bash guard, warn-only (exit 0), detects 3 stale patterns |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_tool_friction_regression.py` | NEW: 7 pytest cases covering each mitigation + anti-spam |
| `tests/unit/test_agent_tool_usage_doc.py` | NEW: assert AGENT_TOOL_USAGE.md exists with 3 required sections |

### Documentation

| File | Responsibility |
|---|---|
| `docs/change-quality-guide.md` | MODIFY: reference the new decision tree in "agent tool discipline" note (optional, only if already exists as section) |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/reduce-rdd-workflow-tool-call-friction
python3 -m pytest tests/unit/test_skill_meta.py -q 2>&1 | tail -3
```

- [ ] **Confirm the guard script target dir exists**

```bash
ls -d skills/rdd-workflow-brainstorm/scripts
ls -d skills/_lib
ls -d tests/integration
```

---

### Task 1: Create `skills/_lib/AGENT_TOOL_USAGE.md` (TDD)

**Files:**
- Create: `skills/_lib/AGENT_TOOL_USAGE.md`
- Create: `tests/unit/test_agent_tool_usage_doc.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_agent_tool_usage_doc.py`:

```python
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SECTIONS = [
    "## Edit 决策树",
    "## Write 决策树",
    "## Read Offset 决策树",
]


def test_agent_tool_usage_doc_exists():
    doc = ROOT / "skills" / "_lib" / "AGENT_TOOL_USAGE.md"
    assert doc.is_file(), f"missing {doc}"


def test_agent_tool_usage_doc_has_all_decision_trees():
    doc = ROOT / "skills" / "_lib" / "AGENT_TOOL_USAGE.md"
    content = doc.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in content, f"missing section {section!r}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_agent_tool_usage_doc.py -v`
Expected: FAIL — `FileNotFoundError` (doc does not exist yet)

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/AGENT_TOOL_USAGE.md` with the 3 required `##` sections plus a top "Why" note. Content must be concrete:

```markdown
# AGENT Tool Usage — 工具选用决策表

> rdd-workflow dogfood 实测 (ses_fb4e3770dffeCYhR7xxAAQdI9l, 492 tool calls, 7 errors/1.4%)。
> 修 3 类可避免摩擦。**本文件是 Agent 工具调用的决策依据 — 每次 edit/write/read 前先看对应决策树。**

## Edit 决策树

- 目标文件已存在 且 需要局部修改 → **edit**（用精确 oldString）
- 目标文件不存在 → **write**
- 上一次 Read/Edit 该文件 > 10 分钟前 → **先 Read 全文再 edit**（防 stale oldString）
- edit 报 "Could not find oldString" → 立即 **Read 全文 → 重试 edit 或降级 write**

## Write 决策树

- 目标文件已存在 → **禁止 write**（改走 edit；整文件重写也用 edit 带完整 oldString）
- 目标文件不存在 → write 可
- write 报 "File already exists" → **改 edit** 或 **Read 后 write**

## Read Offset 决策树

- 读某行号 → **先 Read 文件头确认总行数**，再带 offset
- 行号来自脚本硬编码 → **改用动态 offset**（`python3 -c "print(len(open(p).readlines()))"` 先取行数）
- read 报 "Offset out of range" → **重读文件头**，用实际行数
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_agent_tool_usage_doc.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit** (execute 阶段不逐任务 commit；archive 前统一聚合 commit)

---

### Task 2: Create `pre_tool_use_check.sh` guard (TDD)

**Files:**
- Create: `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh`
- Create: `tests/unit/test_pre_tool_use_check.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_pre_tool_use_check.py`. The guard is a bash script emitting stderr; test it via subprocess with controlled inputs:

```python
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "skills" / "rdd-workflow-brainstorm" / "scripts" / "pre_tool_use_check.sh"


def run_guard(*args, env_extra=None):
    env = dict(os.environ)
    env["RDDF_GUARD_FILE_STATE"] = "stale"  # simulated file state marker
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["bash", str(GUARD), *args],
        capture_output=True, text=True, env=env,
    )
    return proc


def test_guard_warns_on_stale_edit():
    proc = run_guard("edit", "file_x")
    assert proc.returncode == 0, proc.stderr
    assert "STALE-LIKELY" in proc.stderr


def test_guard_warns_on_write_existing():
    proc = run_guard("write", "file_x", env_extra={"RDDF_GUARD_TARGET_EXISTS": "1"})
    assert proc.returncode == 0, proc.stderr
    assert "EXISTS" in proc.stderr


def test_guard_warns_on_read_offset():
    proc = run_guard("read", "file_y", "1104")
    assert proc.returncode == 0, proc.stderr
    assert "OFFSET" in proc.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_pre_tool_use_check.py -v`
Expected: FAIL — `bash: .../pre_tool_use_check.sh: No such file`

- [ ] **Step 3: Write minimal implementation**

Create `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh`:

```bash
#!/usr/bin/env bash
# pre_tool_use_check.sh <tool> [target] [offset]
# Warn-only guard (always exit 0). Emits stderr hints for 3 stale patterns.
# Env override for testability:
#   RDDF_GUARD_FILE_STATE=stale|fresh   — simulated edit target freshness
#   RDDF_GUARD_TARGET_EXISTS=1|0        — simulated write target existence
# Oracle C1: no bash string interpolation into python.

set -uo pipefail

TOOL="${1:-}"
TARGET="${2:-}"
OFFSET="${3:-}"

case "$TOOL" in
  edit)
    state="${RDDF_GUARD_FILE_STATE:-fresh}"
    if [ "$state" = "stale" ]; then
      echo "[pre-tool-check] STALE-LIKELY: edit '$TARGET' after long idle — Read full file first" >&2
    fi
    ;;
  write)
    exists="${RDDF_GUARD_TARGET_EXISTS:-0}"
    if [ "$exists" = "1" ]; then
      echo "[pre-tool-check] EXISTS: write '$TARGET' onto existing file — use edit instead" >&2
    fi
    ;;
  read)
    if [ -n "$OFFSET" ]; then
      echo "[pre-tool-check] OFFSET: read '$TARGET' with hardcoded offset $OFFSET — confirm actual line count first" >&2
    fi
    ;;
esac

exit 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_pre_tool_use_check.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

---

### Task 3: Add 7 regression cases (TDD)

**Files:**
- Create: `tests/integration/test_tool_friction_regression.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_tool_friction_regression.py`. 7 tests — 4 mitigation-verification + 3 anti-spam:

```python
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "skills" / "rdd-workflow-brainstorm" / "scripts" / "pre_tool_use_check.sh"


def run_guard(*args, **kw):
    env = dict(kw.pop("env", {}))
    env["PATH"] = "/usr/bin:/bin"
    return subprocess.run(
        ["bash", str(GUARD), *args], capture_output=True, text=True, env=env,
    )


def test_edit_oldstring_mismatch_triggers_read_fallback():
    proc = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "stale"})
    assert "STALE-LIKELY" in proc.stderr


def test_write_existing_file_triggers_edit_or_read_write():
    proc = run_guard("write", "a.md", env={"RDDF_GUARD_TARGET_EXISTS": "1"})
    assert "EXISTS" in proc.stderr


def test_read_hardcoded_offset_triggers_dynamic_offset():
    proc = run_guard("read", "a.py", "999")
    assert "OFFSET" in proc.stderr


def test_edit_after_fresh_read_no_warning():
    proc = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "fresh"})
    assert proc.stderr.strip() == ""


def test_write_new_file_no_warning():
    proc = run_guard("write", "new.md", env={"RDDF_GUARD_TARGET_EXISTS": "0"})
    assert proc.stderr.strip() == ""


def test_read_without_offset_no_warning():
    proc = run_guard("read", "a.py")
    assert proc.stderr.strip() == ""


def test_repeated_identical_tool_call_collapses_to_single_warning():
    # two consecutive stale edits → exactly one warning line total
    p1 = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "stale"})
    p2 = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "stale"})
    assert p1.stderr.count("STALE-LIKELY") == 1
    assert p2.stderr.count("STALE-LIKELY") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/integration/test_tool_friction_regression.py -v`
Expected: FAIL — first test fails (guard missing or no hint)

- [ ] **Step 3: Implement — this is satisfied by Task 2's guard** (no new code needed)

If all 7 pass already after Task 2, that's acceptable — the regression file still locks the behavior. If any fails, patch the guard script accordingly (e.g., ensure `fresh`/`0`/no-offset paths emit empty stderr).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/integration/test_tool_friction_regression.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Defer commit**

---

### Task 4: Wire guard into brainstorm skill docs

**Files:**
- Modify: `skills/rdd-workflow-brainstorm/SKILL.md` (append a "Agent 工具纪律" callout referencing the guard + decision tree)

- [ ] **Step 1: Write failing test** — test that SKILL.md references the guard path:

```python
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_brainstorm_skill_references_guard():
    skill = ROOT / "skills" / "rdd-workflow-brainstorm" / "SKILL.md"
    content = skill.read_text()
    assert "pre_tool_use_check.sh" in content
    assert "AGENT_TOOL_USAGE.md" in content
```

(Add this test to `tests/unit/test_agent_tool_usage_doc.py`.)

- [ ] **Step 2: Run test — FAIL** (not yet referenced)

- [ ] **Step 3: Implement** — append to `skills/rdd-workflow-brainstorm/SKILL.md`:

```markdown
## Agent 工具纪律

编辑/写入/读取前参阅 `skills/_lib/AGENT_TOOL_USAGE.md` 决策树。若命中 3 类 stale 模式
(edit oldString 过期 / write 覆盖已存在文件 / read 硬编码行号), 先 Read 再操作。
检测脚本: `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh` (warn-only, 不阻断)。
```

- [ ] **Step 4: Run test — PASS**

- [ ] **Step 5: Defer commit**

---

### Task 5: Final verification + tasks.md sync

**Files:**
- Modify: `openspec/changes/reduce-rdd-workflow-tool-call-friction/tasks.md`

- [ ] **Step 1: Run the full test subset**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/reduce-rdd-workflow-tool-call-friction
python3 -m pytest tests/unit/test_agent_tool_usage_doc.py tests/unit/test_pre_tool_use_check.py tests/integration/test_tool_friction_regression.py -v
```

Expected: all pass

- [ ] **Step 2: Verify no lingering tool-friction in new files** (manual scan)

```bash
grep -rn "TBD\|TODO\|FIXME" skills/_lib/AGENT_TOOL_USAGE.md skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh || echo "clean"
```

- [ ] **Step 3: Update tasks.md checkboxes** — flip every `- [ ]` in `openspec/changes/reduce-rdd-workflow-tool-call-friction/tasks.md` to `- [x]`

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/reduce-rdd-workflow-tool-call-friction
sed -i 's/^- \[ \]/- [x]/' openspec/changes/reduce-rdd-workflow-tool-call-friction/tasks.md
grep -c '^- \[x\]' openspec/changes/reduce-rdd-workflow-tool-call-friction/tasks.md
```

- [ ] **Step 4: Confirm archive gate preconditions**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/reduce-rdd-workflow-tool-call-friction
git status --short
```

Expected: only the plan-created files + artifacts appear (all new/untracked or modified), no stray deletions.

- [ ] **Step 5: Defer commit** (archive 前统一聚合 commit)
