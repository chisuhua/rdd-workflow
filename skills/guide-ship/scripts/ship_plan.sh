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