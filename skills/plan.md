---
name: plan
description: 发现所有已创建但未建立 branch/worktree 的 OpenSpec change，按 roadmap 阶段过滤，用户选择后执行 openspec-plan 命令序列创建 worktree 并生成 Prometheus 实施计划。支持阶段门控检查。
license: MIT
metadata:
  author: sisyphus
  version: "2.0"  # P0: Roadmap 驱动，支持阶段过滤和门控
  generatedBy: "2.0"
---

```
main: propose → commit artifacts
                        ↓
             本技能：发现候选 changes → 按阶段过滤 → 阶段门控 → 用户选择 → 创建 worktree → 生成 plan
                    ↓
worktree: execute (基于 .sisyphus/plans/) → merge → archive
```

**Roadmap 驱动特性**：
- 按 roadmap 当前阶段过滤候选 change
- 阶段门控检查（当前阶段未完成时提示）
- 支持跨阶段依赖分析

## 输入

- `change name`（可选）：kebab-case 格式。
  - 提供 → 执行 Phase 0 发现阶段进行验证，然后进入 Phase 2
  - 不提供 → 进入 Phase 0 发现阶段，让用户选择

---

## Phase 0：发现候选 Changes（兼作验证阶段）

扫描 `openspec/changes/` 目录，找出所有已创建但尚未建立 worktree 的 change。

**用途**：
- 未提供 change name → 发现所有候选 changes，展示供用户选择
- 提供 change name → 验证该 name 是否为有效候选（存在、未 plan、未归档）

### Step 0a：列出所有 change 目录

```bash
# 自动检测项目根目录（用于全局安装的技能）
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# 列出 $PROJECT_ROOT/openspec/changes/ 下所有 change 目录（排除 archive/）
ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | sed 's#$PROJECT_ROOT/openspec/changes/##; s#/##'
```

### Step 0b：检查已有 worktree 和分支

对每个 change，判断是否已有 worktree：

```bash
# 检查已有 worktree 分支（兼容旧版 git）
EXISTING_BRANCHES=$(git branch --list 'openspec/*' | sed 's/^[* ]*//; s/^openspec\///')

# 检查已有 worktree
EXISTING_WTS=$(git worktree list | awk '$2 ~ /^openspec\// {print $2}' | sed 's/^openspec\///')
```

一个 change 如果同时满足以下条件才是"待计划"的候选：

| 条件 | 检测 | 说明 |
|------|------|------|
| 目录存在 | `-d openspec/changes/<name>/` | change 已创建 |
| 未归档 | 不在 `openspec/changes/archive/` | 不是已完成的工作 |
| 无 worktree | `git worktree list` 无匹配 | 尚未进入执行阶段 |
| 无 branch | `git branch --list openspec/<name>` 为空 | 尚未创建隔离分支 |
| artifacts 就绪 | `openspec status` 为 `ready` | proposal/design/tasks 齐全 |

### Step 0c：获取每个候选的元数据

对每个符合条件的候选 change，收集信息用于排序和推荐：

```bash
# 获取 openspec 状态
STATE=$(openspec status --change "<name>" --json | jq -r '.state')
PROGRESS=$(openspec status --change "<name>" --json | jq -r '.progress')

# 获取目录修改时间（反映创建时间，macOS/BSD 兼容）
get_mtime() {
    local dir="$1"
    if command -v stat >/dev/null 2>&1; then
        # Linux
        stat -c %Y "$dir" 2>/dev/null || echo 0
    else
        # macOS/BSD
        stat -f %m "$dir" 2>/dev/null || echo 0
    fi
}
MTIME=$(get_mtime "$PROJECT_ROOT/openspec/changes/<name>/")

# 读取 tasks 数量
TASKS_COUNT=$(grep -c "\- \[ \]" "$PROJECT_ROOT/openspec/changes/<name>/tasks.md" 2>/dev/null || echo "?")
```

### Step 0d：按 Roadmap 阶段过滤

如果项目存在 `roadmap.md`，按当前阶段过滤候选 change：

```bash
ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"

if [ -f "$ROADMAP_FILE" ]; then
    echo "📍 Roadmap 模式：按当前阶段过滤"
    
    # 读取当前阶段
    CURRENT_PHASE=$(python3 -c "
import re
with open('$ROADMAP_FILE') as f:
    content = f.read()
phase_match = re.search(r'\*\*当前阶段\*\*:\s*(\S+)', content)
print(phase_match.group(1) if phase_match else 'unknown')
")
    
    # 过滤候选列表
    FILTERED_CANDIDATES=()
    for name in "${CANDIDATES[@]}"; do
        META_FILE="$PROJECT_ROOT/openspec/changes/$name/roadmap-meta.yaml"
        if [ -f "$META_FILE" ]; then
            CHANGE_PHASE=$(python3 -c "
import yaml
with open('$META_FILE') as f:
    data = yaml.safe_load(f)
print(data.get('roadmap', {}).get('phase', 'unknown'))
")
            if [ "$CHANGE_PHASE" = "$CURRENT_PHASE" ]; then
                FILTERED_CANDIDATES+=("$name")
            fi
        else
            # 无 roadmap-meta.yaml 的 change（兼容模式）
            FILTERED_CANDIDATES+=("$name")
        fi
    done
    
    CANDIDATES=("${FILTERED_CANDIDATES[@]}")
    echo "   当前阶段: $CURRENT_PHASE"
    echo "   过滤后候选数: ${#CANDIDATES[@]}"
fi
```

### Step 0e：排序候选

按以下优先级排序（供 AI 推荐参考）：

| 优先级 | 条件 | 原因 |
|--------|------|------|
| 🥇 `ready` 且等待最久 | `state=ready`，`mtime` 最早 | 最成熟、等待最久的 change 应先处理 |
| 🥈 `ready` 较新 | `state=ready`，`mtime` 较新 | 刚完成的 change 上下文新鲜 |
| ❌ 排除 `blocked` | `state=blocked` | artifacts 不完整，需先补全 |
| ❌ 排除 `all_done` | `state=all_done` | 已全部完成，可直接归档 |

### Step 0e：验证提供的 change name（仅当提供 name 时执行）

当提供了 `change name` 参数时，在 Phase 0 完成后验证该 name：

```bash
# 检查 1：change 目录是否存在
if [ ! -d "$PROJECT_ROOT/openspec/changes/<name>/" ]; then
    echo "❌ Change '<name>' 不存在"
    echo "请先创建: skill_use(\"spec-workflow-propose\")"
    exit 1
fi

# 检查 2：是否已归档
if [ -d "$PROJECT_ROOT/openspec/changes/archive/<name>/" ]; then
    echo "❌ Change '<name>' 已归档"
    echo "归档的 change 无法重新 plan"
    exit 1
fi

# 检查 3：是否已有 worktree
if git worktree list | awk '{print $2}' | grep -q "^openspec/<name>$"; then
    WT_PATH=$(git worktree list | awk '$2=="openspec/<name>" {print $1}')
    echo "❌ Change '<name>' 已存在 worktree: $WT_PATH"
    echo "请直接执行: skill_use(\"spec-workflow-execute\")"
    exit 1
fi

# 检查 4：是否已有分支
if git branch --list "openspec/<name>" | grep -q "openspec/<name>"; then
    echo "⚠️  Branch openspec/<name> 已存在，将使用现有分支"
fi

# 检查 5：状态是否为 ready
STATE=$(openspec status --change "<name>" --json | jq -r '.state')
if [ "$STATE" = "blocked" ]; then
    echo "❌ Change '<name>' 状态为 blocked（artifacts 不完整）"
    echo "请补全 artifacts 后重试"
    exit 1
fi

if [ "$STATE" = "all_done" ]; then
    echo "❌ Change '<name>' 状态为 all_done（已全部完成）"
    echo "请直接归档: skill_use(\"spec-workflow-status <name> --archive\")"
    exit 1
fi

# 检查 6：Roadmap 阶段匹配（roadmap 模式下）
if [ "$ROADMAP_MODE" = true ] && [ -f "$PROJECT_ROOT/openspec/changes/<name>/roadmap-meta.yaml" ]; then
    CHANGE_PHASE=$(python3 -c "
import yaml
with open('$PROJECT_ROOT/openspec/changes/<name>/roadmap-meta.yaml') as f:
    data = yaml.safe_load(f)
print(data.get('roadmap', {}).get('phase', 'unknown'))
")
    if [ "$CHANGE_PHASE" != "$CURRENT_PHASE" ]; then
        echo "⚠️  Change '<name>' 属于阶段 '$CHANGE_PHASE'，不是当前阶段 '$CURRENT_PHASE'"
        echo ""
        echo "请选择:"
        echo "1. 仍为此 change 创建 worktree"
        echo "2. 切换到阶段 '$CHANGE_PHASE'"
        echo "3. 取消"
        # 根据用户选择处理
    fi
fi

echo "✅ Change '<name>' 验证通过（state: $STATE）"
echo "   准备创建 worktree..."
```

---

## Phase 0.5：Change 间依赖分析

本阶段复用 Phase 0 的候选 change 列表，调用 `spec-workflow-deps` 进行依赖分析，结果用于 Phase 1 的用户选择。

### Step 1：复用 Phase 0 的候选列表

Phase 0 已完成候选 change 的发现和验证。本步骤直接获取其结果，不重新扫描：

```bash
# Phase 0 已产出候选列表（变量名：CANDIDATES，来自 Phase 0 Step 0a-0d）
# 使用 "${CANDIDATES[@]}" 展开所有元素
echo "📋 候选 change 列表（来自 Phase 0）："
for name in "${CANDIDATES[@]}"; do
  echo "  - $name"
done
```

### Step 2：将候选列表写入共享文件（供 deps 技能读取）

```bash
# 将候选列表写入 JSON 文件，作为 plan → deps 的数据交换契约
DEPS_INPUT="$PROJECT_ROOT/.zcf/.deps-candidates.json"
mkdir -p "$PROJECT_ROOT/.zcf/"

# 构建候选列表的 JSON
echo '{' > "$DEPS_INPUT"
echo '  "project_root": "'"$PROJECT_ROOT"'",' >> "$DEPS_INPUT"
echo '  "candidates": [' >> "$DEPS_INPUT"
first=true
for name in "${CANDIDATES[@]}"; do
  $first || echo ',' >> "$DEPS_INPUT"
  echo -n '    "'"$name"'"' >> "$DEPS_INPUT"
  first=false
done
echo '' >> "$DEPS_INPUT"
echo '  ]' >> "$DEPS_INPUT"
echo '}' >> "$DEPS_INPUT"

echo "✅ 候选列表已写入 $DEPS_INPUT"
```

### Step 3：调用依赖分析技能

将候选列表传递给 `spec-workflow-deps` 技能。deps 技能从 `.zcf/.deps-candidates.json` 读取候选列表，并将分析结果写入 `.zcf/.deps-output.md`：

```bash
echo "🔍 正在分析 ${#CANDIDATES[@]} 个 change 间的依赖关系..."
skill_use("spec-workflow-deps")
```

`spec-workflow-deps` 的输入输出契约：

| 方向 | 文件 | 格式 | 
|------|------|------|
| **plan → deps** | `.zcf/.deps-candidates.json` | `{ "candidates": ["name1", "name2"], ... }` |
| **deps → plan** | `.zcf/.deps-output.md` | Markdown 依赖分析报告（含 5 个章节） |

### Step 4：读取 deps 输出并解析

```bash
DEPS_OUTPUT="$PROJECT_ROOT/.zcf/.deps-output.md"
if [ -f "$DEPS_OUTPUT" ]; then
  echo "✅ 依赖分析结果已就绪: $DEPS_OUTPUT"
else
  echo "⚠️  依赖分析未产生输出，将使用无依赖信息的即席模式"
fi
```

`spec-workflow-deps` 的输出（`.zcf/.deps-output.md`）包含以下章节，供 Phase 1 消费：

```markdown
## 依赖图
flowchart LR
  PREREQ --> DEPENDENT_1
  PREREQ --> DEPENDENT_2

## Change 状态表
| Change | 状态 | 阻塞于 | 冲突 | 置信度 |
|--------|------|--------|------|--------|

## 推荐执行顺序
1. PREREQ ...
2. ...

## 冲突警告
🔴 文件冲突...

## AI 分析建议
🧠 语义依赖 / 粒度评估 / 重组建议 / 风险提示
```

---

## Phase 1：与用户交互选择（含依赖信息）

当提供 change name 时：
- 仍然执行 Phase 0 发现阶段（用于验证提供的 name 是否有效）
- 验证通过后，执行 Phase 0.5 依赖分析（检查该 change 是否有未满足的前置依赖）
- 若其有未满足的前置依赖（blocked_by），提示用户并建议先处理前置 change
- 用户确认后仍可继续进入 Phase 2

当未提供 change name 时：展示加入依赖分析的发现结果，让用户选择。

**两种展示模式**：

### 模式 A：发现候选 changes（含依赖信息和阶段过滤）

```
📋 发现 <N> 个待计划的 change（含依赖分析）：

### 🥇 prerequisite — 其他 change 的前置，建议优先
1. refactor-stream-base ─ ready，阻塞: add-m2sPipe, add-s2mPipe

### ✅ ready — 无前置依赖
2. fix-ns-pollution ─ artifacts ready，5天前，4个任务

### ⚠️ blocked_by — 被其他 change 阻塞
3. add-m2sPipe ─ 阻塞于: refactor-stream-base，冲突: add-s2mPipe
4. add-s2mPipe ─ 阻塞于: refactor-stream-base，冲突: add-s2mPipe

### ❌ artifacts 不完整
5. add-cdc-support ─ 缺少 design.md

### 📍 阶段过滤（Roadmap 模式）
当前阶段: phase-1 (基础架构)
已过滤掉 <M> 个非当前阶段的 change:
  - add-advanced-feature (phase-3)
  - optimize-performance (phase-3)

---

推荐：第 1 个 change 按依赖顺序执行
```

AI 构建 Question 工具选项：

```javascript
{
    header: "选择 change 执行 plan",
    question: "请选择要创建 worktree + plan 的 change（可多选，系统按依赖顺序执行）",
    multiple: true,
    options: [
        { label: "refactor-stream-base (prerequisite)", description: "阻塞: add-m2sPipe, add-s2mPipe, 建议优先" },
        { label: "fix-ns-pollution",                      description: "ready, 5天前, 4个任务" },
        // blocked_by 的 change 灰显提示
        { label: "add-m2sPipe (被阻塞)",                   description: "先完成 refactor-stream-base" },
        // 新增操作选项（始终可选）
        { label: "🔀 合并冲突 change",                     description: "合并有文件冲突的多个 change 为一个" },
        { label: "🔄 为前置依赖创建新 change",             description: "发现新的前置依赖，调用 propose 创建" },
    ]
}
```

### 模式 B：无候选 changes

```
✅ 所有 change 均已创建 worktree 或已归档。

当前所有 openspec 工作进度：
  - add-stream-pipe-ops → .zcf/add-stream-pipe-ops-wt (branch: openspec/add-stream-pipe-ops)
  - fix-ns-pollution → .zcf/fix-ns-pollution-wt (branch: openspec/fix-ns-pollution)

建议：skill_use("spec-workflow-execute") 继续执行现有 worktree 中的任务
```

### 用户选择后的处理

| 用户选择 | 行为 |
|----------|------|
| 选择一个 ready/prerequisite change | 记录 `<name>`，进入 Phase 2 |
| 选择一个 blocked_by change（带警告） | 用户确认后仍允许进入 Phase 2（可能需要在 plan 中标注缺失的前置） |
| 选择多个 ready change | 按依赖图拓扑顺序逐个进入 Phase 2（无冲突的可并行创建 worktree） |
| 🔀 合并冲突 change（带用户输入） | ① 用户指定要合并的多个 change name<br>② AI 读取各 change 的 proposal.md，生成合并后的 proposal 描述<br>③ 调用 propose 技能创建新 change（使用合并后的需求描述）<br>④ 原 change 标记为 superseded（在 `proposal-suggestions.md` 中删除） |
| 🔄 为前置依赖创建新 change（带用户输入） | ① 用户描述前置任务内容<br>② AI 生成 proposal 格式的需求描述（包含 In Scope / ADR 引用）<br>③ 调用 propose 技能创建新 change<br>④ 回到 Phase 1 重新选择（新 change 加入候选列表） |
| 📍 查看/切换阶段（Roadmap 模式） | 展示当前阶段状态，允许切换到其他阶段 |
| 取消/跳过 | 终止，不做任何操作 |

---

## openspec-plan 命令序列

**openspec-plan 命令序列**（等同于 Phase 2 的全部步骤）：
1. `openspec status --change "<name>" --json` — 验证 change 状态是否为 ready
2. COMMIT GATE — 检查 artifacts 是否已 git commit（worktree 只能看到已 commit 的文件）
3. `git branch openspec/<name> HEAD` — 创建基于 HEAD 的分支
4. `git worktree add .zcf/<name>-wt openspec/<name>` — 创建 worktree 隔离环境
5. `openspec instructions apply --change "<name>" --json` — 获取 tasks 和 contextFiles
6. 调用 Prometheus agent 生成 `.sisyphus/plans/<name>.md` 实施计划
7. `git add .sisyphus/plans/<name>.md && git commit` — 提交 plan 到 worktree 分支

---

## Phase 2：为选中的 change 执行 Plan

从用户选择（Phase 1）或直接输入（`<name>` 参数）获得 change name，执行以下流程。

### Step 1：验证前置条件

**1a. 验证 change 存在（防御性检查）**

> 注：Phase 0 和 Phase 0e 已验证过 change 存在。此处为防御性重复检查，覆盖"Phase 1 用户选择到 Phase 2 执行之间有人为删除了 change 目录"的边界情况。

```bash
openspec status --change "<name>" --json
```

| state | 处理 |
|-------|------|
| `blocked` | 终止，提示补全 artifacts |
| `all_done` | 终止，提示已可归档 |
| `ready` | 继续 |

**1b. COMMIT GATE —— 检查 artifacts 是否已提交**

```bash
# 先检查是否有未提交的修改（防止用户修改 artifacts 后未重新 commit）
if [ -n "$(git status --porcelain $PROJECT_ROOT/openspec/changes/<name>/)" ]; then
    echo "⚠️  $PROJECT_ROOT/openspec/changes/<name>/ 有未提交的修改"
    echo ""
    echo "请选择处理方式："
    echo "  1. 自动执行：git add + git commit（推荐）"
    echo "  2. 手动处理：先退出，执行以下命令后再重新调用 plan"
    echo ""
    echo "手动命令："
    echo "  git add $PROJECT_ROOT/openspec/changes/<name>/"
    echo '  git commit -m "feat: <name> change artifacts"'
    echo "  skill_use(\"spec-workflow-plan <name>\")"
    echo ""
    read -p "选择 [1=自动/2=手动]: " gate_choice
    
    if [ "$gate_choice" = "1" ]; then
        git add "$PROJECT_ROOT/openspec/changes/<name>/"
        git commit -m "feat: <name> change artifacts"
        echo "✅ 已自动提交"
    else
        echo "已取消，请先手动提交"
        exit 1
    fi
fi

# 再检查 artifacts 是否在 HEAD 的提交记录中
git show HEAD:$PROJECT_ROOT/openspec/changes/<name>/.openspec.yaml > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Artifacts 尚未提交，无法创建 worktree"
    echo ""
    echo "原因: git worktree 只能检出已 commit 的快照"
    echo "      当前 artifacts 尚未进入分支历史"
    echo ""
    echo "请选择处理方式："
    echo "  1. 自动执行：git add + git commit（推荐）"
    echo "  2. 手动处理：先退出，执行手动命令后再重新调用 plan"
    echo ""
    read -p "选择 [1=自动/2=手动]: " retry_choice
    
    if [ "$retry_choice" = "1" ]; then
        git add "$PROJECT_ROOT/openspec/changes/<name>/"
        git commit -m "feat: <name> change artifacts"
        echo "✅ 已自动提交，继续执行 plan..."
    else
        echo "已取消，请先手动提交："
        echo "  git add $PROJECT_ROOT/openspec/changes/<name>/"
        echo '  git commit -m "feat: <name> change artifacts"'
        echo "  skill_use(\"spec-workflow-plan <name>\")"
        exit 1
    fi
fi
```

### Step 2：检查是否已存在 worktree

```bash
git worktree list | awk '$2=="openspec/<name>" {print $1}'
```

- 匹配到 path → 已存在 worktree，跳转到 Step 4（在 worktree 内生成 plan）
- 空结果 → 不存在，继续 Step 3

> 注：此检查理论上应为空（Phase 0 已排除有 worktree 的 change），
> 但保留 double-check 以防止 Phase 0 后外部创建了 worktree。

### Step 3：创建 worktree

```bash
# Guardrail：确认当前在 main/master
CURRENT=$(git branch --show-current)
if [ "$CURRENT" != "main" ] && [ "$CURRENT" != "master" ]; then
    echo "❌ 当前不在 main/master 分支（当前: $CURRENT）"
    echo "请先切换到 main 再执行 plan"
    exit 1
fi

# 创建分支（基于 HEAD，确保包含 artifacts commit）
if git branch --list "openspec/<name>" | grep -q "openspec/<name>"; then
    echo "⚠️  Branch openspec/<name> 已存在，使用现有分支"
else
    git branch openspec/<name> HEAD
fi

# 检查 worktree 目录冲突
if [ -d "$PROJECT_ROOT/.zcf/<name>-wt" ]; then
    if git worktree list | grep -q "$PROJECT_ROOT/.zcf/<name>-wt"; then
        echo "⚠️  Worktree 目录 $PROJECT_ROOT/.zcf/<name>-wt 已存在且已注册"
        echo "   跳转到 Step 4 直接生成 plan"
        # 跳转到 Step 4 的逻辑
    else
        echo "❌ 目录 $PROJECT_ROOT/.zcf/<name>-wt 已存在但未注册为 worktree"
        echo "   请手动清理后重试：rm -rf $PROJECT_ROOT/.zcf/<name>-wt"
        exit 1
    fi
else
    git worktree add $PROJECT_ROOT/.zcf/<name>-wt openspec/<name>
    echo "✅ Worktree 已创建: $PROJECT_ROOT/.zcf/<name>-wt"
    echo "   Branch: openspec/<name>"
fi

# ============================================================
# WORKTREE VERIFICATION GATE (P0 FIX)
# 验证 worktree 是否正确关联到分支，防止 detached HEAD 问题
# ============================================================
WT_PATH="$PROJECT_ROOT/.zcf/<name>-wt"
WT_BRANCH=$(git worktree list --porcelain | awk -v path="$WT_PATH" '
    $1 == "worktree" && $2 == path { found=1; next }
    found && $1 == "branch" { print $2; exit }
    found && $1 == "detached" { print "DETACHED"; exit }
')

if [ "$WT_BRANCH" = "DETACHED" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ 错误：Worktree 处于 detached HEAD 状态！"
    echo ""
    echo "  这意味着 branch 创建失败或 worktree 指向了错误的 commit。"
    echo "  新提交的代码将无法被 main 分支 merge。"
    echo ""
    echo "  修复步骤："
    echo "  1. cd $WT_PATH"
    echo "  2. git checkout openspec/<name>  # 切换回正确分支"
    echo "  3. cd $PROJECT_ROOT && skill_use(\"spec-workflow-plan <name>\")  # 重新进入 Plan"
    echo ""
    echo "  或完全重建："
    echo "  1. git worktree remove $WT_PATH"
    echo "  2. git branch -D openspec/<name>"
    echo "  3. skill_use(\"spec-workflow-plan <name>\")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
elif [ -z "$WT_BRANCH" ]; then
    echo "⚠️  警告：无法确定 worktree 分支状态"
else
    echo "✅ Worktree 分支验证通过: $WT_BRANCH"
fi
```

### Step 4：切换到 worktree 并读取 artifacts

```bash
cd $PROJECT_ROOT/.zcf/<name>-wt
```

子代理的 prompt 应指明：

```
WORKTREE: .zcf/<name>-wt
所有操作在 .zcf/<name>-wt/ 目录下执行（使用 workdir 参数）。
```

读取 change artifacts：

```bash
openspec instructions apply --change "<name>" --json
```

提取：
- `contextFiles`：需读取的文件
- `tasks`：任务列表（作为 Prometheus 的参考）

按顺序读取 `contextFiles`：
- `openspec/changes/<name>/proposal.md`
- `openspec/changes/<name>/specs/*.md`
- `openspec/changes/<name>/design.md`
- `openspec/changes/<name>/tasks.md`（薄参考层，Prometheus 会生成自己的详细分解）

### Step 5：生成 Prometheus 实施计划

调用 Prometheus agent 在 worktree 下生成 `.sisyphus/plans/<name>.md`：

```
传递给 Prometheus 的内容：
- change name 和描述
- 所有 artifact 文件内容摘要
- tasks 列表（参考用，Prometheus 会重新分解）
- AGENTS.md 项目规范
- 注意：当前工作目录在 worktree 中

要求 Prometheus 输出：
- Scope（IN/OUT）
- Dependency Graph（可并行执行的任务标记）
- Work Units（带优先级、依赖、预计工作量）
- QA Scenarios
- 风险点和缓解措施
```

Prometheus agent 调用 planning-with-files 技能生成计划文件。

### Step 6：提交 plan 到 worktree 分支

```bash
# 此时已在 worktree 目录内（Step 4 中已 cd）
git add .sisyphus/plans/<name>.md
git commit -m "plan: <name> 实施计划"
```

### Step 7：输出结果 + 循环检查

```
✅ Plan 完成

Change: <name>
Worktree: .zcf/<name>-wt  (branch: openspec/<name>)
Plan: .sisyphus/plans/<name>.md

下一步：
  1. 进入 worktree 目录（execute 技能需要在 worktree 内执行）：
     cd .zcf/<name>-wt

  2. 然后在 worktree 内执行：
     skill_use("spec-workflow-execute")

  如果还有未计划的 change，可以再次执行本技能：
    skill_use("spec-workflow-plan")
```

**Plan 后循环检查**：

```bash
# 检查是否还有其他已创建但未计划的 change
UNPLANNED=$(ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | grep -v archive/ | while read dir; do
    name=$(basename "$dir")
    if ! git worktree list | awk '{print $2}' | grep -q "^openspec/$name$"; then
        echo "$name"
    fi
done | wc -l)

if [ "$UNPLANNED" -gt 0 ]; then
    echo ""
    echo "📋 还有 $UNPLANNED 个已创建但未计划的 change:"
    ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | grep -v archive/ | while read dir; do
        name=$(basename "$dir")
        if ! git worktree list | awk '{print $2}' | grep -q "^openspec/$name$"; then
            echo "   - $name"
        fi
    done
    echo ""
    echo "请选择:"
    echo "1. 继续为其他 change 创建 worktree（返回 Phase 1）"
    echo "2. 完成 Plan 阶段，进入 Execute 阶段"
    echo "i. 其他输入"
fi
```

---

## 关键约束

1. **COMMIT GATE 不可跳过**：`git worktree add` 只能看到已 commit 的文件
2. **Plan 不进 main 分支**：只在 worktree 的 `openspec/<name>` 分支上
3. **tasks.md 是薄层**：Prometheus 有自己详细的 `.sisyphus/plans/`，tasks.md 仅用于 openspec CLI 进度检测
4. **Worktree 构建目录**：`.zcf/<name>-wt/build/`（独立构建，ccache 加速）
5. **发现阶段只扫描 active 目录**：不扫描 `openspec/changes/archive/` 中的已归档 change
6. **Roadmap 阶段过滤**：roadmap 模式下，只显示当前阶段的 change（除非用户明确要求查看其他阶段）
7. **阶段门控提示**：当前阶段有未完成的 change 时，提示用户优先完成当前阶段
