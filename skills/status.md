---
name: status
description: 查看 OpenSpec change 状态、归档已完成的 change、清理 worktree 和 branch。可被 guide-ship 调用（archive 阶段），也可独立调用查看状态。
license: MIT
compatibility: Requires openspec CLI
metadata:
  version: "2.0"
  author: sisyphus
  version: "2.0.2"  # v2.0.2: planned 状态展示 (Mode A + Mode E)
---

# OpenSpec 工作流 — Status

提供四种工作模式：状态概览、检测与修复、归档完成、路线图状态。

## 工作流位置

```
Mode A: 全局概览 — 无需参数，列出所有 change + worktree
Mode B: 检测修复 — 检查具体 change 的完成状态和同步问题
Mode C: 归档完成 — change 完成后 merge → archive → cleanup
Mode D: 路线图状态 — 查看 roadmap 阶段进度和阶段门控
Mode E: 当前迭代 — 列出当前 sprint 的所有 change (状态/阻塞/进度)
```

## 输入

- 无参数 → Mode A（全局概览）
- change name → Mode B（单 change 详情 + 同步检测）
- change name + 明确要求归档 → Mode C（归档流程）
- `--roadmap` 或 `roadmap` → Mode D（路线图状态）
- `--iteration` 或 `iteration` → Mode E（当前迭代）

## 工作目录检测（所有模式通用）

```bash
# Source helper (worktree-aware functions)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/worktree.sh" ]; then
  source "$SCRIPT_DIR/_lib/worktree.sh"
fi
```

```bash
# 自动检测项目根目录（用于全局安装的技能）
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# 确定当前 git 上下文
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")

# 获取 worktree 列表
WORKTREE_LIST=$(git worktree list)
echo "当前分支: $CURRENT_BRANCH"
echo "Worktree 列表:"
echo "$WORKTREE_LIST"

# 判断是否在 worktree 内
IN_WORKTREE=false
WORKTREE_PATH=""
if echo "$CURRENT_BRANCH" | grep -q '^openspec/'; then
    IN_WORKTREE=true
    WORKTREE_PATH=$(pwd)
    CHANGE_NAME=$(echo "$CURRENT_BRANCH" | sed 's/^openspec\///')
fi
```

---

## 模式 A：状态概览

### Step 1：获取 worktree 列表

```bash
git worktree list
```

输出示例：
```
/path/to/PROJECT_ROOT                    master
/path/to/PROJECT_ROOT/.rddf/wt/add-uart   openspec/add-uart
/path/to/PROJECT_ROOT/.rddf/wt/fix-spi    openspec/fix-spi
```

### Step 2：获取 openspec 列表

```bash
openspec list
```

提取 active changes 及其进度。

### Step 3：获取每个 active change 的进度

```bash
for each active_change:
    openspec instructions apply --change "<name>" --json
    # 解析 progress.complete, progress.total, state
```

```bash
# v2.0.2: Planned (skeleton) changes don't have apply progress.
# For planned changes, skip the progress fetch and display 0/0.
```

对比 worktree 分支名与 change 名称，建立映射。

### Step 4：输出概览表格

```
OpenSpec 工作流状态概览
=======================
（若无 worktree → 显示 "当前无活跃 worktree"）

Change          │ Worktree              │ 进度        │ 状态
──────────────────────────────────────────────────────────────
add-uart        │ .rddf/wt/add-uart      │ 3/7  (43%)  │ 🔄 执行中
fix-spi         │ .rddf/wt/fix-spi       │ 6/6  (100%) │ ✅ 可归档
pending-change  │ （无 worktree）        │ 2/5  (40%)  │ ⏸ 暂停
──────────────────────────────────────────────────────────────

请选择要执行的操作（输入编号）：
  1. 查看 add-uart 详情（检测同步问题）
  2. 查看 fix-spi 详情（检测同步问题）
  3. 归档 fix-spi（已完成）
  4. ↩️ 返回 Execute 阶段
  i. 其他输入
```

**动态状态展示（v2.0.2）**：

```bash
for each active_change:
    status=$(python3 -c "
import json
try:
    d = json.load(open('.rddf/state/iteration.json'))
    c = next((c for c in d.get('changes', []) if c.get('name') == '$active_change'), None)
    if c:
        print(c.get('status', 'unknown'))
    else:
        print('unknown')
except Exception:
    print('unknown')
" 2>/dev/null)
    case "$status" in
      planned) echo "📋 $active_change: planned (skeleton)" ;;
      proposed) echo "✅ $active_change: proposed (ready)" ;;
      in_worktree) echo "🔧 $active_change: in worktree" ;;
      completed) echo "✓ $active_change: completed" ;;
      archived) echo "📦 $active_change: archived" ;;
      *) echo "❓ $active_change: $status" ;;
    esac
```

**用户输入处理（case handler）**：

当用户输入不在上述有效选项内时，按以下 case 分支处理：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新展示菜单
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

**Mode A 职责说明**：此模式仅做状态概览，不执行问题检测。问题检测由 Mode B 专门负责。

---

## 模式 B：检测与修复

### Step 1：获取基本信息

```bash
# 阶段检测：先检查是否已 plan
PLAN_FILE=".rddf/plans/<name>.md"
if [ ! -f "$PLAN_FILE" ]; then
    echo "⏳ Change <name> 已 propose 但尚未 plan"
    echo "   请先执行: skill_use(\"guide-ship\")   # 内部选择 <name>"
    exit 0
fi

# 获取 change 状态
APPLY=$(openspec instructions apply --change "<name>" --json)
STATE=$(echo "$APPLY" | jq -r '.state')
COMPLETE=$(echo "$APPLY" | jq '.progress.complete')
TOTAL=$(echo "$APPLY" | jq '.progress.total')
# 验证数字有效性后再进行算术运算
if [[ "$COMPLETE" =~ ^[0-9]+$ ]] && [[ "$TOTAL" =~ ^[0-9]+$ ]] && [ "$TOTAL" -gt 0 ]; then
    REMAINING=$((TOTAL - COMPLETE))
else
    REMAINING=0
fi

# P0-7 fix: inline worktree path resolver with bracket-aware branch column lookup.
# git worktree list emits `path  hash  [branch]` — third column is the
# bracketed branch name. The earlier shell helper used commit-hash
# comparison which never matched; the inline version compares against
# the literal bracket form using awk with an explicit string variable.
wt_path_for_branch_inline() {
    local branch="$1"
    git worktree list 2>/dev/null | awk -v br="\[openspec/\$branch\]" '$3 == br {print $1; exit}'
}
# 通过 git worktree list 动态查找 worktree 路径（不硬编码 $PROJECT_ROOT/.rddf/wt/<name>）
# P0-7: 使用内联 helper 而非 _lib/worktree.sh — 内联版本处理 bracket column 索引
WORKTREE_PATH=$(wt_path_for_branch_inline "<name>")
HAS_WORKTREE=false
if [ -n "$WORKTREE_PATH" ] && [ -d "$WORKTREE_PATH" ]; then
    HAS_WORKTREE=true
    # 使用 subshell 获取 worktree 内状态，不改变当前目录
    WT_BRANCH=$(cd "$WORKTREE_PATH" && git branch --show-current)
    WT_DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | grep -c . || true)
fi
```

### Step 2：三类问题检测

#### 问题类型一：不同步（tasks.md 与实际完成状态不一致）

```bash
# 方法：对比 openspec CLI progress 与计划文件中的实际完成标记
# CLI progress 来源于 tasks.md 的 [x] 计数
# .rddf/plans/ 中的 [x] 标记是 Prometheus 执行的实际完成状态

PLAN_FILE=".rddf/plans/<name>.md"
TASKS_FILE="$PROJECT_ROOT/openspec/changes/<name>/tasks.md"

# 如果 plan 文件存在，检查其 [x] 计数
PLAN_DONE=0
if [ -f "$PLAN_FILE" ]; then
    PLAN_DONE=$(grep -c "\- \[x\]" "$PLAN_FILE" 2>/dev/null || echo 0)
fi

# tasks.md 的 [x] 计数
TASKS_DONE=$(grep -c "\- \[x\]" "$TASKS_FILE" 2>/dev/null || echo 0)

if [ "$PLAN_DONE" -gt "$TASKS_DONE" ]; then
    echo "⚠️ 不同步: Prometheus 已完成 $PLAN_DONE 个单元，但 tasks.md 只标记了 $TASKS_DONE 个"
    echo "修复: 同步 tasks.md 以匹配实际完成状态"
fi
```

#### 问题类型二：worktree 有未提交更改

```bash
if [ "$HAS_WORKTREE" = true ] && [ "$WT_DIRTY" -gt 0 ]; then
    echo "⚠️ Worktree 有 $WT_DIRTY 个未提交文件"
    git status --short
fi
```

#### 问题类型三：worktree 分支落后于默认分支

```bash
if [ "$HAS_WORKTREE" = true ]; then
    # 动态检测默认分支（不硬编码 main/master）
    DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@' || echo "main")
    MERGE_BASE=$(git merge-base "openspec/<name>" "$DEFAULT_BRANCH" 2>/dev/null)
    MAIN_TIP=$(git rev-parse "$DEFAULT_BRANCH" 2>/dev/null)
    if [ "$MERGE_BASE" != "$MAIN_TIP" ]; then
        echo "⚠️ Worktree 分支落后于 $DEFAULT_BRANCH（创建后有新 commit 进入默认分支）"
    fi
fi
```

### Step 3：不同步修复

**核心原则**：不同步修复通过 `sed` 直接修改 tasks.md，**不重新执行 plan**。

```bash
# 场景 A：Prometheus 已完成但 tasks.md 未标记
# 使用 awk index() 进行字面量匹配（避免正则元字符风险）
TASK_DESC="具体任务描述"
TMPFILE=$(mktemp -t status_tasks_XXXXXX.md)
awk -v desc="- [ ] $TASK_DESC" -v repl="- [x] $TASK_DESC" '
  index($0, desc) { sub(desc, repl); changed=1 }
  { print }
  END { exit (changed ? 0 : 1) }
' $PROJECT_ROOT/openspec/changes/<name>/tasks.md > "$TMPFILE" && \
  mv "$TMPFILE" $PROJECT_ROOT/openspec/changes/<name>/tasks.md || {
    echo "⚠️  未找到匹配的任务描述: $TASK_DESC"
    rm -f "$TMPFILE"
  }

# 场景 B：tasks.md 标记完成但实际代码未提交
# 提示先 git commit
echo "⚠️ tasks.md 标记完成但 worktree 有未提交代码"
echo "请先提交代码更改，或确认更改是否完整"
```

### Step 4：输出检测报告

```
Change: <name>
───────────────
进度: 3/7 (43%)
状态: 执行中
Worktree: .rddf/wt/<name>

问题:
  ⚠️ tasks.md 不同步 — Prometheus 已完成 5 个单元，tasks.md 只标记了 3 个
  修复: sed -i 's/- \[ \] 任务描述/- [x] 任务描述/' tasks.md

建议:
  - skill_use("execute") 继续执行
  - 或修复同步后归档
```

### Step 5：完成判定

如果所有 tasks.md 的 `[ ]` 都已标记为 `[x]`，且 `openspec status` 显示 `state=all_done`：

```
✅ Change <name> 全部完成！

建议立即归档:
  skill_use("status <name> --archive")
```

---

## 模式 C：归档完成

### 前置条件：确认全部完成

```bash
APPLY=$(openspec instructions apply --change "<name>" --json)
STATE=$(echo "$APPLY" | jq -r '.state')
COMPLETE=$(echo "$APPLY" | jq '.progress.complete')
TOTAL=$(echo "$APPLY" | jq '.progress.total')

if [ "$COMPLETE" -ne "$TOTAL" ]; then
    echo "❌ 未全部完成 ($COMPLETE/$TOTAL)，不能归档"
    echo "请先执行剩余的 Work Unit"
    exit 1
fi
```

### Step 1-5：执行归档（提取到 `_lib/archive.sh`，P1-14 去重）

```bash
# P1-14: archive 流程（worktree 查找 → 脏检查 → merge → archive → cleanup）
# 提取到 skills/_lib/archive.sh,与 guide-ship.md Phase 3 共享同一份实现。
# 源文件: skills/_lib/archive.sh::archive_change
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/archive.sh" ]; then
  source "$SCRIPT_DIR/_lib/archive.sh"
fi

archive_change "<name>"
```

> **重构说明（P1-14）**：
> - 旧的 Step 1-5（worktree 定位、脏检查、merge、archive、cleanup）已合并为单次 `archive_change` 调用。
> - 共享 helper 包含 3 个原子函数：`check_worktree_commits`（T20 pre-merge check）、
>   `verify_merge_result`（post-merge 校验）、`archive_change`（端到端编排）。
> - 当 `archive_change` 内部已经走完 dirty-check + pre-merge check + merge + verify +
>   `openspec archive` + worktree/branch cleanup，调用方不再需要重复这些步骤。
> - 详细语义见 `skills/_lib/archive.sh` 顶部注释。

### Step 6：输出归档报告 + 循环检查

```
🎉 Change <name> 归档完成

已完成:
  ✅ Merge: openspec/<name> → ${DEFAULT_BRANCH:-master}
  ✅ Archive: openspec/changes/archive/<date>-<name>/
  ✅ Cleanup: worktree + branch 已删除

过程:
  - ccache 加速构建
  - 所有 Work Unit 完成
  - merge 方式: fast-forward / merge commit
```

**归档后循环检查**（与 guide 的 status_archive 阶段保持一致）：

```bash
# 检查是否还有其他 worktree（$2 是 commit hash, $3 是 "[branch]"; regex 需含前导 `[`）
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\// {print $1}' | grep -c . || true)
if [ "$REMAINING_WT" -gt 0 ]; then
    echo ""
    echo "📋 还有 $REMAINING_WT 个 worktree 正在进行"
    echo "请选择:"
    echo "1. 继续处理其他 worktree"
    echo "2. 返回 guide: skill_use(\"guide\")"
else
    # 检查 proposal-suggestions.md
    # P1-7: 文件格式已规范化为 JSON 列表
    #       用 json.load 解析后统计 status == "待创建" 的条目数
    if [ -f "proposal-suggestions.md" ]; then
        REMAINING=$(python3 -c "
import json, sys
try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print(0)
        sys.exit(0)
    count = sum(1 for e in entries if isinstance(e, dict) and e.get('status') == '待创建')
    print(count)
except (FileNotFoundError, json.JSONDecodeError):
    print(0)
" 2>/dev/null)
        REMAINING=${REMAINING:-0}
        if [ "$REMAINING" -gt 0 ]; then
            echo ""
            echo "📋 proposal-suggestions.md 中还有 $REMAINING 个未创建的 change"
            echo "建议运行: skill_use(\"guide\") 回到 propose 阶段"
        fi
    fi
fi
```

---

## Mode D：路线图状态

### 入口条件

用户传入 `--roadmap` 或 `roadmap` 参数，或无参数但项目存在 `roadmap.md`。

### 展示内容

```bash
if [ "$MODE" = "roadmap" ] || ([ -z "$MODE" ] && [ -f "$PROJECT_ROOT/roadmap.md" ]); then
    echo "📊 路线图状态"
    echo "=============="
    
    # 读取 roadmap
    if [ -f "$PROJECT_ROOT/roadmap.md" ]; then
        CURRENT_PHASE=$(python3 -c "
import re
with open('$PROJECT_ROOT/roadmap.md') as f:
    content = f.read()
phase_match = re.search(r'\*\*当前阶段\*\*:\s*(\S+)', content)
print(phase_match.group(1) if phase_match else 'unknown')
")
        echo "当前阶段: $CURRENT_PHASE"
    fi
    
    # 读取状态
    if [ -f "$PROJECT_ROOT/.rddf/state/roadmap-state.json" ]; then
        python3 -c "
import json
with open('$PROJECT_ROOT/.rddf/state/roadmap-state.json') as f:
    state = json.load(f)

print('')
print('阶段进度:')
for phase_id, phase_data in state.get('phases', {}).items():
    status = phase_data.get('status', 'unknown')
    status_icon = {'completed': '✅', 'in_progress': '🔄', 'pending': '⏳'}.get(status, '❓')
    
    total = sum(len(c.get('changes', [])) for c in phase_data.get('categories', {}).values())
    completed = sum(len(c.get('completed_changes', [])) for c in phase_data.get('categories', {}).values())
    
    print(f'{status_icon} {phase_id}: {completed}/{total} change 完成')
    
    # 分类详情
    for cat_id, cat_data in phase_data.get('categories', {}).items():
        cat_total = len(cat_data.get('changes', []))
        cat_completed = len(cat_data.get('completed_changes', []))
        if cat_total > 0:
            print(f'   - {cat_id}: {cat_completed}/{cat_total}')

# 当前阶段门控
if 'current_phase' in state:
    phase = state['current_phase']
    if phase in state.get('phases', {}):
        gate = state['phases'][phase].get('gate_status', {})
        print('')
        print('阶段门控:')
        print(f'  所有 change 完成: {\"✅\" if gate.get(\"all_changes_complete\") else \"❌\"}')
        for check, checked in gate.get('checklist', {}).items():
            print(f'  {check}: {\"✅\" if checked else \"❌\"}')
"
    fi
    
    echo ""
    echo "操作选项:"
    echo "1. 生成阶段门控报告"
    echo "2. 推进到下一阶段（如满足条件）"
        echo "3. 查看详细 change 列表"
        echo "i. 其他输入"
fi
```

**用户输入处理（case handler）**：

当用户输入不在上述有效选项内时，按以下 case 分支处理：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新展示菜单
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

---

## 模式 E：当前迭代（v2.0 新增）

读取 `.rddf/state/iteration.json` 渲染当前 sprint 视图，列出**所有 active change** 的状态、阻塞关系、任务进度、计划文件路径。供 `propose → guide-ship → execute → archive` 流程中的快速概览。

### Step 1：读取 iteration.json

```bash
ITERATION_FILE="$PROJECT_ROOT/.rddf/state/iteration.json"

if [ ! -f "$ITERATION_FILE" ]; then
    echo "📭 iteration.json 不存在"
    echo "   说明: 尚未运行过 propose (roadmap 模式)"
    echo "   初始化: skill_use(\"propose\", \"<name>\")"
    exit 0
fi
```

### Step 2：渲染当前迭代表

```bash
# v2.0.2 安全修复: bash 变量通过环境变量传递 (os.environ),
# 不用 '$VAR' 直接拼到 Python 源码. 避免单引号路径/注入风险.
PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, sys
from datetime import datetime, timezone

try:
    from skills._lib import iteration as it_mod
except ImportError as e:
    print(f"❌ iteration 模块不可用: {e}")
    sys.exit(1)

data = it_mod.load(os.environ["PROJECT_ROOT"])
phase = data.get("current_phase", "default")
updated_at = data.get("updated_at", "")

# 渲染头
print("📊 当前迭代视图")
print(f"   Phase: {phase}    Updated: {updated_at}")
print(f"   活跃: {sum(1 for c in data[\"changes\"] if c[\"status\"] in (\"proposed\", \"in_worktree\", \"completed\"))} | 已归档: {sum(1 for c in data[\"changes\"] if c[\"status\"] == \"archived\")}")
print()

active = [c for c in data["changes"] if c["status"] in ("proposed", "in_worktree", "completed")]
if not active:
    print("  (无 active change)")
else:
    print("| Feature | Change | Phase | Cat | Status | Blocker | Group | Conflicts | Tasks | Plan |")
    print("|---------|--------|-------|-----|--------|---------|-------|-----------|-------|------|")
    for c in active:
        feature = it_mod.derive_feature_name(c["name"])
        status_icon = {"proposed": "📋", "in_worktree": "🔄", "completed": "✅"}.get(c["status"], "?")
        blocker = c.get("blocker") or "—"
        group = str(c.get("parallel_group", "—"))
        conflicts = ",".join(c.get("conflicts", [])) or "—"
        done = c.get("tasks_done", 0)
        total = c.get("tasks_total", 0)
        tasks = f"{done}/{total}" if total else "—"
        plan = "✅" if c.get("plan_path") else "—"
        print(f"| {feature} | {c[\"name\"]} | {c.get(\"phase\", \"—\")[:8]} | {(c.get(\"category\") or \"—\")[:10]} | {status_icon} {c[\"status\"]} | {blocker} | {group} | {conflicts} | {tasks} | {plan} |")
    print()

# 渲染已归档段
archived = it_mod.list_archived(data)
if archived:
    print("🗄️  最近归档 (top 5):")
    for c in archived[:5]:
        print(f"   ✅ {c[\"name\"]}  ({c.get(\"archived_at\", \"\")})")
    if len(archived) > 5:
        print(f"   ... (共 {len(archived)} 个归档)")
    print()

# 漂移提示
stale = [c for c in active if c.get("last_deps_at")]
now = datetime.now(timezone.utc)
for c in stale:
    last = datetime.fromisoformat(c["last_deps_at"].replace("Z", "+00:00"))
    age_hours = (now - last).total_seconds() / 3600
    if age_hours > 24:
        print(f"⚠️  {c[\"name\"]}: deps 信息已 {age_hours:.0f}h 未更新, 建议重跑 deps")
'
```

### Step 2b (v2.0.2): 显示 planned 状态 change

```bash
PLANNED_LIST=$(python3 -c "
import json, os
p = '.rddf/state/iteration.json'
if not os.path.isfile(p):
    print('(no iteration.json)')
else:
    try:
        d = json.load(open(p))
    except Exception as e:
        print(f'(parse error: {e})')
        exit()
    planned = [c for c in d.get('changes', []) if c.get('status') == 'planned']
    if not planned:
        print('(none)')
    else:
        for c in planned:
            blocker = c.get('blocker', '')
            blocker_str = f' (blocked by {blocker})' if blocker else ''
            print(f\"  📋 {c['name']}{blocker_str}\")
" 2>/dev/null)
if [ -n "$PLANNED_LIST" ]; then
    echo ""
    echo "📋 Planned (skeleton) changes:"
    echo "$PLANNED_LIST"
fi
```

### Step 3：用户操作

```
请选择:
1. 🔄 刷新视图 (重新读取 iteration.json)
2. 🚀 进入 guide-ship (处理 active change)
3. 📊 查看完整依赖图 (.rddf/state/deps-output.md)
4. ↩️ 返回主菜单
i. 其他输入
```

**用户输入处理**：

```bash
case "$choice" in
  1) exec $0 --iteration ;;  # 重新进入 Mode E
  2) skill_use("guide-ship") ;;
  3) [ -f "$PROJECT_ROOT/.rddf/state/deps-output.md" ] && cat "$PROJECT_ROOT/.rddf/state/deps-output.md" ;;
  4) exec $0 ;;  # 返回 Mode A
  q|quit) exit 0 ;;
  *) echo "❌ 无效输入 '$choice'" ;;
esac
```

**Mode E 职责说明**：此模式仅做当前 sprint 视图渲染，不修改任何文件。如需更新 iteration 字段（tasks_done 等），由 execute/archive/propose 钩子自动维护。

---

## 关键约束

1. **归档前必须先 merge**：确保代码变更已合入 default branch（`master`/`main`/`develop`，由 `find_default_branch` 动态检测）
2. **不同步用 sed 修复**：**不重跑 plan**（会覆盖 `.rddf/plans/` 中的任务分解细节）
3. **所有操作可从主仓库 TUI session 完成**：通过 `workdir` 参数在 worktree 内执行
4. **归档不可逆**：确认全部完成后再执行模式 C
5. **Roadmap 状态自动更新**：execute 完成后自动更新 .roadmap-state.json
