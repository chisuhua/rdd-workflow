#!/usr/bin/env bash
# skills/_lib/ship_monitor.sh
# Phase 2 progress monitor from guide-ship.md extracted into a reusable helper.
# Was ~54-line inline bash block at L260-L315 reading progress across all
# openspec/* branches (worktree + lightweight modes).
#
# Functions exported:
#   - run_ship_monitor()
#       Lists openspec/* worktree branches via 'git worktree list --porcelain'.
#       For each worktree: reads tasks.md progress (done/total).
#       Also enumerates openspec/* branches NOT in worktree list (lightweight).
#       Marks current branch as 轻量(当前).
#       Prints formatted 'name → done/total [mode]'.
#       Uses mapfile with bash < 4.0 fallback.

run_ship_monitor() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  echo "📋 所有 Changes 实际进度:"

  local LAST_CHECK
  LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

  # 收集所有活跃的 openspec/* 分支（含 worktree 和轻量模式）
  # 从 worktree 列表获取
  local -a wt_list=()
  if command -v mapfile >/dev/null 2>&1; then
    mapfile -t wt_list < <(git worktree list --porcelain \
      | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}' 2>/dev/null)
  else
    # bash < 4.0 fallback
    while IFS= read -r line; do
      [ -n "$line" ] && wt_list+=("$line")
    done < <(git worktree list --porcelain \
      | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}' 2>/dev/null)
  fi

  local wt branch name tasks_file total done progress mode
  for wt in "${wt_list[@]}"; do
      branch=$(git worktree list | grep -F "$wt" | awk '{print $3}')
      [ -z "$branch" ] && continue
      name=$(echo "$branch" | sed 's|openspec/||')
      tasks_file="$wt/openspec/changes/$name/tasks.md"
      mode="worktree"
      if [ -f "$tasks_file" ]; then
          total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null | head -n1 || echo 0)
          done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null | head -n1 || echo 0)
          progress="${done}/${total}"
      else
          progress="? (文件不存在)"
      fi
      echo "  $name → $progress [$mode]"
  done

  # 补充轻量模式（有 openspec/ 分支但不在 worktree 列表中的）
  if git branch | grep -q "openspec/"; then
      local branch_name in_wt wt_branch CURRENT_BRANCH
      for branch_name in $(git branch | grep "openspec/" | sed 's/.*openspec\///'); do
          in_wt=false
          for wt in "${wt_list[@]:-}"; do
              wt_branch=$(git worktree list | grep -F "$wt" | awk '{print $3}' | sed 's|openspec/||')
              [ "$wt_branch" = "$branch_name" ] && in_wt=true && break
          done
          $in_wt && continue

          tasks_file="$PROJECT_ROOT/openspec/changes/$branch_name/tasks.md"
          CURRENT_BRANCH=$(git branch --show-current)
          if [ "$CURRENT_BRANCH" = "openspec/$branch_name" ]; then
              mode="轻量(当前)"
          else
              mode="轻量"
          fi
          if [ -f "$tasks_file" ]; then
              total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null | head -n1 || echo 0)
              done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null | head -n1 || echo 0)
              progress="${done}/${total}"
          else
              progress="? (文件不存在)"
          fi
          echo "  $branch_name → $progress [$mode]"
      done
  fi

  echo ""
  echo "上次检测: $LAST_CHECK"
}