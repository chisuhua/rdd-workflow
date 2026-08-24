# _lib/ship_review.sh
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
# Helpers required (provided by _lib/worktree.sh):
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

  # Create .rddf/improvements/<name>.md file (new format)
  local imp_dir="$project_root/.rddf/improvements"
  mkdir -p "$imp_dir"
  
  local imp_file="$imp_dir/${debt_name}.md"
  if [ ! -f "$imp_file" ]; then
    cat > "$imp_file" << EOF
# $debt_name

**优先级**: P2 | **来源**: execute review: $change_name
**阶段**: default | **分类**: arch-design
**类型**: debt

## 架构依据
- $change_name 执行后审查发现

## 范围
- **In Scope**: 见 TODO 扫描结果
- **Out Scope**: 已完成的功能

## 关键场景
- GIVEN 原有功能正常, WHEN 添加清理代码, THEN 不引入新问题

## 技术约束
- MUST NOT 影响已有功能
- SHOULD 保持代码风格一致

## 验收标准
- 新增测试通过
- 无回归
EOF
    echo "✅ 已创建 .rddf/improvements/${debt_name}.md"
  fi

  # Update proposal-suggestions.md index (Markdown table format)
  local suggestions_file="$project_root/proposal-suggestions.md"
  local timestamp=$(date -u +%Y-%m-%d)
  
  PY_PROJECT_ROOT="$project_root" python3 -c "
import os, re
try:
    sg_path = os.path.join(os.environ['PY_PROJECT_ROOT'], 'proposal-suggestions.md')
    debt_name = '$debt_name'
    timestamp = '$timestamp'
    
    # Read existing file or create header
    if os.path.isfile(sg_path):
        with open(sg_path) as f:
            content = f.read()
    else:
        content = '''# 提案池（待架构讨论）

> arch 阶段输入。guide-arch Phase 5.5 逐个审查，批准后添加到 \`proposal-approved.md\`。

| 提案 | 优先级 | 来源 | 添加时间 |
|------|--------|------|----------|
'''
    
    # Check if already in table
    if f'[{debt_name}]' in content:
        print(f'⚠️  {debt_name} 已在 proposal-suggestions.md 中')
    else:
        # Add new row after header
        lines = content.split('\n')
        insert_idx = -1
        for i, line in enumerate(lines):
            if '|---|' in line:
                insert_idx = i + 1
                break
        
        new_row = f'| [{debt_name}](.rddf/improvements/{debt_name}.md) | P2 | execute review | {timestamp} |'
        
        if insert_idx > 0:
            lines.insert(insert_idx, new_row)
        else:
            # Fallback: append at end
            lines.append(new_row)
        
        with open(sg_path, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f'✅ 已追加到 proposal-suggestions.md: {debt_name}')
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

# _review_debt_precommit_check <project_root> <change_name>
#   Phase 2.5 review debt check: runs BEFORE the aggregate commit.
#   Calls _lib/review_debt_checker.py to check for new TODOs without
#   a corresponding debt file. Exits 1 if TODOs found and no debt file.
_review_debt_precommit_check() {
  local project_root="$1"
  local change_name="$2"
  local execute_finished_at
  execute_finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  RDDF_PROJECT_ROOT="$project_root" \
  RDDF_CHANGE_NAME="$change_name" \
  RDDF_EXECUTE_FINISHED_AT="$execute_finished_at" \
  python3 -c "
import os, sys, datetime
sys.path.insert(0, os.environ.get('RDDF_EXECUTION_ROOT', '.'))
from review_debt_checker import check_review_debt_recorded
project_root = os.environ['RDDF_PROJECT_ROOT']
change_name = os.environ['RDDF_CHANGE_NAME']
finish_at = datetime.datetime.fromisoformat(
    os.environ['RDDF_EXECUTE_FINISHED_AT'].replace('Z', '+00:00')
)
verdict = check_review_debt_recorded(project_root, change_name, finish_at)
print(f'verdict: persisted={verdict.persisted} count={verdict.found_count}')
print(f'reason: {verdict.reason}')
if not verdict.persisted and verdict.found_count > 0:
    sys.exit(1)
"
}

# Full regression gate (add-full-regression-gate)
full_regression_gate() {
  local project_root="$1"
  if [ "${SKIP_REGRESSION:-}" = "1" ]; then
    echo "⚠️  已跳过回归门 (SKIP_REGRESSION=1)"
    return 0
  fi
  local build_dir="$project_root/build"
  if [ ! -d "$build_dir" ]; then
    echo "⚠️  无构建目录，跳过回归门"
    return 0
  fi
  if ctest --test-dir "$build_dir" --output-on-failure; then
    echo "✅ 全量回归通过"
    return 0
  fi
  echo ""
  echo "❌ 全量回归失败。请选择:"
  echo "1. 返回 execute 修复问题"
  echo "2. 创建 debt change 跟踪"
  echo "3. SKIP_REGRESSION=1 强制跳过"
  return 1
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