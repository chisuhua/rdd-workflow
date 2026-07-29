# skills/guide-ship/scripts/ship_plan.sh
# Phase 1 of guide-ship.md extracted into a reusable helper.
# Was a 123-line inline bash block in guide-ship.md Phase 1 (lines 144-268 + 270-348).
#
# Functions exported:
#   - check_artifacts_committed <project_root> <change_name>
#       Returns 0 if openspec/changes/<change_name>/.openspec.yaml exists in HEAD.
#       Returns 1 (with error message) if HEAD does not exist or the change
#       directory has uncommitted modifications. Mirrors the original COMMIT GATE.
#
#   - read_plan_handoff <project_root>
#       Reads .rddf/state/.plan-handoff.json (written by guide-plan at plan-done),
#       displays the handoff state to the user, and atomically updates
#       ship_started_at to the current timestamp. Missing file or parse
#       failure silently falls back to old behavior (no hard gate).
#       Mirrors the original HANDOFF STATE READ block (P2-5).
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
#       Calls skill_use("rdd-workflow-writing-plans") unless
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
#   - run_ship_phase1 <project_root> <change_name>
#       Thin orchestrator replacing the 30-line inline block at guide-ship.md
#       SKILL.md L116-L145. MUST be invoked on the SAME LINE as the `source`
#       of this file (AI platforms may split markdown bash blocks into
#       multiple bash processes; a separate call line would hit
#       "run_ship_phase1: command not found"). Sets globals MODE, WT_PATH,
#       PLAN_STEP_COUNT for downstream lines. Uses `return 1` (NOT `exit 1`)
#       on every failure — same lesson as plan_done_gate.sh's
#       PLAN_GATE_0_SKIPPED sentinel fix; exit would kill the AI host shell.
#
# Helpers required (provided by skills/_lib/worktree.sh):
#   - wt_path_for_branch <name>
#   - find_default_branch
#   - main_repo_root

# Guard against direct execution (sourced-only). Same pattern as
# skills/_lib/discover-arch-artifacts.sh L27-30 — uses [ not [[ to match
# the existing precedent. Direct execution produces a clear error instead
# of the cryptic "command not found" downstream callers would otherwise see.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "ERROR: ship_plan.sh defines bash functions only. Source it instead: source skills/guide-ship/scripts/ship_plan.sh" >&2
  exit 1
fi

# _LIB_DIR points to skills/_lib/ (shared library location)
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
_LIB_DIR="$(cd "$_SCRIPT_DIR/../../_lib" 2>/dev/null && pwd)"
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

# read_plan_handoff <project_root>
#   Phase 1 entry: read .rddf/state/.plan-handoff.json, display to user,
#   atomically update ship_started_at. Silent fallback on missing/parse error.
read_plan_handoff() {
  local project_root="$1"
  local handoff_file="$project_root/.rddf/state/.plan-handoff.json"

  if [ ! -f "$handoff_file" ]; then
    return 0
  fi

  echo "📋 Reading handoff state from plan-side..."
  cat "$handoff_file"
  echo ""

  PY_PROJECT_ROOT="$project_root" python3 -c '
import os, json, datetime, sys
try:
    p = os.path.join(os.environ["PY_PROJECT_ROOT"], ".rddf/state/.plan-handoff.json")
    with open(p) as f:
        data = json.load(f)
    data["ship_started_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
    print("✅ Handoff state updated: ship_started_at set")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"⚠️  Failed to update handoff: {e}", file=sys.stderr)
    sys.exit(0)
' 2>/dev/null
}

# detect_execution_mode <project_root> <change_name>
#   Priority (ADR-0023):
#     1. Read from .plan-handoff.json execution_mode_decisions[change_name] (deps analysis)
#     2. Fallback to parallel conflict detection (existing worktrees + total changes)
detect_execution_mode() {
  local project_root="$1"
  local change_name="$2"
  
  local handoff_file="$project_root/.rddf/state/.plan-handoff.json"
  local decision=""
  local reason=""
  
  if [ -f "$handoff_file" ]; then
    decision=$(PY_PROJECT_ROOT="$project_root" PY_CHANGE_NAME="$change_name" python3 -c '
import os, json
try:
    with open(os.environ["PY_PROJECT_ROOT"] + "/.rddf/state/.plan-handoff.json") as f:
        data = json.load(f)
    decisions = data.get("execution_mode_decisions", {})
    change = os.environ["PY_CHANGE_NAME"]
    if change in decisions:
        rec = decisions[change]
        print(rec.get("mode", ""))
except: pass
' 2>/dev/null)
    reason=$(PY_PROJECT_ROOT="$project_root" PY_CHANGE_NAME="$change_name" python3 -c '
import os, json
try:
    with open(os.environ["PY_PROJECT_ROOT"] + "/.rddf/state/.plan-handoff.json") as f:
        data = json.load(f)
    decisions = data.get("execution_mode_decisions", {})
    change = os.environ["PY_CHANGE_NAME"]
    if change in decisions:
        rec = decisions[change]
        print(rec.get("reason", ""))
except: pass
' 2>/dev/null)
  fi
  
  if [ -n "$decision" ]; then
    echo "$decision"
    echo "📋 deps 分析决策: $reason" >&2
    return 0
  fi
  
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
    if ! git -C "$project_root" checkout "openspec/$change_name" >/dev/null 2>&1; then
      echo "❌ 切换分支失败: openspec/$change_name" >&2
      return 1
    fi
    echo "⚡ 轻量模式: 已切换到 openspec/$change_name, 跳过 worktree" >&2 >&2
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

  if ! skill_use "rdd-workflow-writing-plans" 2>/dev/null; then
    echo "❌ 实施计划生成失败" >&2
    echo "   rdd-workflow-writing-plans 技能未找到,检查安装是否完整" >&2
    return 1
  fi

  local plan_file=".rddf/plans/$change_name.md"
  if [ ! -f "$plan_file" ]; then
    echo "❌ 计划文件缺失: $plan_file" >&2
    return 1
  fi

  local plan_task_count
  plan_task_count=$(grep -c '^### Task' "$plan_file" 2>/dev/null || true)
  local plan_step_count
  plan_step_count=$(grep -c '^- \[ \]' "$plan_file" 2>/dev/null || true)

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

# run_ship_phase1 <project_root> <change_name>
#   Thin orchestrator for guide-ship.md Phase 1 (was the 30-line inline
#   block at SKILL.md L116-L145). Call it on the SAME LINE as `source`
#   of this file:
#     source ".../ship_plan.sh" && run_ship_phase1 "$PROJECT_ROOT" "$CHANGE_NAME"
#   AI platforms may split markdown bash blocks into multiple bash
#   processes; a separate call line would hit "run_ship_phase1: command
#   not found".
#
#   Sets globals MODE / WT_PATH / PLAN_STEP_COUNT for downstream lines
#   in the same shell; echoes three capture-friendly summary lines.
#
#   All failures use `return 1`, NEVER `exit 1`: this file is sourced,
#   and `exit` would kill the AI host shell mid-workflow (same bug
#   class as the plan_done_gate.sh exit → PLAN_GATE_0_SKIPPED fix).
run_ship_phase1() {
  local project_root="$1"
  local change_name="$2"

  if [ -z "$project_root" ] || [ -z "$change_name" ]; then
    echo "❌ 用法: run_ship_phase1 <project_root> <change_name>" >&2
    return 1
  fi

  # 0) HANDOFF STATE READ (P2-5) - read .plan-handoff.json, update ship_started_at
  read_plan_handoff "$project_root"

  # 1) COMMIT GATE — return 1, NOT exit 1 (see header note)
  if ! check_artifacts_committed "$project_root" "$change_name"; then
    echo "请先 commit openspec/changes/$change_name/ 后重试" >&2
    return 1
  fi

  # 2) PARALLEL CONFLICT DETECTION → execution mode
  MODE=$(detect_execution_mode "$project_root" "$change_name") || return 1

  # 3) MODE-SPECIFIC SETUP + WORKTREE VERIFICATION GATE
  WT_PATH=$(setup_execution_workspace "$project_root" "$change_name" "$MODE") || return 1

  # 4) PLAN GENERATION (calls skill_use "rdd-workflow-writing-plans" internally;
  #    honors SKIP_PROMETHEUS_PLANNING=yes to write placeholder plan file)
  PLAN_STEP_COUNT=$(generate_implementation_plan "$project_root" "$change_name" "$MODE") || return 1

  # 5) iteration.json HOOK (status → in_worktree)
  record_iteration_status "$project_root" "$change_name" "$MODE" "$WT_PATH" "$PLAN_STEP_COUNT"

  # Globals for same-shell downstream lines; echo 3 lines as capture-friendly summary
  export MODE WT_PATH PLAN_STEP_COUNT
  echo "MODE=$MODE"
  echo "WT_PATH=$WT_PATH"
  echo "PLAN_STEP_COUNT=$PLAN_STEP_COUNT"
}

# detect_quick_finish <project_root> <change_name>
#   Returns: "quick_finish" (exit 0) if remaining tasks are trivial and ≤2,
#            "standard" (exit 0) otherwise,
#            "no_tasks" (exit 1) if tasks.md missing.
#   Trivial keywords: update, proposal, suggestion, doc, status, changelog,
#     readme, .md, bump, version, release, note.
#   Non-trivial keywords (any match blocks quick-finish): implement, add,
#     create, build, refactor, test, function, class, module, api, feature,
#     logic, handler, controller, schema, migration, script.
detect_quick_finish() {
  local project_root="$1"
  local change_name="$2"
  local tasks_file="$project_root/openspec/changes/$change_name/tasks.md"

  # Missing tasks.md -> no_tasks
  if [ ! -f "$tasks_file" ]; then
    echo "no_tasks"
    return 1
  fi

  # Collect remaining unchecked tasks
  local remaining
  remaining=$(grep -cE '^\- \[ \]' "$tasks_file" 2>/dev/null || echo 0)
  remaining=$(echo "$remaining" | tr -d '[:space:]')

  # 0 tasks or >2 tasks -> standard
  if [ "${remaining:-0}" -eq 0 ] || [ "${remaining:-0}" -gt 2 ]; then
    echo "standard"
    return 0
  fi

  # Extract the task text lines
  local task_text
  task_text=$(grep -E '^\- \[ \]' "$tasks_file")

  # Non-trivial keywords block quick-finish
  if echo "$task_text" | grep -qiE 'implement|add |create|build|refactor|test |function|class|module|api|feature|logic|handler|controller|schema|migration|script'; then
    echo "standard"
    return 0
  fi

  # Trivial keywords required (at least one)
  if ! echo "$task_text" | grep -qiE 'update|proposal|suggestion|doc|status|changelog|readme|\.md|bump|version|release|note'; then
    echo "standard"
    return 0
  fi

  # Check git status: no uncommitted code changes (exclude tasks.md)
  local dirty_code
  dirty_code=$(git -C "$project_root" status --porcelain 2>/dev/null | grep -vE 'tasks\.md$' | head -1)
  if [ -n "$dirty_code" ]; then
    echo "standard"
    return 0
  fi

  echo "quick_finish"
}