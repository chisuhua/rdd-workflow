# extract-guide-ship-inlined-scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `skills/guide-ship.md` from 1361 → ~720 lines by extracting 3 large inline bash blocks into 3 new `_lib/` shell scripts, following the established P1-14 / `commit_archive_moves` extraction pattern. Lock each extraction with bats regression tests.

**Architecture:** Three new self-contained bash scripts in `skills/_lib/`, each encapsulating one Phase of `guide-ship.md`:

1. `skills/_lib/ship_plan.sh` (~150 lines) — Phase 1: COMMIT GATE + parallel conflict detection + execution mode selection + worktree/lightweight setup + plan generation + iteration.json hook
2. `skills/_lib/ship_review.sh` (~180 lines) — Phase 2.5: review debt recording case/esac (4 sub-actions: in-scope tasks, side-effect debt change, arch drift, skip)
3. `skills/_lib/ship_archive.sh` (~200 lines) — Phase 3: archive mode detection + feature integrity gate + worktree/lightweight archive orchestration

Each script exposes 1-3 public functions with explicit parameters (no global side effects from sourcing), follows the existing `_lib/worktree.sh` and `_lib/archive.sh` conventions (header comment block, `main_repo_root()` for state writes, `_LIB_DIR` self-discovery), and is locked by bats integration tests asserting both function existence and absence of the original inline patterns in `guide-ship.md`.

**Tech Stack:** Bash 4+ (POSIX-ish, with `local`/`[[ ]]`) + bats 1.10+ + openspec CLI v1.4.1+ + Python 3.11+ (`skills._lib.iteration`, `skills._lib.rddf_session`).

---

## File Structure

### Production Code (NEW)

| File | Responsibility |
|---|---|
| `skills/_lib/ship_plan.sh` | Phase 1 logic: COMMIT GATE → parallel-conflict detect → mode (worktree\|lightweight) → branch/worktree setup → plan generation → iteration.json hook |
| `skills/_lib/ship_review.sh` | Phase 2.5 logic: 4-option case/esac (in-scope / debt change / drift doc / skip), conflict-driven auto-deps |
| `skills/_lib/ship_archive.sh` | Phase 3 logic: ARCHIVE_MODE detect → feature gate → worktree-mode call to `archive_change` OR lightweight-mode inline merge/cleanup |

### Production Code (MODIFY)

| File | Responsibility |
|---|---|
| `skills/guide-ship.md` | Replace 3 large inline bash blocks with `source "$REPO_ROOT/skills/_lib/ship_*.sh"` + single function call. Reduce 1361 → ~720 lines. |

### Tests (NEW)

| File | Responsibility |
|---|---|
| `tests/integration/test_ship_plan_extraction.bats` | 6 bats tests: helper exists + functions exported + guide-ship.md no longer inlines the 123-line block + runtime: COMMIT GATE / mode detection in scratch repo |
| `tests/integration/test_ship_review_extraction.bats` | 7 bats tests: helper exists + functions exported + guide-ship.md no longer inlines the 173-line case/esac + runtime: 4 sub-actions produce expected side effects |
| `tests/integration/test_ship_archive_extraction.bats` | 7 bats tests: helper exists + functions exported + guide-ship.md no longer inlines the 179-line block + runtime: ARCHIVE_MODE detection + feature integrity gate behavior |

### Documentation (MODIFY)

| File | Responsibility |
|---|---|
| `AGENTS.md` | Append 3 paragraphs under "关键约定" listing the new `_lib/ship_*.sh` helpers and their consumer (`guide-ship.md`) |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
bats tests/integration/test_archive_dedup.bats
bats tests/integration/test_guide_ship_skill.bats
```

Expected: All pass (these lock the existing `_lib/archive.sh` extraction and guide-ship.md frontmatter).

- [ ] **Identify exact line ranges of the 3 inline blocks to extract**

```bash
grep -nE '^## Phase|^```bash' skills/guide-ship.md
```

Expected output:
- Phase 1 bash block: lines 144–268 (~123 lines: COMMIT GATE + conflict detect + branch/worktree setup)
- Phase 1 bash block 2: lines 270–348 (~77 lines: plan generation + iteration.json hook)
- Phase 2.5 case/esac: lines 696–869 (~173 lines: 4-option debt handler)
- Phase 3 bash block: lines 927–1107 (~179 lines: archive orchestration)

- [ ] **Confirm `skills/_lib/worktree.sh` and `skills/_lib/archive.sh` provide needed primitives**

```bash
grep -nE '^(wt_path_for_branch|find_default_branch|main_repo_root|archive_change|commit_archive_moves|mark_iteration_archived)' skills/_lib/*.sh
```

Expected: All 6 functions exist. The 3 new scripts will reuse these — no duplication.

---

## Task 1: Create `skills/_lib/ship_plan.sh` — Phase 1 logic

**Files:**
- Create: `skills/_lib/ship_plan.sh`
- Test: `tests/integration/test_ship_plan_extraction.bats`

### Step 1.1: Write the failing test (extraction contract)

Create `tests/integration/test_ship_plan_extraction.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_ship_plan_extraction.bats
# P3-2 regression: Phase 1 of guide-ship.md (COMMIT GATE + parallel conflict
# detection + execution mode selection + worktree/lightweight setup + plan
# generation + iteration.json hook) was a 123-line inline bash block. Extracted
# to skills/_lib/ship_plan.sh.
#
# These tests lock the refactor in place:
#   1. ship_plan.sh exists with the expected function exports.
#   2. guide-ship.md sources ship_plan.sh and calls detect_execution_mode +
#      setup_execution_workspace + generate_implementation_plan + record_iteration.
#   3. guide-ship.md no longer inlines COMMIT GATE / parallel conflict / worktree
#      setup / plan generation logic.
#   4. Runtime: detect_execution_mode returns the correct mode on a scratch repo.

load ../test_helper

@test "skills/_lib/ship_plan.sh exists with expected function exports" {
  [ -f "$REPO_ROOT/skills/_lib/ship_plan.sh" ]
  grep -q "^check_artifacts_committed()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^detect_execution_mode()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^setup_execution_workspace()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^generate_implementation_plan()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^record_iteration_status()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
}

@test "ship_plan.sh sources worktree.sh for wt_path_for_branch + find_default_branch" {
  [ -f "$REPO_ROOT/skills/_lib/ship_plan.sh" ]
  grep -q "worktree.sh" "$REPO_ROOT/skills/_lib/ship_plan.sh"
}

@test "guide-ship.md Phase 1 sources and uses ship_plan.sh helpers" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  grep -nE 'source .*_lib/ship_plan.sh' "$REPO_ROOT/skills/guide-ship.md"
  grep -nE 'detect_execution_mode|setup_execution_workspace|generate_implementation_plan|record_iteration_status' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 1 no longer inlines COMMIT GATE logic" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # The old code inlined `git status --porcelain ...openspec/changes/...` and
  # `git show HEAD:openspec/changes/.../.openspec.yaml` checks.
  ! grep -nE 'git status --porcelain .*openspec/changes/' "$REPO_ROOT/skills/guide-ship.md"
  ! grep -nE 'git show HEAD:.*openspec.yaml' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 1 no longer inlines parallel conflict detection" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # The old code inlined `git worktree list | awk '$3 ~ /^openspec\//' | wc -l`
  # and `ls -d $PROJECT_ROOT/openspec/changes/*/ | grep -v archive/ | wc -l`.
  ! grep -nE "awk '..3 ~ /\\^openspec\\\\/" "$REPO_ROOT/skills/guide-ship.md"
  ! grep -nE "grep -v archive/" "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 1 no longer inlines worktree creation in markdown bash block" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # The old code inlined `git worktree add .rddf/wt/...`. After the refactor
  # that lives inside setup_execution_workspace.
  ! grep -nE 'git worktree add .*\.rddf/wt/' "$REPO_ROOT/skills/guide-ship.md"
}

@test "detect_execution_mode returns lightweight when no parallel conflict" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md
  git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/single-change
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/_lib/ship_plan.sh"
  result=$(detect_execution_mode "$TEST_REPO" "single-change")
  [ "$result" = "lightweight" ]
  rm -rf "$TEST_REPO"
}

@test "detect_execution_mode returns worktree when active worktree exists" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md
  git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/c1 openspec/changes/c2
  git worktree add -b openspec/c1 .rddf/wt/c1 HEAD >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/_lib/ship_plan.sh"
  result=$(detect_execution_mode "$TEST_REPO" "c2")
  [ "$result" = "worktree" ]
  rm -rf "$TEST_REPO"
}
```

### Step 1.2: Run test to verify it fails

Run: `bats tests/integration/test_ship_plan_extraction.bats`
Expected: All tests FAIL with "file not found" or "function not defined".

### Step 1.3: Create the helper script

Create `skills/_lib/ship_plan.sh`:

```bash
# skills/_lib/ship_plan.sh
# Phase 1 of guide-ship.md extracted into a reusable helper.
# Was a 123-line inline bash block in guide-ship.md Phase 1 (lines 144-268 + 270-348).
#
# Functions exported:
#   - check_artifacts_committed <project_root> <change_name>
#       Returns 0 if openspec/changes/<change_name>/.openspec.yaml exists in HEAD.
#       Returns 1 (with error message) if HEAD does not exist or the change
#       directory has uncommitted modifications. Mirrors the original COMMIT GATE.
#
#   - detect_execution_mode <project_root> <change_name>
#       Returns "worktree" if (existing openspec/* worktree > 0) OR
#       (more than 1 non-archived change exists). Returns "lightweight"
#       otherwise. Mirrors the original PARALLEL CONFLICT DETECTION block.
#
#   - setup_execution_workspace <project_root> <change_name> <mode>
#       If mode=worktree: creates branch openspec/<change_name>, creates
#       .rddf/wt/<change_name>/ worktree, validates the worktree is NOT
#       detached, and returns the worktree path via stdout.
#       If mode=lightweight: checks out openspec/<change_name> in main repo
#       and returns the main repo path via stdout.
#       Mirrors the original MODE-SPECIFIC SETUP + WORKTREE VERIFICATION GATE.
#
#   - generate_implementation_plan <project_root> <change_name> <mode>
#       For worktree mode: cd into worktree. For lightweight: stay in main repo.
#       Calls skill_use("rdd-workflow/writing-plans") unless
#       SKIP_PROMETHEUS_PLANNING=yes (in which case writes a placeholder
#       tasks file). Validates the resulting .rddf/plans/<change_name>.md
#       has at least 1 Task and 1 Step. Mirrors the original plan-generation
#       block.
#
#   - record_iteration_status <project_root> <change_name> <mode> <wt_path> <step_count>
#       Updates .rddf/state/iteration.json: status=in_worktree, plan_path,
#       worktree_path (if worktree mode), tasks_total. Uses python3 inline
#       to call skills._lib.iteration. Graceful exit on import failure.
#       Mirrors the original v2.0.2 iteration hook.
#
# Helpers required (provided by skills/_lib/worktree.sh):
#   - wt_path_for_branch <name>
#   - find_default_branch
#   - main_repo_root

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$_LIB_DIR/worktree.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/worktree.sh"
fi

# check_artifacts_committed <project_root> <change_name>
check_artifacts_committed() {
  local project_root="$1"
  local change_name="$2"
  local change_dir="$project_root/openspec/changes/$change_name"

  # Check working-tree dirt
  if [ -n "$(git -C "$project_root" status --porcelain "$change_dir/" 2>/dev/null)" ]; then
    echo "⚠️  检测到未提交的修改，提示用户提交或放弃" >&2
    return 1
  fi

  # Check HEAD exists and contains the change artifacts
  if ! git -C "$project_root" rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "❌ 当前仓库没有任何提交（HEAD 不存在）" >&2
    echo "请先 git commit 一些文件后再执行 plan" >&2
    return 1
  fi

  if ! git -C "$project_root" show "HEAD:openspec/changes/$change_name/.openspec.yaml" > /dev/null 2>&1; then
    echo "❌ Artifacts 尚未提交，请先提交" >&2
    return 1
  fi

  return 0
}

# detect_execution_mode <project_root> <change_name>
detect_execution_mode() {
  local project_root="$1"
  local change_name="$2"

  local existing_wt
  existing_wt=$(git -C "$project_root" worktree list 2>/dev/null | awk '$3 ~ /^openspec\//' | wc -l || echo 0)

  local total_changes
  total_changes=$(ls -d "$project_root"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l || echo 0)

  if [ "$existing_wt" -gt 0 ] || [ "$total_changes" -gt 1 ]; then
    echo "worktree"
    echo "🔀 并行风险: $existing_wt worktrees, $total_changes changes → worktree 隔离模式" >&2
  else
    echo "lightweight"
    echo "⚡ 无并行冲突 → 轻量模式（跳过 worktree）" >&2
  fi
}

# setup_execution_workspace <project_root> <change_name> <mode>
#   Echoes the working directory (WT_PATH) to stdout for the caller.
setup_execution_workspace() {
  local project_root="$1"
  local change_name="$2"
  local mode="$3"

  # Always ensure branch exists
  if ! git -C "$project_root" branch --list "openspec/$change_name" | grep -q "openspec/$change_name"; then
    git -C "$project_root" branch "openspec/$change_name" HEAD
  fi

  if [ "$mode" = "worktree" ]; then
    local wt_path="$project_root/.rddf/wt/${change_name}"
    if [ -d "$wt_path" ]; then
      if git -C "$project_root" worktree list | grep -q "$wt_path"; then
        echo "⚠️  Worktree 已存在" >&2
      else
        echo "❌ 目录冲突，请先清理: rm -rf \"$wt_path\"" >&2
        return 1
      fi
    else
      git -C "$project_root" worktree add "$wt_path" "openspec/$change_name"
    fi

    # WORKTREE VERIFICATION GATE (P0 FIX)
    local wt_branch
    wt_branch=$(git -C "$project_root" worktree list --porcelain | awk -v path="$wt_path" '
        $1 == "worktree" && $2 == path { found=1; next }
        found && $1 == "branch" { print $2; exit }
        found && $1 == "detached" { print "DETACHED"; exit }
    ')

    if [ "$wt_branch" = "DETACHED" ]; then
      echo "❌ 错误：Worktree 处于 detached HEAD 状态！" >&2
      echo "  请执行以下命令修复：" >&2
      echo "    cd $wt_path && git checkout openspec/$change_name" >&2
      return 1
    fi

    local expected="refs/heads/openspec/$change_name"
    if [ "$wt_branch" != "$expected" ] && [ "$wt_branch" != "openspec/$change_name" ]; then
      echo "⚠️  警告：Worktree 分支 $wt_branch 与预期不符" >&2
    fi

    echo "$wt_path"
  else
    # Lightweight mode: switch branch in main repo
    if ! git -C "$project_root" checkout "openspec/$change_name" 2>/dev/null; then
      echo "❌ 切换分支失败: openspec/$change_name" >&2
      return 1
    fi
    echo "⚡ 轻量模式: 已切换到 openspec/$change_name, 跳过 worktree" >&2
    echo "$project_root"
  fi
}

# generate_implementation_plan <project_root> <change_name> <mode>
generate_implementation_plan() {
  local project_root="$1"
  local change_name="$2"
  local mode="$3"

  local work_dir
  work_dir=$(setup_execution_workspace "$project_root" "$change_name" "$mode")
  cd "$work_dir" || { echo "❌ 进入工作目录失败: $work_dir" >&2; return 1; }

  if [ "${SKIP_PROMETHEUS_PLANNING:-no}" = "yes" ]; then
    echo "⚠️  跳过实施计划生成 (SKIP_PROMETHEUS_PLANNING=yes)" >&2
    mkdir -p .rddf/plans
    local plan_file=".rddf/plans/$change_name.md"
    touch "$plan_file"
    echo "- [ ] (占位任务) 手工填充 $plan_file" >> "$plan_file"
    echo 0
    return 0
  fi

  if ! skill_use "rdd-workflow/writing-plans" 2>/dev/null; then
    echo "❌ 实施计划生成失败" >&2
    echo "   rdd-workflow/writing-plans 技能未找到,检查安装是否完整" >&2
    return 1
  fi

  local plan_file=".rddf/plans/$change_name.md"
  if [ ! -f "$plan_file" ]; then
    echo "❌ 计划文件缺失: $plan_file" >&2
    return 1
  fi

  local plan_task_count
  plan_task_count=$(grep -c '^### Task' "$plan_file" 2>/dev/null || echo 0)
  local plan_step_count
  plan_step_count=$(grep -c '^- \[ \]' "$plan_file" 2>/dev/null || echo 0)

  if [ "$plan_task_count" -eq 0 ] || [ "$plan_step_count" -eq 0 ]; then
    echo "❌ 计划文件存在但无 Task 或 Step (Tasks: $plan_task_count, Steps: $plan_step_count)" >&2
    return 1
  fi

  echo "✅ 实施计划已生成: $plan_task_count Tasks / $plan_step_count Steps (TDD 5 步结构)" >&2
  echo "$plan_step_count"
}

# record_iteration_status <project_root> <change_name> <mode> <wt_path> <step_count>
record_iteration_status() {
  local project_root="$1"
  local change_name="$2"
  local mode="$3"
  local wt_path="$4"
  local step_count="$5"

  PROJECT_ROOT="$project_root" \
  CHANGE_NAME="$change_name" \
  MODE="$mode" \
  WT_PATH="$wt_path" \
  PLAN_STEP_COUNT="$step_count" \
  python3 -c '
import os, sys
try:
    from skills._lib import iteration as it_mod
except ImportError as e:
    print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
    sys.exit(0)
try:
    project_root = os.environ["PROJECT_ROOT"]
    change_name = os.environ["CHANGE_NAME"]
    mode = os.environ.get("MODE", "")
    wt_path = os.environ.get("WT_PATH", "")
    plan_step_count = os.environ.get("PLAN_STEP_COUNT", "0")
    data = it_mod.load(project_root)
    kwargs = {
        "name": change_name,
        "status": "in_worktree",
        "plan_path": f".rddf/plans/{change_name}.md",
        "tasks_total": int(plan_step_count or 0),
    }
    if mode == "worktree" and wt_path:
        kwargs["worktree_path"] = f".rddf/wt/{change_name}"
    data = it_mod.add_or_update_change(data, **kwargs)
    it_mod.save(project_root, data)
    print("✅ iteration.json: status=in_worktree, plan_path 已记录")
except Exception as e:
    print(f"⚠️  iteration.json 更新失败 (非致命): {e}", file=sys.stderr)
    sys.exit(0)
' 2>&1 | grep -v "^$" || true
}
```

### Step 1.4: Run test to verify it passes

Run: `bats tests/integration/test_ship_plan_extraction.bats`
Expected: All 8 tests PASS.

### Step 1.5: Commit

```bash
git add skills/_lib/ship_plan.sh tests/integration/test_ship_plan_extraction.bats
git commit -m "feat(ship): extract Phase 1 inline scripts to _lib/ship_plan.sh"
```

---

## Task 2: Wire `guide-ship.md` Phase 1 to call `ship_plan.sh` helpers

**Files:**
- Modify: `skills/guide-ship.md` (Phase 1 bash block, lines 144-348)

### Step 2.1: Write the failing test (guide-ship integration contract)

Append to `tests/integration/test_ship_plan_extraction.bats` (BEFORE the runtime tests):

```bash
@test "guide-ship.md Phase 1 source block is now ≤ 30 lines (was 200+)" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # Extract just the FIRST bash block under Phase 1 heading (after line 144)
  # and count its lines. After refactor it should be a thin call-out.
  local block_lines
  block_lines=$(awk '/^```bash$/{n++; if(n==1){capture=1;next}} capture{print; if(/^```$/){exit}}' "$REPO_ROOT/skills/guide-ship.md" | wc -l)
  [ "$block_lines" -le 30 ]
}
```

### Step 2.2: Run test to verify it fails

Run: `bats tests/integration/test_ship_plan_extraction.bats -f "Phase 1 source block"`
Expected: FAIL.

### Step 2.3: Replace the Phase 1 inline blocks (lines 144-348) with thin wrappers

In `skills/guide-ship.md`, replace lines 144-348 (the two large bash blocks under `## Phase 1: plan`) with:

```bash
# === Phase 1: thin orchestrator — heavy lifting in skills/_lib/ship_plan.sh ===
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CHANGE_NAME="${CHANGE_NAME:-fix-ns-pollution}"  # default for documentation

source "$REPO_ROOT/skills/_lib/ship_plan.sh"

# 1) COMMIT GATE
check_artifacts_committed "$PROJECT_ROOT" "$CHANGE_NAME" || {
  echo "请先 commit openspec/changes/$CHANGE_NAME/ 后重试"
  exit 1
}

# 2) PARALLEL CONFLICT DETECTION → execution mode
MODE=$(detect_execution_mode "$PROJECT_ROOT" "$CHANGE_NAME")

# 3) MODE-SPECIFIC SETUP + WORKTREE VERIFICATION GATE
WT_PATH=$(setup_execution_workspace "$PROJECT_ROOT" "$CHANGE_NAME" "$MODE")

# 4) PLAN GENERATION (calls skill_use "rdd-workflow/writing-plans" internally)
PLAN_STEP_COUNT=$(generate_implementation_plan "$PROJECT_ROOT" "$CHANGE_NAME" "$MODE")

# 5) iteration.json HOOK (status → in_worktree)
record_iteration_status "$PROJECT_ROOT" "$CHANGE_NAME" "$MODE" "$WT_PATH" "$PLAN_STEP_COUNT"
```

### Step 2.4: Run all Phase 1 tests to verify they pass

Run: `bats tests/integration/test_ship_plan_extraction.bats`
Expected: All 9 tests PASS.

### Step 2.5: Run smoke + related integration tests to confirm no regression

```bash
bats tests/smoke.bats
bats tests/integration/test_guide_ship_skill.bats
bats tests/integration/test_archive_dedup.bats
```

Expected: All pass.

### Step 2.6: Commit

```bash
git add skills/guide-ship.md tests/integration/test_ship_plan_extraction.bats
git commit -m "refactor(ship): wire Phase 1 to _lib/ship_plan.sh, drop 200 inline lines"
```

---

## Task 3: Create `skills/_lib/ship_review.sh` — Phase 2.5 logic

**Files:**
- Create: `skills/_lib/ship_review.sh`
- Test: `tests/integration/test_ship_review_extraction.bats`

### Step 3.1: Write the failing test

Create `tests/integration/test_ship_review_extraction.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_ship_review_extraction.bats
# P3-2 regression: Phase 2.5 of guide-ship.md was a 173-line case/esac
# bash block handling 4 review-debt sub-actions. Extracted to
# skills/_lib/ship_review.sh.
#
# These tests lock the refactor in place:
#   1. ship_review.sh exists with handle_review_action exported.
#   2. guide-ship.md Phase 2.5 calls handle_review_action "$choice" and
#      no longer inlines the 4 sub-action blocks.
#   3. Runtime: each of the 4 sub-actions produces the expected side effect.

load ../test_helper

@test "skills/_lib/ship_review.sh exists with handle_review_action" {
  [ -f "$REPO_ROOT/skills/_lib/ship_review.sh" ]
  grep -q "^handle_review_action()" "$REPO_ROOT/skills/_lib/ship_review.sh"
}

@test "guide-ship.md Phase 2.5 sources and uses ship_review.sh" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  grep -nE 'source .*_lib/ship_review.sh' "$REPO_ROOT/skills/guide-ship.md"
  grep -nE 'handle_review_action' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 2.5 no longer inlines the 4 debt-action case branches" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # Branch 1 (in-scope append)
  ! grep -nE '追加到 tasks.md' "$REPO_ROOT/skills/guide-ship.md"
  # Branch 2 (side-effect debt change → proposal-suggestions.md)
  ! grep -nE 'type.: .debt.' "$REPO_ROOT/skills/guide-ship.md"
  # Branch 3 (arch drift doc)
  ! grep -nE 'drift-analysis\.md' "$REPO_ROOT/skills/guide-review.sh" 2>/dev/null
  ! grep -nE '\-drift-analysis\.md' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 2.5 source block is now ≤ 20 lines (was 173)" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # Count the bash block under Phase 2.5 (the case/esac replacement)
  local block_lines
  block_lines=$(awk '/^## Phase 2\.5/{found=1; next} found && /^```bash$/{capture=1; next} capture && /^```$/{exit} capture{print}' "$REPO_ROOT/skills/guide-ship.md" | wc -l)
  [ "$block_lines" -le 20 ]
}

@test "handle_review_action option 1 appends review todos to tasks.md" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  mkdir -p openspec/changes/test-change
  echo "# tasks" > openspec/changes/test-change/tasks.md
  echo "/tmp/review_new_todos.txt" > /tmp/review_new_todos.txt
  printf "src/api.py: consider type hints\n" > /tmp/review_new_todos.txt
  source "$REPO_ROOT/skills/_lib/ship_review.sh"
  handle_review_action "$TEST_REPO" "test-change" "$TEST_REPO" "1"
  grep -q "review: src/api.py" "$TEST_REPO/openspec/changes/test-change/tasks.md"
  rm -rf "$TEST_REPO"
  rm -f /tmp/review_new_todos.txt
}

@test "handle_review_action option 2 creates debt entry in proposal-suggestions.md" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  mkdir -p openspec/changes/parent-change
  source "$REPO_ROOT/skills/_lib/ship_review.sh"
  handle_review_action "$TEST_REPO" "parent-change" "$TEST_REPO" "2"
  [ -f "$TEST_REPO/proposal-suggestions.md" ]
  grep -q '"type": "debt"' "$TEST_REPO/proposal-suggestions.md"
  grep -q 'cleanup-parent-change-debt' "$TEST_REPO/proposal-suggestions.md"
  rm -rf "$TEST_REPO"
}

@test "handle_review_action option 4 is a no-op (skip)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  source "$REPO_ROOT/skills/_lib/ship_review.sh"
  run handle_review_action "$TEST_REPO" "x" "$TEST_REPO" "4"
  [ "$status" -eq 0 ]
  rm -rf "$TEST_REPO"
}
```

### Step 3.2: Run test to verify it fails

Run: `bats tests/integration/test_ship_review_extraction.bats`
Expected: All FAIL with "file not found".

### Step 3.3: Create the helper script

Create `skills/_lib/ship_review.sh`:

```bash
# skills/_lib/ship_review.sh
# Phase 2.5 of guide-ship.md extracted into a reusable helper.
# Was a 173-line case/esac block (lines 696-869) handling 4 review-debt actions.
#
# Functions exported:
#   - handle_review_action <project_root> <change_name> <wt_path> <choice>
#       Dispatches review-debt handling to one of 4 sub-actions based on
#       <choice> (1=in-scope, 2=side-effect debt change, 3=arch drift,
#       4=skip). Reads from /tmp/review_new_todos.txt + /tmp/review_test_failures.txt
#       (set by upstream review-collection step). Mirrors the original case/esac.
#
# Input contract (set by caller before invocation):
#   /tmp/review_new_todos.txt      - newline-separated "file: text" pairs
#   /tmp/review_test_failures.txt  - newline-separated failure messages
#
# Helpers required (provided by skills/_lib/worktree.sh):
#   - wt_path_for_branch <name>
#   - main_repo_root

# _review_append_in_scope_tasks <wt_path> <change_name>
#   Action 1: append /tmp/review_new_todos.txt entries as `- [ ] review:` lines
#   to openspec/changes/<change_name>/tasks.md.
_review_append_in_scope_tasks() {
  local wt_path="$1"
  local change_name="$2"
  local tasks_file="$wt_path/openspec/changes/$change_name/tasks.md"
  local review_file="/tmp/review_new_todos.txt"

  echo "📝 追加范围內债务到 tasks.md..."
  if [ -f "$review_file" ] && [ -s "$review_file" ]; then
    {
      echo ""
      echo "## Review 阶段 (execute 后追加)"
      echo ""
      while IFS= read -r line; do
        local file
        file=$(echo "$line" | cut -d: -f1)
        local text
        text=$(echo "$line" | cut -d: -f2-)
        echo "- [ ] review: $file — $text"
      done < "$review_file"
    } >> "$tasks_file"
    echo "✅ 范围內债务已追加，返回 execute 继续执行..."
  else
    echo "⚠️  无范围內债务可追加"
  fi
}

# _review_create_debt_change <project_root> <change_name>
#   Action 2: append a debt entry to proposal-suggestions.md, create a new
#   openspec change, run conflict-driven auto-deps if file conflicts exist.
_review_create_debt_change() {
  local project_root="$1"
  local change_name="$2"
  local debt_name="cleanup-${change_name}-debt"

  echo "🔖 创建新 debt change: $debt_name"

  # Append to proposal-suggestions.md (type=debt)
  PY_PROJECT_ROOT="$project_root" python3 -c "
import os, json
try:
    debt = {
        'name': '$debt_name',
        'priority': 'P2',
        'source': 'execute review: $change_name',
        'status': '待创建',
        'phase': 'default',
        'category': 'arch-design',
        'type': 'debt',
        'description': '## 架构依据\n- $change_name 执行后审查发现\n## 范围\n- 见 TODO 扫描结果\n## 关键场景\n- 常规清理\n## 技术约束\n- MUST NOT 影响已有功能\n## 验收标准\n- 新增测试通过\n',
        'effort': '1天'
    }
    path = os.path.join(os.environ['PY_PROJECT_ROOT'], 'proposal-suggestions.md')
    if os.path.isfile(path):
        with open(path) as f:
            entries = json.load(f)
    else:
        entries = []
    entries.append(debt)
    with open(path, 'w') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f'✅ 已追加到 proposal-suggestions.md: {debt[\"name\"]}')
except Exception as e:
    print(f'⚠️  追加失败: {e}')
"

  # Create openspec change directory
  (
    cd "$project_root"
    openspec new change "$debt_name" 2>/dev/null || true
  )

  echo ""
  echo "🔍 检查文件冲突 + 自动增量 deps..."

  local active_changes_json
  active_changes_json=$(PY_PROJECT_ROOT="$project_root" python3 -c "
import os, sys, json
try:
    from skills._lib import iteration as it
    d = it.load(os.environ.get('PY_PROJECT_ROOT', '.'))
    out = it.list_active(d)
    names = [c['name'] for c in out if c['name'] != '$debt_name']
    print(json.dumps(names))
except Exception:
    print('[]', file=sys.stderr)
" 2>/dev/null)

  local conflict_detected="false"
  if [ -n "$active_changes_json" ] && [ "$active_changes_json" != "[]" ]; then
    local debt_keyword
    debt_keyword=$(echo "$debt_name" | sed -E 's/^(debt|fix|prefix|cleanup)-?(.*)/\2/' | sed 's/-.*//')
    if [ -n "$debt_keyword" ]; then
      for active_name in $(echo "$active_changes_json" | python3 -c "import sys, json; print(' '.join(json.load(sys.stdin)))"); do
        if echo "$active_name" | grep -qF "$debt_keyword"; then
          conflict_detected="true"
          echo "⚠️  潜在文件冲突: $debt_name 与 $active_name (共享关键词 '$debt_keyword')"
          break
        fi
      done
    fi
  fi

  if [ "$conflict_detected" = "true" ]; then
    echo "  → 自动增量 deps (将新 debt change 加入 .deps-candidates.json)..."
    PY_PROJECT_ROOT="$project_root" python3 -c "
import os, json
p = os.path.join(os.environ.get('PY_PROJECT_ROOT', '.'), '.rddf/state/.deps-candidates.json')
data = {'candidates': []}
if os.path.isfile(p):
    try:
        with open(p) as f:
            data = json.load(f)
            if not isinstance(data, dict) or 'candidates' not in data:
                data = {'candidates': []}
    except (FileNotFoundError, json.JSONDecodeError):
        data = {'candidates': []}
candidates = data.get('candidates', [])
if '$debt_name' not in candidates:
    candidates.append('$debt_name')
    data['candidates'] = candidates
    with open(p, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'  ✅ 已添加 $debt_name 到 .deps-candidates.json')
else:
    print(f'  ℹ️  $debt_name 已在 .deps-candidates.json 中')
"
    if skill_use "deps" 2>/dev/null; then
      echo "✅ 增量 deps 完成, 新 debt change 已纳入依赖图"
      echo "   查看: cat .rddf/state/.deps-output.md"
    else
      echo "⚠️  skill_use(\"deps\") 调用失败, 请手动重跑"
      echo "   运行: skill_use(\"deps\")"
    fi
  else
    echo "✅ 无文件冲突（debt change '$debt_name' 与活跃 changes 无关键词重叠）"
    echo "   debt change 可安全 deferred 到下次 sprint"
  fi
}

# _review_record_arch_drift <project_root> <change_name>
#   Action 3: write docs/architecture/<change>-drift-analysis.md and suggest
#   re-running guide-arch.
_review_record_arch_drift() {
  local project_root="$1"
  local change_name="$2"
  local drift_doc="$project_root/docs/architecture/${change_name}-drift-analysis.md"

  mkdir -p "$(dirname "$drift_doc")"
  cat > "$drift_doc" <<DRIFTDOC
# 架构漂移分析: $change_name

> **来源**: execute 后 review Phase 2.5
> **生成日期**: $(date -Iseconds)
> **关联 change**: $change_name
> **状态**: 草案

## 检测到的漂移

$(cat /tmp/review_new_todos.txt 2>/dev/null | sed 's/^/- /' || echo '(未检测到)')

## 建议操作

1. 运行 skill_use("guide-arch") 审查是否需要修正 ADR
2. 如 ADR 需修正，回到 adr-create 阶段创建或修订 ADR
3. 修正后重新运行 guide-plan → deps
DRIFTDOC
  echo "✅ 差距分析已创建: $drift_doc"
  echo ""
  echo "💡 下一步: 运行 skill_use(\"guide-arch\") 进入架构审查"
}

# handle_review_action <project_root> <change_name> <wt_path> <choice>
handle_review_action() {
  local project_root="$1"
  local change_name="$2"
  local wt_path="$3"
  local choice="$4"

  case "$choice" in
    1) _review_append_in_scope_tasks "$wt_path" "$change_name" ;;
    2) _review_create_debt_change "$project_root" "$change_name" ;;
    3) _review_record_arch_drift "$project_root" "$change_name" ;;
    4) echo "⏭️  跳过 review，直接进入 archive" ;;
    5)
      echo "📋 新增 TODO/FIXME 标记:"
      cat /tmp/review_new_todos.txt 2>/dev/null || echo "(无)"
      echo ""
      echo "📋 测试失败详情:"
      cat /tmp/review_test_failures.txt 2>/dev/null || echo "(无)"
      ;;
    *) echo "❌ 无效 review 选项: $choice" >&2; return 1 ;;
  esac
}
```

### Step 3.4: Run test to verify it passes

Run: `bats tests/integration/test_ship_review_extraction.bats`
Expected: All 7 tests PASS.

### Step 3.5: Commit

```bash
git add skills/_lib/ship_review.sh tests/integration/test_ship_review_extraction.bats
git commit -m "feat(ship): extract Phase 2.5 review-debt case/esac to _lib/ship_review.sh"
```

---

## Task 4: Wire `guide-ship.md` Phase 2.5 to call `ship_review.sh`

**Files:**
- Modify: `skills/guide-ship.md` (Phase 2.5 case/esac, lines 696-869)

### Step 4.1: Run test (already exists from Task 3)

Run: `bats tests/integration/test_ship_review_extraction.bats -f "guide-ship.md Phase 2.5 sources and uses"`
Expected: FAIL (Phase 2.5 still has inline case/esac).

### Step 4.2: Replace the Phase 2.5 case/esac (lines 696-869) with thin wrapper

In `skills/guide-ship.md`, replace the bash block starting at line 696 with:

```bash
source "$REPO_ROOT/skills/_lib/ship_review.sh"
handle_review_action "$PROJECT_ROOT" "$CHANGE_NAME" "$WT_PATH" "$choice"
```

### Step 4.3: Run all Phase 2.5 tests

Run: `bats tests/integration/test_ship_review_extraction.bats`
Expected: All 7 tests PASS.

### Step 4.4: Commit

```bash
git add skills/guide-ship.md
git commit -m "refactor(ship): wire Phase 2.5 to _lib/ship_review.sh, drop 173 inline lines"
```

---

## Task 5: Create `skills/_lib/ship_archive.sh` — Phase 3 logic

**Files:**
- Create: `skills/_lib/ship_archive.sh`
- Test: `tests/integration/test_ship_archive_extraction.bats`

### Step 5.1: Write the failing test

Create `tests/integration/test_ship_archive_extraction.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_ship_archive_extraction.bats
# P3-2 regression: Phase 3 of guide-ship.md was a 179-line inline bash block
# for archive mode detection + feature integrity gate + worktree/lightweight
# archive orchestration. Extracted to skills/_lib/ship_archive.sh.
#
# These tests lock the refactor in place:
#   1. ship_archive.sh exists with archive_change_for_mode exported.
#   2. guide-ship.md Phase 3 calls archive_change_for_mode instead of inlining
#      the 179-line block.
#   3. Runtime: detect_archive_mode returns correct mode + feature integrity
#      gate is non-blocking by default.

load ../test_helper

@test "skills/_lib/ship_archive.sh exists with expected exports" {
  [ -f "$REPO_ROOT/skills/_lib/ship_archive.sh" ]
  grep -q "^detect_archive_mode()" "$REPO_ROOT/skills/_lib/ship_archive.sh"
  grep -q "^check_feature_integrity()" "$REPO_ROOT/skills/_lib/ship_archive.sh"
  grep -q "^archive_change_for_mode()" "$REPO_ROOT/skills/_lib/ship_archive.sh"
}

@test "ship_archive.sh sources worktree.sh and archive.sh" {
  [ -f "$REPO_ROOT/skills/_lib/ship_archive.sh" ]
  grep -q "worktree.sh" "$REPO_ROOT/skills/_lib/ship_archive.sh"
  grep -q "archive.sh" "$REPO_ROOT/skills/_lib/ship_archive.sh"
}

@test "guide-ship.md Phase 3 sources and uses ship_archive.sh" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  grep -nE 'source .*_lib/ship_archive.sh' "$REPO_ROOT/skills/guide-ship.md"
  grep -nE 'archive_change_for_mode|detect_archive_mode|check_feature_integrity' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 3 no longer inlines validate_delta_targets + merge inline" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # The old code inlined `python3 skills/_lib/validate_delta_targets.py` and
  # `git merge --ff-only` / `git merge --no-ff` for the lightweight path.
  ! grep -nE 'validate_delta_targets\.py' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 3 source block is now ≤ 25 lines (was 179)" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  local block_lines
  block_lines=$(awk '/^## Phase 3: archive/{found=1; next} found && /^```bash$/{capture=1; next} capture && /^```$/{exit} capture{print}' "$REPO_ROOT/skills/guide-ship.md" | wc -l)
  [ "$block_lines" -le 25 ]
}

@test "detect_archive_mode returns worktree when worktree exists" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md && git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/c1
  git worktree add -b openspec/c1 .rddf/wt/c1 HEAD >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/_lib/ship_archive.sh"
  result=$(detect_archive_mode "$TEST_REPO" "c1")
  [ "$result" = "worktree" ]
  rm -rf "$TEST_REPO"
}

@test "detect_archive_mode returns lightweight when no worktree" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md && git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/c1
  git checkout -b openspec/c1 >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/_lib/ship_archive.sh"
  result=$(detect_archive_mode "$TEST_REPO" "c1")
  [ "$result" = "lightweight" ]
  rm -rf "$TEST_REPO"
}

@test "check_feature_integrity is non-blocking by default (FEATURE_ARCHIVE_GATE unset)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md && git add README.md && git commit -q -m "initial"
  # No iteration.json, no feature-X changes → should exit 0 (no-op)
  source "$REPO_ROOT/skills/_lib/ship_archive.sh"
  run check_feature_integrity "$TEST_REPO" "any-change"
  [ "$status" -eq 0 ]
  rm -rf "$TEST_REPO"
}
```

### Step 5.2: Run test to verify it fails

Run: `bats tests/integration/test_ship_archive_extraction.bats`
Expected: All FAIL.

### Step 5.3: Create the helper script

Create `skills/_lib/ship_archive.sh`:

```bash
# skills/_lib/ship_archive.sh
# Phase 3 of guide-ship.md extracted into a reusable helper.
# Was a 179-line inline bash block (lines 927-1107) handling archive mode
# detection, feature integrity check, and worktree/lightweight archive
# orchestration.
#
# Functions exported:
#   - detect_archive_mode <project_root> <change_name>
#       Returns "worktree" if .rddf/wt/<change_name>/ exists AND is registered
#       with `git worktree list`. Returns "lightweight" otherwise. Mirrors the
#       original ARCHIVE_MODE detection block.
#
#   - check_feature_integrity <project_root> <change_name>
#       Best-effort feature completion check using skills._lib.iteration.
#       Honors FEATURE_ARCHIVE_GATE=hard (blocking) vs unset/soft (warning).
#       Returns 0 if non-blocking OR no feature context. Returns 1 only when
#       FEATURE_ARCHIVE_GATE=hard and feature is incomplete.
#
#   - archive_change_for_mode <project_root> <change_name> <mode>
#       Full archive orchestration:
#         - worktree mode: validates branch not detached → calls
#           archive_change from archive.sh → cd back to project_root.
#         - lightweight mode: validates delta targets → fast-forward or
#           no-ff merge → openspec archive → commit_archive_moves →
#           branch cleanup (-d, fallback -D when FORCE_BRANCH_DELETE=yes).
#       Mirrors the original MODE-SPECIFIC archive orchestration.
#
# Helpers required (provided by skills/_lib/worktree.sh, archive.sh):
#   - wt_path_for_branch <name>           (worktree.sh)
#   - find_default_branch                (worktree.sh)
#   - main_repo_root                     (worktree.sh)
#   - archive_change <name>              (archive.sh)
#   - commit_archive_moves <name> <root> (archive.sh)
#   - mark_iteration_archived <name> <root> (archive.sh)

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$_LIB_DIR/worktree.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/worktree.sh"
fi
if [ -f "$_LIB_DIR/archive.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/archive.sh"
fi

# detect_archive_mode <project_root> <change_name>
detect_archive_mode() {
  local project_root="$1"
  local change_name="$2"
  local wt_path="$project_root/.rddf/wt/${change_name}"

  if [ -d "$wt_path" ] && git -C "$project_root" worktree list | grep -q "$wt_path"; then
    echo "worktree"
  else
    echo "lightweight"
  fi
}

# check_feature_integrity <project_root> <change_name>
check_feature_integrity() {
  local project_root="$1"
  local change_name="$2"

  PY_PROJECT_ROOT="$project_root" CHANGE_NAME="$change_name" python3 <<'PYEOF' 2>/dev/null
import os, sys
try:
    from skills._lib import iteration as it
except ImportError:
    sys.exit(0)

project_root = os.environ.get("PY_PROJECT_ROOT", ".")
change_name = os.environ.get("CHANGE_NAME", "")
try:
    d = it.load(project_root)
    feature = it.derive_feature_name(change_name)

    pf = None
    ch = it.get_change(d, change_name)
    if ch:
        pf = ch.get("parent_feature")
    if not change_name.startswith("feature-") and not pf:
        sys.exit(0)

    progress = it.feature_progress(d)
    if feature not in progress:
        sys.exit(0)

    done, total = progress[feature]
    if total <= 1:
        sys.exit(0)

    remaining = total - done
    if remaining > 1 or (remaining == 1 and any(
        c.get("status") != "archived"
        for c in d.get("changes", [])
        if it.derive_feature_name(c.get("name", "")) == feature
        and c.get("name") != change_name
    )):
        print(f"⚠️  Feature '{feature}' 完整性提示: 已归档 {done}/{total}")
        print(f"   还有 {total - done} 个 sub-change 未归档，此 feature 仍未完整")

        gate_mode = os.environ.get("FEATURE_ARCHIVE_GATE", "soft")
        if gate_mode == "hard":
            print(f"   ❌ FEATURE_ARCHIVE_GATE=hard 阻止归档 (请先处理其余 sub-change)")
            sys.exit(1)
        else:
            print(f"   归档不会阻断 (设置 FEATURE_ARCHIVE_GATE=hard 可升级为硬阻断)")
except SystemExit:
    raise
except Exception:
    pass
PYEOF
}

# archive_change_for_mode <project_root> <change_name> <mode>
archive_change_for_mode() {
  local project_root="$1"
  local change_name="$2"
  local mode="$3"

  if [ "$mode" = "worktree" ]; then
    local wt_path="$project_root/.rddf/wt/${change_name}"
    echo "🔍 验证 worktree 分支状态..."

    local wt_branch
    wt_branch=$(git -C "$project_root" worktree list --porcelain | awk -v path="$wt_path" '
        $1 == "worktree" && $2 == path { found=1; next }
        found && $1 == "branch" { print $2; exit }
        found && $1 == "detached" { print "DETACHED"; exit }
    ')

    if [ "$wt_branch" = "DETACHED" ]; then
      echo "❌ 错误：Worktree 处于 detached HEAD，无法 merge" >&2
      echo "   请先切换到正确分支：" >&2
      echo "   cd $wt_path && git checkout openspec/$change_name" >&2
      return 1
    fi

    archive_change "$change_name"
    cd "$project_root" || return 1
  else
    # Lightweight mode
    local default_branch
    default_branch=$(find_default_branch)
    local branch="openspec/$change_name"

    local new_commits
    new_commits=$(git -C "$project_root" rev-list --count "$default_branch..$branch" 2>/dev/null || echo 0)

    if [ "$new_commits" -eq 0 ]; then
      echo "❌ 分支 $branch 无新提交，无需 merge" >&2
    else
      echo "📦 Merge $branch → $default_branch ($new_commits 个新提交)"

      git -C "$project_root" checkout "$default_branch" || {
        echo "❌ 无法切换到 $default_branch" >&2
        return 1
      }

      if git -C "$project_root" merge --ff-only "$branch" 2>/dev/null; then
        echo "✅ Fast-forward merge 到 $default_branch 完成"
      else
        echo "⚠️  Fast-forward 不可用，创建 merge commit"
        git -C "$project_root" merge --no-ff "$branch" -m "merge: $change_name change" || {
          echo "❌ merge 失败" >&2
          return 1
        }
      fi

      # Spec-validation gate (add-spec-validation-gates)
      if ! python3 "$project_root/skills/_lib/validate_delta_targets.py" "$change_name" 2>/dev/null; then
        echo "❌ Archive pre-flight failed for $change_name" >&2
        echo "   Delta targets invalid. Run validate_delta_targets.py for details." >&2
        python3 "$project_root/skills/_lib/validate_delta_targets.py" "$change_name"
        return 1
      fi

      openspec archive "$change_name" --yes || {
        echo "⚠️  openspec archive 失败（可能是 CLI 未找到）" >&2
      }

      # Auto-commit archive file moves (failure-tolerant)
      commit_archive_moves "$change_name" "$project_root" || true
    fi

    # Delete branch
    if git -C "$project_root" branch -d "$branch" 2>/dev/null; then
      echo "✅ Branch 已删除: $branch"
    else
      echo "⚠️  Branch $branch 有未合并的提交" >&2
      if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
        git -C "$project_root" branch -D "$branch" 2>/dev/null || true
      fi
    fi

    echo "✅ $change_name 已归档（轻量模式）"
  fi
}
```

### Step 5.4: Run test to verify it passes

Run: `bats tests/integration/test_ship_archive_extraction.bats`
Expected: All 8 tests PASS.

### Step 5.5: Commit

```bash
git add skills/_lib/ship_archive.sh tests/integration/test_ship_archive_extraction.bats
git commit -m "feat(ship): extract Phase 3 archive orchestration to _lib/ship_archive.sh"
```

---

## Task 6: Wire `guide-ship.md` Phase 3 to call `ship_archive.sh`

**Files:**
- Modify: `skills/guide-ship.md` (Phase 3 bash block, lines 927-1107)

### Step 6.1: Replace the Phase 3 inline block

In `skills/guide-ship.md`, replace the bash block starting at line 927 with:

```bash
source "$REPO_ROOT/skills/_lib/ship_archive.sh"

ARCHIVE_MODE=$(detect_archive_mode "$PROJECT_ROOT" "$CHANGE_NAME")
echo "🔍 归档模式: $ARCHIVE_MODE"

check_feature_integrity "$PROJECT_ROOT" "$CHANGE_NAME"
archive_change_for_mode "$PROJECT_ROOT" "$CHANGE_NAME" "$ARCHIVE_MODE"
```

### Step 6.2: Run all Phase 3 tests + full archive integration

```bash
bats tests/integration/test_ship_archive_extraction.bats
bats tests/integration/test_archive_dedup.bats
bats tests/integration/test_commit_archive_moves.bats
bats tests/integration/test_branch_delete.bats
bats tests/integration/test_merge_verification.bats
```

Expected: All pass.

### Step 6.3: Commit

```bash
git add skills/guide-ship.md
git commit -m "refactor(ship): wire Phase 3 to _lib/ship_archive.sh, drop 179 inline lines"
```

---

## Task 7: Final verification + documentation + line-count assertion

**Files:**
- Modify: `AGENTS.md` (append 3 paragraphs under "关键约定")

### Step 7.1: Write a line-count regression test

Append to `tests/integration/test_ship_plan_extraction.bats` (or create new `test_guide_ship_line_count.bats`):

```bash
#!/usr/bin/env bats
# tests/integration/test_guide_ship_line_count.bats
# P3-2 final check: guide-ship.md should be ≤ 750 lines after extraction
# (was 1361). This guards against future inline-script regression.

load ../test_helper

@test "guide-ship.md is ≤ 750 lines after extraction (was 1361)" {
  local line_count
  line_count=$(wc -l < "$REPO_ROOT/skills/guide-ship.md")
  [ "$line_count" -le 750 ]
}

@test "guide-ship.md contains no bash blocks > 50 lines" {
  # After extraction, every remaining bash block in guide-ship.md should be
  # a thin orchestrator (≤ 50 lines). This is a soft limit to catch future
  # inline-script growth.
  local max_block
  max_block=$(awk '
    /^```bash$/ { n++; lines=0; next }
    /^```$/ { if (n>0 && lines>max) max=lines; n=0; next }
    n { lines++ }
    END { print max+0 }
  ' "$REPO_ROOT/skills/guide-ship.md")
  [ "$max_block" -le 50 ]
}
```

### Step 7.2: Run line-count tests

Run: `bats tests/integration/test_guide_ship_line_count.bats`
Expected: Both PASS.

### Step 7.3: Update AGENTS.md "关键约定" section

Append after the existing `_lib` paragraphs (search for `skills/_lib/state_vector.py` and add after the next blank line):

```markdown
### Ship 阶段 `_lib/ship_*.sh` 提取（v2.0.5 新增）

`guide-ship.md` v2.0 起按 Phase 把超过 50 行的内联 bash 块提取为 3 个 `_lib/` 脚本:

| Script | Source Phase | Public functions |
|--------|-------------|------------------|
| `skills/_lib/ship_plan.sh` | Phase 1 (plan) | `check_artifacts_committed`, `detect_execution_mode`, `setup_execution_workspace`, `generate_implementation_plan`, `record_iteration_status` |
| `skills/_lib/ship_review.sh` | Phase 2.5 (review) | `handle_review_action` (4-option dispatch) |
| `skills/_lib/ship_archive.sh` | Phase 3 (archive) | `detect_archive_mode`, `check_feature_integrity`, `archive_change_for_mode` |

`guide-ship.md` 由 1361 → ≤ 750 行。每个 script 都通过 `bats tests/integration/test_ship_*_extraction.bats` 锁定（功能性测试 + 结构性 grep 双保险），遵循 P1-14 archive.sh 提取的同款模式。
```

### Step 7.4: Run full test suite to confirm no regression

```bash
bats tests/smoke.bats
python3 -m pytest tests/unit/ -q --tb=short
python3 -m pytest tests/integration/ -q --tb=short
```

Expected: All pass. No P0/P1 regression.

### Step 7.5: Commit

```bash
git add tests/integration/test_guide_ship_line_count.bats AGENTS.md
git commit -m "docs(ship): document _lib/ship_*.sh extraction + line-count guard"
```

---

## Acceptance Criteria

- [ ] `skills/guide-ship.md` is ≤ 750 lines (was 1361).
- [ ] `skills/guide-ship.md` contains no inline bash block > 50 lines.
- [ ] 3 new helper scripts exist: `skills/_lib/ship_plan.sh`, `ship_review.sh`, `ship_archive.sh`.
- [ ] 22 new bats tests pass (8 + 7 + 7), locking function existence + extraction contract + runtime behavior.
- [ ] Existing P0/P1 regression tests still pass (`test_archive_dedup`, `test_commit_archive_moves`, `test_merge_verification`, `test_branch_delete`).
- [ ] `AGENTS.md` documents the 3 new helpers.
- [ ] No semantic change to user-facing guide-ship behavior — only internal extraction.

## Estimated Effort

- 7 tasks × ~30 min = ~3.5 hours of focused work
- Review + merge = ~30 min
- Total = ~4 hours