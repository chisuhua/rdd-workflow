---
name: status
description: 查看 OpenSpec change 状态、归档已完成的 change、清理 worktree 和 branch。可被 guide-ship 调用（archive 阶段），也可独立调用查看状态。
license: MIT
compatibility: Requires openspec CLI
metadata:
  version: "2.0.2"  # source-of-truth (latest semver)
  author: sisyphus
  evolved-from: "status.md v1.x; v2.0.2 added planned 状态展示 (Mode A + Mode E)"
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

## 输入 + 顶层路由（NEW in v2.0.3，对应 S8）

| 输入 | Mode | 备注 |
|------|------|------|
| 无参数 / `status` | Mode A | 全局概览 |
| `<change-name>` | Mode B | 单 change 详情 + 同步检测 |
| `<change-name> --archive` / `--yes` | Mode C | 归档（强制确认 gate 由 1.3 引入） |
| `--roadmap` / `roadmap` | Mode D | 路线图状态 |
| `--iteration` / `iteration` | Mode E | 当前迭代视图 |
| `--help` / `-h` / `?` | （帮助） | 列出 5 个 mode + 用法 |

**路由实现**：

```bash
status_router() {
  case "$1" in
    "")                                echo "A" ;;
    --roadmap|roadmap)                 echo "D" ;;
    --iteration|iteration)             echo "E" ;;
    --help|-h|help|\?)                 echo "help" ;;
    --archive|--yes|-y)                echo "C" ;;
    *)                                 echo "B:$1" ;;           # 视为 change name
  esac
}
```

## 工作目录检测（所有模式通用）

```bash
# 工作目录检测（所有模式通用）
# 注（v2.0.3）：原 dead-source `_lib/worktree.sh` 已移除（S5）。
# Mode B 内联使用 `wt_path_for_branch_inline`（P0-7）作为唯一来源。
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
add-uart        │ .rddf/wt/add-uart      │ 3/7  (43%)  │ 🔧 in_worktree
fix-spi         │ .rddf/wt/fix-spi       │ 6/6  (100%) │ ✔ completed
pending-change  │ （无 worktree）        │ 2/5  (40%)  │ 💼 committed
──────────────────────────────────────────────────────────────

请选择要执行的操作（输入编号）：
  1. 查看 add-uart 详情（检测同步问题）
  2. 查看 fix-spi 详情（检测同步问题）
  3. 归档 fix-spi（已完成）
  4. ↩️ 返回 Execute 阶段
  i. 其他输入
```

**Status rendering（v2.0.3，从 iteration.json 派生单一真理源）**：

```bash
# Status rendering extracted to scripts/status_render_mode_a.sh (Round B Task B6).
# Single-import helper for Mode A change status display.
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/status_render_mode_a.sh"

# Usage: render_status_mode_a <change-name>
# The helper queries iteration.json (primary) with filesystem fallback
# and returns an emoji + status label string, e.g.:
#   status=$(render_status_mode_a "my-change")
```

**单一真理源规则**：Mode A 的状态列**只**从 iteration.json 读取；filesystem-only fallback 仅在 iteration.json 缺失时触发。禁止在表格或 case 分支里硬编码状态文字。

**用户输入处理（case handler）**：

当用户输入不在上述有效选项内时，调用共享菜单处理器处理（extracted to scripts/status_archive_menu.sh）：

```bash
# Mode A status overview menu - shared handler (extracted from inline case block)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/status_archive_menu.sh"
handle_status_archive_menu "$choice"
[ $? -eq 2 ] && continue  # r|refresh -> 重新展示菜单
```

**Mode A 职责说明**：此模式仅做状态概览，不执行问题检测。问题检测由 Mode B 专门负责。

---

## 模式 B：检测与修复

### Step 1：获取基本信息

```bash
# 阶段检测：先检查是否已 plan
PLAN_FILE="$PROJECT_ROOT/.rddf/plans/<name>.md"
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
# P3-3c: 使用 _lib/worktree.sh::wt_path_for_branch 替代 P0-7 内联版本 (修复 silent bug)
# P0-7 引入的内联 helper 因 awk 字符串比较中 '\\[' 与 '[' 不匹配而永远返回空,
# 导致 HAS_WORKTREE 永远为 false. _lib/worktree.sh 用 porcelain 格式 + kv 解析, 工作正常.
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/worktree.sh"
WORKTREE_PATH=$(wt_path_for_branch "<name>")
    HAS_WORKTREE=true
    # 使用 subshell 获取 worktree 内状态，不改变当前目录
    WT_BRANCH=$(cd "$WORKTREE_PATH" && git branch --show-current)
    WT_DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | grep -c . || true)
fi
```

### Step 2：三类问题检测

检测逻辑已抽取到 `skills/_lib/status_helpers.sh::detect_sync_issues` (单入口、三类问题统一报告)。
status.md 只保留 prose 解释 + 1 行调用,确保 AI 助手有可执行规约可循。

```bash
# Mode B Step 2: 三类问题检测（已抽取到 _lib/status_helpers.sh）
#   detect_sync_issues <project_root> <name> <has_worktree> <wt_dirty>
#   返回 0 表示发现至少一个问题,1 表示全部正常。
#   HAS_WORKTREE (1/0) 与 WT_DIRTY (n) 由 Step 1 计算后传入。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/../_lib/status_helpers.sh" ]; then
  source "$SCRIPT_DIR/../_lib/status_helpers.sh"
fi

detect_sync_issues "$PROJECT_ROOT" "<name>" "$HAS_WORKTREE" "$WT_DIRTY"
```

**三类问题语义**:

| # | 触发条件 | 含义 | 处理 |
|---|---|---|---|
| 1 | `PLAN_DONE > TASKS_DONE` | Prometheus 已完成 N 个单元,但 tasks.md 只标记了 M < N 个 | 跑 Step 3 修复 tasks.md |
| 2 | `HAS_WORKTREE=1 && WT_DIRTY>0` | worktree 有未提交文件 | 先 `git commit` 再继续 |
| 3 | `merge_base != main_tip` | worktree 分支落后默认分支 | 重新基于默认分支 rebase 或 merge |

### Step 3：不同步修复

**核心原则**：不同步修复通过 `sed` 直接修改 tasks.md，**不重新执行 plan**。

修复逻辑已抽取到 `skills/_lib/status_helpers.sh::repair_sync_state` (awk `index()` 字面量匹配,避免正则元字符风险)。

```bash
# Mode B Step 3: 不同步修复（已抽取到 _lib/status_helpers.sh）
#   repair_sync_state <project_root> <name> "<task_description>"
#   找到首个 "- [ ] <task>" 替换为 "- [x] <task>",返回 0 表示成功。

repair_sync_state "$PROJECT_ROOT" "<name>" "<具体任务描述>"
```

**场景 B 处理** (tasks.md 标记完成但 worktree 有未提交代码): 这是用户责任,AI 助手应提示 `git commit` 或确认更改完整性 — 不能由 helper 静默处理。

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

### Step 0：用户确认 gate（NEW in v2.0.3，对应 S7 + 关键约束 #4 "归档不可逆"）

```bash
# 必填：强制 y/n 确认。若传入 --yes/-y 则跳过交互（CI 用法）。
case "${1:-}" in
  --yes|-y) CONFIRMED=yes ;;
  *) CONFIRMED=no ;;
esac

if [ "$CONFIRMED" = "no" ]; then
  echo "⚠️  即将归档 change <name>。此操作不可逆（merge → archive → cleanup）。"
  echo -n "   输入 'yes' 确认,其他任意输入取消: "
  read -r REPLY
  case "$REPLY" in
    yes|YES|y|Y) CONFIRMED=yes ;;
    *) echo "❌ 已取消归档"; exit 1 ;;
  esac
fi
[ "$CONFIRMED" = "yes" ] || { echo "❌ 未确认"; exit 1; }
```

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
if [ -f "$SCRIPT_DIR/../_lib/archive.sh" ]; then
  source "$SCRIPT_DIR/../_lib/archive.sh"
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
# P1-PIN: git worktree list 输出 "path  hash  [branch]" — $1=path, $2=commit hash, $3="[branch]"
# 因此 regex 必须含前导 `[`，不能匹配路径中含 "openspec/" 的子串
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
        source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/state.sh"
        REMAINING=$(count_pending_suggestions "$PROJECT_ROOT")
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
```bash
# === Mode D: thin wrapper — render logic in skills/_lib/roadmap_state.py ===
if [ "$MODE" = "roadmap" ] || ([ -z "$MODE" ] && [ -f "$PROJECT_ROOT/roadmap.md" ]); then
    if [ -f "$PROJECT_ROOT/.rddf/state/roadmap-state.json" ]; then
        # Indent the python3 call
        PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, sys
try:
    from skills._lib.roadmap_state import render_status_view
except ImportError as e:
    print(f"⚠️  roadmap_state 模块不可用: {e}", file=sys.stderr)
    sys.exit(0)
project_root = os.environ.get("PROJECT_ROOT", ".")
sys.exit(render_status_view(
    os.path.join(project_root, "roadmap.md"),
    os.path.join(project_root, ".rddf/state/roadmap-state.json"),
))
'
    else
        echo "⚠️  .rddf/state/roadmap-state.json 不存在，请先运行 skill_use(\"roadmap\", \"init\")"
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
  r|refresh) continue ;;
  ?|help) echo "可用命令: [数字选项], i(自定义输入), q(退出), r(刷新), ?(帮助)" ;;
  i)         # 用户自定义输入
     echo -n "  自定义操作: "; read -r CUSTOM
     echo "   收到: '$CUSTOM' — 尝试路由到最接近的 mode"
     ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

---

## 模式 E：当前迭代（v2.0 新增）

读取 `.rddf/state/iteration.json` 渲染当前 sprint 视图，列出**所有 active change** 的状态、阻塞关系、任务进度、计划文件路径。供 `propose → guide-ship → execute → archive` 流程中的快速概览。

### Step 1：读取 iteration.json

读取与渲染已合并抽取到 `skills/_lib/iteration.py::print_view()`。模块函数内部处理文件缺失(友好提示)、schema 校验失败(回退到空 state)和漂移检测。

```bash
# Mode E: 渲染当前迭代视图（已抽取到 _lib/iteration.py::print_view）
#   print_view <project_root>  → 渲染 header + active 表 + 归档 top5 + 漂移提示 + planned
#   缺失 iteration.json 时返回 0 + 友好提示,不抛错。

PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.iteration import print_view
sys.exit(print_view(os.environ["PROJECT_ROOT"]))
'
```

### Step 2：渲染当前迭代表

见 Step 1 — 已合并到 `print_view()` 单次调用。表格字段、archived top-5、漂移告警、planned 列表(S10)都在模块内部统一处理。

### Step 2b (v2.0.3): 显示 planned 状态 change

planned 列表由 `print_view(show_planned=True)` 统一渲染 (默认 True)。若需隐藏 planned 段,传 `show_planned=False`。

### Step 3：用户操作

```
请选择:
1. 🔄 刷新视图 (重新读取 iteration.json)
2. 🚀 进入 guide-ship (处理 active change)
3. 📊 查看完整依赖图 (.rddf/state/deps-output.md)
4. ↩️ 返回主菜单
i. 其他输入
```

**用户输入处理（v2.0.3 重写，S9 修复）**：

> 注：markdown skill 不是 shell 脚本，`exec $0` 无法工作。重新进入 Mode E 由 AI 助手按以下提示执行：

| 用户输入 | 动作 |
|---------|------|
| `1` 或 `refresh` | 重新读取 iteration.json 并渲染 |
| `2` | `skill_use("guide-ship")` 进入 ship 流 |
| `3` | `cat $PROJECT_ROOT/.rddf/state/deps-output.md` （如存在） |
| `4` 或 `back` | 返回 Mode A 概览 |
| `q` / `quit` / `exit` | 退出 status |
| 其他 | "❌ 无效输入 '$choice'" 提示 |
```

**Mode E 职责说明**：此模式仅做当前 sprint 视图渲染，不修改任何文件。如需更新 iteration 字段（tasks_done 等），由 execute/archive/propose 钩子自动维护。

---


## 输出风格指南（v2.0.3 NEW，对应 C2）

**Emoji 集（locked vocabulary）**：

| 用途 | Emoji |
|------|-------|
| 扫描/推荐 | 🔍 |
| 推荐操作 | 💡 |
| 警告 | ⚠️ |
| 成功 | ✅ |
| 失败 | ❌ |
| 计划/草稿 | 📋 |
| 庆祝 | 🎉 |
| 状态: planned | 📋 |
| 状态: committed-no-wt | 💼 |
| 状态: proposed | ✅ |
| 状态: in_worktree | 🔧 |
| 状态: completed | ✔ |
| 状态: archived | 📦 |

**对齐规范**：表格使用等宽对齐；进度列格式 `done/total  (P%)`（左对齐 11 字符）。Mode A/B/C/D/E 五种输出统一使用上表 emoji，不得混用（🔄 已禁用，统一用 🔧 表示 in_worktree）。

**语言**：中文为主，专有名词保持原文（`openspec`、`worktree`、`ADR`）。

## 关键约束

1. **归档前必须先 merge**：确保代码变更已合入 default branch（`master`/`main`/`develop`，由 `find_default_branch` 动态检测）
2. **不同步用 sed 修复**：**不重跑 plan**（会覆盖 `.rddf/plans/` 中的任务分解细节）
3. **所有操作可从主仓库 TUI session 完成**：通过 `workdir` 参数在 worktree 内执行
4. **归档不可逆**：确认全部完成后再执行模式 C
5. **Roadmap 状态自动更新**：execute 完成后自动更新 .roadmap-state.json
