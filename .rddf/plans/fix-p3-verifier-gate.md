# fix-p3-verifier-gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 P3 归档前的验收门真实生效 —— 用既有的 `archive_gate_check` 取代「预调用一个不存在的脚本 + 把它的缺席当作通过」的失效路径，并补上 `openspec_tracked=false` 分支提前 return 导致的门缺失。

**Architecture:** 不新增校验逻辑。验收判据（sha 绑定 / cache 完整性 / `STRICT_AC_GATE` 两态 / bypass 审计 / 三条出路文案）**全部复用** `_lib/archive.sh:360-556` 的 `archive_gate_check`，本 change 只做两件事：① 让 P3 调用它；② 让 `archive_change` 的 `openspec_tracked=false` 分支也走到它。verdict cache 由 agent 走 `rdd-verifier` skill 产出（ADR-0045），bash 层只读不产。

**关键实测前提（决定 `tasks_root` 的取法）**：`git worktree add` 出来的 worktree 里，`.rddf/state/` 与 `openspec/` **都不存在**（两者在本仓均 gitignored）。`archive_gate_check` 用 `$tasks_root` 同时定位 `tasks.md` / verdict cache / `git rev-parse HEAD`，因此**不能无条件传 worktree**（否则门永远读不到 cache）；也不能无条件传主仓（tracked-openspec 的仓库里 tasks.md 在 worktree）。

**Tech Stack:** bash（`_lib/archive.sh` / `skills/rdd-builder/scripts/phase3_archive.sh`）+ bats（集成测试）+ 既有 `archive_gate.py`（不动）。

---

## File Structure

### Production Code

| File | 类型 | Responsibility |
|---|---|---|
| `_lib/archive.sh` | 改 | `archive_change` 的 `openspec_tracked=false` 分支（`:612-620`）在 `openspec archive` 之前补 `archive_gate_check "$name" "$main_root"` |
| `skills/rdd-builder/scripts/phase3_archive.sh` | 改 | 删除失效的 `verifier_run.sh` 预调用与 `route_verifier_verdict($VERIFIER_EXIT)` 路由；改为「解析 tasks_root → 调 `archive_gate_check` → 归档」 |

### Tests

| File | 类型 | Responsibility |
|---|---|---|
| `tests/integration/test_rdd_builder_phase3_archive.bats` | 新 | P3 的 gate 三态（complete / missing cache / stale sha）+ bypass 两态 |
| `tests/integration/test_archive_gate_tracked_false.bats` | 新 | `archive_change` 在 `openspec_tracked=false` 下真的过门（无 cache ⇒ 拒绝） |
| `tests/unit/test_phase3_verifier_wiring.py` | 新 | 静态守卫：`skills/` + `_lib/` 下无 `verifier_run` 引用；`phase3_archive.sh` 内不再有 `VERIFIER_EXIT=0` 初值放行 |

### 不做（Out of Scope，见 improvement）

- 不改 `archive_gate_check` 的判据与文案（门只有一个真源）
- 不把归档动作交给 `archive_change`（那是 `fix-worktree-archive-path`）
- 不改 `run_verification.sh` 的 staging 语义

---

### Task 1: `archive_change` 的 false 分支补门

**Files:**
- Modify: `_lib/archive.sh:600-621`
- Test: `tests/integration/test_archive_gate_tracked_false.bats`

**为什么 `tasks_root` 传 `$main_root` 而不是 `$wt_path`**：该分支存在的场景就是 `openspec/` 未入库，而 `openspec/` 未入库 ⇒ worktree 里没有 `openspec/changes/<name>/tasks.md`，也没有 `.rddf/state/verifier/`（实测，见 Architecture）。传 `$wt_path` 会让门在「找不到 tasks.md」处失败，等于把门换成另一个必然失败。

- [ ] **Step 1: Write the failing test**

```bash
#!/usr/bin/env bats
# tests/integration/test_archive_gate_tracked_false.bats
#
# archive_change must run archive_gate_check on the openspec_tracked=false
# branch too (per fix-p3-verifier-gate). Historically that branch returned 0
# before reaching the gate call at step 2.5.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q . && git config user.email t@t && git config user.name t
    mkdir -p .rddf openspec/changes/demo .rddf/state
    printf 'git:\n  openspec_tracked: false\n' > .rddf/project.yaml
    printf '# proposal\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    git add -A && git commit -qm init
    # A worktree is required by archive_change; create it via git directly.
    git worktree add -q .rddf/wt/demo -b openspec/demo
}

teardown() {
    cd /
    git -C "$TEST_TMP" worktree remove --force "$TEST_TMP/.rddf/wt/demo" 2>/dev/null || true
    rm -rf "$TEST_TMP"
}

@test "tracked=false: archive_change refuses when no verdict cache exists" {
    run bash -c "cd '$TEST_TMP' && source '$REPO_ROOT/_lib/archive.sh' && archive_change demo"
    [ "$status" -ne 0 ]
}

@test "tracked=false: gate is reached (failure is the gate, not worktree lookup)" {
    run bash -c "cd '$TEST_TMP' && source '$REPO_ROOT/_lib/archive.sh' && archive_change demo"
    [[ "$output" == *"找不到 worktree"* ]] && false
    [ "$status" -eq 3 ] || [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_gate_tracked_false.bats`
Expected: 第 1 条 **FAIL**（当前 false 分支直接 `openspec archive` 后 `return 0`，status = 0）

- [ ] **Step 3: Write minimal implementation**

```bash
  if [ "$openspec_tracked" = "false" ] || [ "$openspec_tracked" = "False" ]; then
    echo "📦 openspec_tracked=false: 跳过 git merge/commit"
    switch_to_default_branch "$main_root" "$default_branch" || return 1
    # Archive gate (ADR-0035) must run on this branch too. The tracked branch
    # only reaches it at step 2.5, which sits below this early return.
    # tasks_root = $main_root: this branch exists precisely because openspec/
    # is untracked, so the worktree has neither openspec/ nor .rddf/state/.
    # Output is NOT silenced — a rejected archive must say why and how to unblock.
    archive_gate_check "$name" "$main_root" || return 3
    if ! openspec archive "$name" --yes; then
      echo "❌ openspec archive 失败"
      return 1
    fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_gate_tracked_false.bats`
Expected: 2/2 PASS

- [ ] **Step 5: 回归既有 archive 测试**

Run: `bats tests/integration/test_archive*.bats`
Expected: 全绿（tracked=true 路径行为不变）

---

### Task 2: P3 改为调用 `archive_gate_check`

**Files:**
- Modify: `skills/rdd-builder/scripts/phase3_archive.sh:24-99`
- Test: `tests/integration/test_rdd_builder_phase3_archive.bats`

- [ ] **Step 1: Write the failing test**

（Task 4 提供完整 bats；此处先写最小失败用例）

```bash
@test "phase3: refuses to archive when no verdict cache exists" {
    run env PROJECT_ROOT="$TEST_TMP" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 7 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_builder_phase3_archive.bats -f "no verdict cache"`
Expected: FAIL（当前脚本 exit 0 / 或 openspec archive 失败 exit 7 但原因错）

- [ ] **Step 3: Write minimal implementation**

删除 `:24-46` 的预调用与 `DECISION_JSON` 解析、`:48-81` 的 `HALTED` / `BACK_ROUTE` 两个 block，改为：

```bash
# --- Execution mode + tasks root -------------------------------------------
# Resolve the rdd-workflow package root — the directory that CONTAINS `_lib/`.
# It is NOT the project root: in a user project `_lib/` lives under the installed
# package. Order mirrors phase2_execute.sh: owning package first (dev checkout /
# symlinked global install), then project-local, then global.
_resolve_pkg_root() {
    local c here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
    if [ -d "$here/_lib" ]; then printf '%s' "$here"; return 0; fi
    for c in \
        "$PROJECT_ROOT/.opencode/skills/rdd-workflow" \
        "$HOME/.agents/skills/rdd-workflow" \
        "$HOME/.agents/skills"
    do
        if [ -n "$c" ] && [ -d "$c/_lib" ]; then printf '%s' "$c"; return 0; fi
    done
    return 1
}
PKG_ROOT="$(_resolve_pkg_root || true)"

EXEC_MODE=$(PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 -c "
import os, sys
if os.environ.get('PKG_ROOT'):
    sys.path.insert(0, os.environ['PKG_ROOT'])
from _lib.builder_handoff import read_builder_handoff
print(read_builder_handoff(os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME']).get('execution_mode_decision', {}).get('mode', 'worktree'))
" 2>/dev/null || echo "worktree")

WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"
TASKS_ROOT="$PROJECT_ROOT"
if [ "$EXEC_MODE" = "worktree" ]; then
    [ -d "$WT_PATH" ] || { echo "worktree not found at $WT_PATH" >&2; exit 3; }
    if [ -f "$WT_PATH/openspec/changes/$CHANGE_NAME/tasks.md" ]; then
        TASKS_ROOT="$WT_PATH"
    fi
fi

# Archive gate (ADR-0035 / ADR-0045).
# shellcheck source=/dev/null
source "$PKG_ROOT/_lib/archive.sh" 2>/dev/null || true
if ! declare -f archive_gate_check >/dev/null 2>&1; then
    echo "❌ archive_gate_check unavailable: failed to source $PKG_ROOT/_lib/archive.sh" >&2
    exit 7
fi
archive_gate_check "$CHANGE_NAME" "$TASKS_ROOT" || exit 7
```

归档段保持不变（`cd "$WT_PATH"` + `openspec archive`），但 `cd` 改用绝对路径 `$WT_PATH`；`WT_PATH` 声明同时服务于 Task 2 与 Task 4。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rdd_builder_phase3_archive.bats -f "no verdict cache"`
Expected: PASS

- [ ] **Step 5: 确认没有遗留的 exit-code 路由**

```bash
grep -n "route_verifier_verdict\|VERIFIER_EXIT\|DECISION_JSON" skills/rdd-builder/scripts/phase3_archive.sh
```
Expected: 无输出（`route_verifier_verdict` 函数本体保留在 `_lib/builder_retry.py`，但 P3 不再用它作 verdict 输入；重试计数由 `skills/rdd-verifier/scripts/route_loop.sh` 负责，per ADR-0034）

---

### Task 3: 静态守卫（无 `verifier_run` 残留 / 无初值放行）

**Files:**
- Test: `tests/unit/test_phase3_verifier_wiring.py`

- [ ] **Step 1: Write the failing test**

```python
"""Static guards for fix-p3-verifier-gate (AC-2 / AC-1)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_verifier_run_reference_in_code():
    out = subprocess.run(
        ["grep", "-rn", "verifier_run", str(ROOT / "skills"), str(ROOT / "_lib")],
        capture_output=True, text=True,
    )
    # grep exits 1 when nothing matched
    assert out.stdout.strip() == "", out.stdout


def test_phase3_has_no_default_pass_on_verifier_exit():
    src = (ROOT / "skills/rdd-builder/scripts/phase3_archive.sh").read_text()
    assert "VERIFIER_EXIT=0" not in src
    assert "route_verifier_verdict" not in src
    assert "archive_gate_check" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_phase3_verifier_wiring.py -q`
Expected: 2 FAIL（当前 phase3 有 `verifier_run.sh` 引用与 `VERIFIER_EXIT=0`）

- [ ] **Step 3: Write minimal implementation**

Task 2 已删除代码侧引用；若 `skills/` 下仍有残留（如文档注释），一并清理。

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_phase3_verifier_wiring.py -q`
Expected: 2 passed

---

### Task 4: P3 gate 三态 + bypass 两态 bats

**Files:**
- Test: `tests/integration/test_rdd_builder_phase3_archive.bats`（追加）

- [ ] **Step 1: Write the failing tests**

```bash
@test "phase3: archives when verdict cache is complete and sha matches" {
    _write_cache "$(git -C "$TEST_TMP" rev-parse HEAD)" pass
    _fake_openspec
    run env PROJECT_ROOT="$TEST_TMP" PATH="$FAKE_BIN:$PATH" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 0 ]
}

@test "phase3: refuses when cached codebase_commit is stale" {
    _write_cache "0000000000000000000000000000000000000000" pass
    run env PROJECT_ROOT="$TEST_TMP" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 7 ]
    [[ "$output" == *"stale"* || "$output" == *"no valid verdict cache"* ]]
}

@test "phase3: SKIP_RDD_VERIFIER without reason still fails closed" {
    run env PROJECT_ROOT="$TEST_TMP" SKIP_RDD_VERIFIER=yes \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 7 ]
}

@test "phase3: SKIP_RDD_VERIFIER with reason passes and writes bypass audit" {
    _fake_openspec
    run env PROJECT_ROOT="$TEST_TMP" SKIP_RDD_VERIFIER=yes \
        RDDF_VERIFIER_BYPASS_REASON="integration fixture" PATH="$FAKE_BIN:$PATH" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.rddf/state/.bypass-audit.jsonl" ]
}
```

helper（setup 内）：

```bash
_write_cache() {   # $1=sha $2=pass|fail
    mkdir -p "$TEST_TMP/.rddf/state/verifier"
    python3 - "$TEST_TMP/.rddf/state/verifier/.ac-verdict-demo.json" "$1" "$2" <<'PY'
import json, sys
path, sha, mode = sys.argv[1:4]
status = "pass" if mode == "pass" else "fail"
verdict = [{"ac_id": "AC-1", "description": "d", "status": status,
            "confidence": 0.9, "evidence": [], "reasoning": "arena"}]
json.dump({"schema_version": 2, "version": 2, "change": "demo",
           "codebase_commit": sha, "verdict": verdict,
           "verification_state": "passed" if status == "pass" else "failed",
           "failed_acs": [] if status == "pass" else ["AC-1"]},
          open(path, "w"))
PY
}
_fake_openspec() {
    FAKE_BIN="$TEST_TMP/bin"; mkdir -p "$FAKE_BIN"
    printf '#!/bin/sh\nexit 0\n' > "$FAKE_BIN/openspec"; chmod +x "$FAKE_BIN/openspec"
}
```

- [ ] **Step 2: Run to verify failures**

Run: `bats tests/integration/test_rdd_builder_phase3_archive.bats`
Expected: no-cache / stale / bypass 两条中至少 3 条 FAIL

- [ ] **Step 3: implementation**

Task 2 已实现；若 bypass 审计未写，确认失败来自 `archive_gate_check:539-547` 而非本 change 新增代码（若是门内缺陷，**停下来路由**，不在本 change 改门）。

- [ ] **Step 4: Run to verify all pass**

Run: `bats tests/integration/test_rdd_builder_phase3_archive.bats`
Expected: 5/5 PASS

---

### Task 5: 全量回归 + 遗留清扫

- [ ] **Step 1: 泄漏清扫**

```bash
grep -rn "verifier_run\|VERIFIER_EXIT\|route_verifier_verdict" skills/ _lib/ || echo "clean"
grep -rn "TODO\|FIXME\|XXX" skills/rdd-builder/scripts/phase3_archive.sh _lib/archive.sh || echo "clean"
```

- [ ] **Step 2: 本 change 测试**

```bash
bats tests/integration/test_rdd_builder_phase3_archive.bats \
     tests/integration/test_archive_gate_tracked_false.bats \
     tests/integration/test_archive*.bats
python3 -m pytest tests/unit/test_phase3_verifier_wiring.py -q
```

- [ ] **Step 3: 全量回归（archive 前门）**

```bash
./test.sh --full --regression
```
Expected: 无新增失败（baseline 已知失败可放行）

- [ ] **Step 4: doctor 全量**

```bash
bash skills/rdd-doctor/scripts/doctor.sh
```
Expected: 0 CRITICAL（WARNING 不超过基线 59）
