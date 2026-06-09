---
name: guide-spec
description: Spec-side state machine for OpenSpec workflow — guides user from setup through roadmap, propose, deps, and emits "ready for guide-ship" handoff. Owns openspec/changes/<name>/ artifacts. Called by user when starting new changes.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  author: sisyphus
  version: "1.0"  # P0: Spec-side state machine, split from guide
  evolved-from: "split from guide.md v3.0"
  user-invocable: true
---

# OpenSpec 工作流 — Spec-Side Guide

本技能是 OpenSpec 工作流的 **spec 端状态机**：负责在 git 提交 OpenSpec change artifacts 之前的所有工作——环境检查、路线图管理、扫描/创建 change、依赖分析。提交完成后，发出 "ready for guide-ship" 交接信号，由 `guide-ship` 接管 worktree 创建、计划生成、执行、归档。

**职责边界**：
- **拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md` 的创建与提交
- **不拥有**：worktree 创建、Prometheus 计划生成、实施执行、归档清理（这些由 `guide-ship` 处理）
- **状态持久化**：仅依赖 `proposal-suggestions.md` 的状态标记（本技能不写其他状态文件）

**调用方式**：

```
skill_use("guide-spec")   # 无参数版本
```

---

## Architecture: Spec/Ship Split

本技能是 OpenSpec 工作流拆分后的 **spec 端**实现。在 v3.0 重构前，所有流程由单一 `guide.md` 驱动；重构后拆分为三个职责清晰的子技能：

| 子技能 | 职责 | 关键产物 |
|--------|------|---------|
| `guide-spec`（本技能） | spec 端状态机：环境检查 → 路线图 → 扫描/创建 change → 依赖分析 | `openspec/changes/<name>/{proposal,design,tasks}.md` 已提交 |
| `guide-ship`（后续） | ship 端状态机：发现已提交 change → worktree → plan → execute → archive | worktree 目录、Prometheus 计划文件、归档操作 |
| `guide`（后续） | 无状态推荐器：根据当前 phase 推荐下一步该调用哪个子技能 | 仅对话输出 |

**核心边界（git commit 即切换点）**：

```
[guide-spec]  --(git commit artifacts)-->  [guide-ship]
   spec 端                                          ship 端
   owns: changes/<name>/{proposal,design,tasks}.md  owns: worktree, .sisyphus/plans/, execute
   exits: proposal-suggestions.md status markers    exits: archived changes
```

**为什么这样切**：

- **职责单一**：spec 端不需要懂 worktree，ship 端不需要懂提议生成
- **可独立演进**：修改提议格式不影响 worktree 流程
- **可独立测试**：spec 端的"git commit artifacts"是清晰的契约（用 `git show HEAD:<path>` 验证）
- **会话中断友好**：spec 端用 `proposal-suggestions.md` 状态标记，ship 端用 worktree 自身的 git 状态

**spec 端不写的文件**（与旧 `guide.md` 的区别）：

- 不写旧版 `guide.md` 时代的状态持久化文件（旧版通过那两个文件跨 session 恢复，本技能不写）
- 不创建 worktree（属于 `guide-ship`）
- 不调用 `openspec` 的执行类命令（属于 `guide-ship`）
- 不做归档/清理（属于 `guide-ship`）

**spec 端必须写的文件**：

- 调用 `propose` 技能时生成/更新 `proposal-suggestions.md`（这是 spec 端唯一的状态标记文件）
- 通过 `propose` 技能创建 `openspec/changes/<name>/{proposal.md, design.md, tasks.md, .openspec.yaml}`
- 通过 `deps` 分析生成 `.zcf/.deps-candidates.json` 和 `.zcf/.deps-output.md`（分析输出，不是状态文件）

---

## Phase 1: setup

执行环境检测，检查清单：

```bash
echo "🔍 环境检查..."
echo ""

# 1. openspec CLI
OPENSPEC_PATH=""
for p in $(command -v openspec 2>/dev/null) /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec; do
  [ -x "$p" ] && OPENSPEC_PATH="$p" && break
done
if [ -z "$OPENSPEC_PATH" ]; then
    echo "❌ openspec CLI 未找到"
    echo "   请安装: npm install -g openspec-cli"
    exit 1
fi
if [ -x "$OPENSPEC_PATH" ]; then
    OPENSPEC_VER=$("$OPENSPEC_PATH" --version 2>/dev/null || echo "?")
    echo "✅ openspec CLI: $OPENSPEC_VER"
    OPENSPEC_OK=true
else
    echo "❌ openspec CLI 未找到"
    OPENSPEC_OK=false
fi

# 2. git 状态
GIT_CLEAN=$(git status --porcelain | grep -c . || true)
if [ "$GIT_CLEAN" -eq 0 ]; then
    echo "✅ git 工作区干净"
else
    echo "⚠️  git 工作区有 $GIT_CLEAN 个未跟踪/修改文件"
fi

# 3. 当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "📌 当前分支: $CURRENT_BRANCH"

# 4. 构建目录（按项目类型检测）
if [ -f "Cargo.toml" ]; then
  BUILD_DIR="target"
  PROJECT_TYPE="Rust"
elif [ -f "package.json" ]; then
  BUILD_DIR="node_modules"
  PROJECT_TYPE="Node.js"
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  BUILD_DIR="venv"
  PROJECT_TYPE="Python"
elif [ -f "CMakeLists.txt" ] || [ -f "Makefile" ]; then
  BUILD_DIR="build"
  PROJECT_TYPE="C++/Make"
else
  BUILD_DIR="build"
  PROJECT_TYPE="Unknown"
fi

if [ -d "$BUILD_DIR" ]; then
    echo "✅ 构建目录存在 ($BUILD_DIR/, $PROJECT_TYPE)"
else
    echo "⚠️  构建目录不存在 ($BUILD_DIR/, $PROJECT_TYPE)"
fi

# 5. 已有 change
ACTIVE=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
echo "📋 活跃 changes: $ACTIVE"
```

**展示环境状态 + 选项**：

使用 `question` 工具询问用户：

```
环境检查结果：

✅ openspec CLI: 1.3.1 (/home/ubuntu/.npm-global/bin/openspec)
✅ git 工作区干净
📌 当前分支: master
✅ 构建目录存在
📋 活跃 changes: 0

当前状态: 未开始任何变更流程

请选择:
1. 继续 → 进入 Propose 阶段（扫描建议）
2. 修复 PATH（显示如何添加 openspec 到 PATH）
3. 重新检查（刷新环境状态）
0. 💾 保存并退出
i. 其他输入
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

**步骤 2：进入对应阶段**

根据当前阶段跳转到对应入口。

<!-- Worktree recovery logic moved to guide-ship.md Phase 1 -->

---

## Phase 1.5: roadmap

**入口条件**：setup 已完成，且当前阶段为 roadmap 或 roadmap.md 需要初始化。

**行为**：

1. 检查是否存在 `roadmap.md`
2. 如果不存在，**自动调用** `skill_use("roadmap", "init")` 引导用户通过 4 个模板创建初始路线图
3. 如果存在，展示当前阶段和进度

**环境检测命令**（已与 setup 共享）：

```bash
# openspec CLI 检测
OPENSPEC_PATH=""
for p in $(command -v openspec 2>/dev/null) /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec; do
  [ -x "$p" ] && OPENSPEC_PATH="$p" && break
done
if [ -z "$OPENSPEC_PATH" ]; then
    echo "❌ openspec CLI 未找到"
    echo "   请安装: npm install -g openspec-cli"
    exit 1
fi

# git 状态
GIT_STATUS=$(git status --porcelain)

# 当前分支
CURRENT_BRANCH=$(git branch --show-current)

# 构建目录
BUILD_EXISTS=$([ -d "build" ] && echo "yes" || echo "no")

# 活跃 changes
ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
```

**菜单选项**：

```bash
# ============================================================
# ROADMAP CHECK (P0 FIX)
# Setup 完成后检查 roadmap.md 是否存在
# 不存在则自动调用 skill_use("roadmap", "init") 引导创建
# ============================================================
ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"

if [ ! -f "$ROADMAP_FILE" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  未发现 roadmap.md"
    echo ""
    echo "   路线图用于管理项目阶段和 change 分类。"
    echo "   如果没有路线图，所有 change 将被标记为'未分类'。"
    echo ""
    echo "→ 自动调用 skill_use(\"roadmap\", \"init\") 进入模板选择..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    skill_use("roadmap", "init")
fi
# P1-6: 检测兼容模式 + 残留状态文件
# 当 roadmap.md 不存在但 .zcf/.roadmap-state.json 仍存在,说明:
#   - 之前启用过 roadmap,后来切换到兼容模式
#   - 或 roadmap.md 被误删/未提交
# 此时不自动恢复,只提示用户,避免误覆盖用户数据
if [ ! -f "$ROADMAP_FILE" ] && [ -f "$STATE_FILE" ]; then
    echo ""
    echo "⚠️  roadmap.md 已不存在，但 .zcf/.roadmap-state.json 存在"
    echo "   推测：roadmap 模式已切换为兼容模式"
    echo "   已有的 roadmap-meta.yaml 不会自动更新 .roadmap-state.json"
    echo "   如需重新启用 roadmap，请运行：skill_use(\"roadmap\", \"init\")"
fi
```

```
环境检查完成。检测到：

  openspec CLI: ✅ 1.3.1
  git 工作区:  ✅ 干净
  当前分支:    master
  构建目录:    ✅ 存在
  活跃 changes: 0

请选择:
1. ✅ 继续 → 进入 Propose 阶段
2. 🔄 重新检查
i. 其他操作
```

**菜单示例**：

```
路线图状态

当前阶段: phase-1 (基础架构)
进度:
  - arch-design: 1/2 ✅
  - infra-setup: 0/1 ⏳
  - core-impl: 0/0

请选择:
1. ✅ 继续 → 进入 Propose 阶段（按当前阶段生成 change）
2. 📝 编辑路线图（修改阶段或任务分类）
3. 📊 查看阶段门控报告
4. ⏭️  强制进入下一阶段（如当前阶段已完成）
0. 💾 保存并退出
```

**与 propose 的衔接**：

用户选择「继续」后，guide-spec 进入 propose 阶段。propose 技能会自动读取 roadmap.md，只生成当前阶段的 change。

---

## Phase 2: propose

**入口条件**：setup 已完成，且当前阶段为 propose。

**行为**：

本阶段所有扫描和创建逻辑委托给 `propose` 技能。
guide-spec 作为交互式向导，展示提议技能的结果，让用户选择，然后调用提议技能的创建逻辑。

**交互流程**：

1. **扫描阶段**：调用 `propose` 执行扫描，生成/更新 `proposal-suggestions.md`
2. **选择阶段**：展示扫描结果（从 `proposal-suggestions.md` 读取），让用户选择
   - Roadmap 模式下，只展示当前阶段的 change
   - 非当前阶段的 change 可折叠或标记为「未来阶段」
3. **创建阶段**：用户选择后，调用 `propose --create <name>` 执行创建
4. **循环**：创建后重新展示，用户可继续选或选「完成 Propose 阶段」

**注意**：guide-spec 不直接调用 `openspec new`/`openspec propose` 命令。所有创建逻辑由 `propose` 技能处理。

**显示与执行分离**：

guide-spec 负责显示扫描结果和接收用户选择，但创建操作通过调用 `propose` 技能完成。

```bash
# 展示当前活跃 changes
echo "📋 当前已创建的 Changes:"
# git show HEAD:<path> 要求相对于 repo root 的相对路径。
# 先 cd 进 PROJECT_ROOT,然后用相对 glob 枚举 changes。
(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v archive/ | while read -r dir; do
    name=$(basename "$dir")
    if git rev-parse --verify HEAD >/dev/null 2>&1; then
        committed=$(git show HEAD:"openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
    else
        committed="⏳"
    fi
    echo "  - $name  [Artifacts: $committed]"
done)

# 检查建议列表
if [ -f "proposal-suggestions.md" ]; then
    echo ""
    echo "📂 已有的建议列表 (proposal-suggestions.md)"
    # P1-7: 文件格式已规范化为 JSON 列表
    #       用 python 解析后格式化输出（而不是 cat 原始 JSON）
    #       这样 description 字段的多行内容能正确显示
    python3 -c "
import json, sys
try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print('⚠️  proposal-suggestions.md 顶层不是 JSON 数组', file=sys.stderr)
        sys.exit(0)
    for i, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            continue
        name = e.get('name', '?')
        priority = e.get('priority', '?')
        source = e.get('source', '?')
        status = e.get('status', '?')
        effort = e.get('effort', '')
        effort_str = f' ({effort})' if effort else ''
        print(f'  {i}. [{priority}] {name} — {source} [{status}]{effort_str}')
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'⚠️  读取失败: {e}', file=sys.stderr)
" 2>/dev/null || cat proposal-suggestions.md
else
    echo ""
    echo "🆕 开始扫描..."
    # Sub-skill: propose (called from guide-spec.Phase 2)
    skill_use("propose")
fi
```

**用户选择后的处理**：

当用户选择某个建议进行创建时，guide-spec 调用 `propose` 执行创建：

```bash
if [ "$choice" = "1" ]; then
    # 创建 fix-ns-pollution
    # Sub-skill: propose (called from guide-spec.Phase 2)
    skill_use("propose", "--create", "fix-ns-pollution")
elif [ "$choice" = "2" ]; then
    # 创建 add-stream-pipes
    # Sub-skill: propose (called from guide-spec.Phase 2)
    skill_use("propose", "--create", "add-stream-pipes")
fi
```

**建议列表选项**（每次创建后重新展示）：

```
建议列表（来自 ADR 扫描 + 代码 TODO）：

🔴 高优先级
1. fix-ns-pollution  — 修复命名空间污染 (ADR-033, 3 个任务)
2. add-stream-pipes  — 实现 Stream 管道操作符 (ADR-022, 5 个任务)

🟡 中优先级
3. add-cdc-support   — 跨时钟域支持 (架构差距分析)

当前已创建: fix-ns-pollution ✅

请选择:
1. 创建 fix-ns-pollution（已存在的跳过）
2. 创建 add-stream-pipes
3. 创建 add-cdc-support
4. ✅ 完成 Propose 阶段 → 进入 Deps 阶段
5. 📋 查看所有已创建的 change 详情
0. 💾 保存并退出
i. 手动输入 change 名称
```

**创建后重新进入此阶段**：

每次创建完成后，重新检查建议列表 + 活跃 changes，重新展示选项菜单（循环）。

**Propose 阶段完成条件**：

用户选择「4. 完成 Propose 阶段」后，验证至少有一个 change 的 artifacts 已提交，然后推进到 **deps 阶段**（依赖分析）。

**Propose → Deps 流程**：

```
用户选择「完成 Propose」
    ↓
验证 artifacts 已提交
    ↓
【自动执行】调用 deps.md 分析候选 change 依赖
    ↓
展示依赖图和推荐执行顺序
    ↓
guide-spec 阶段完成（spec-done）
    ↓
交接给 guide-ship
```

---

## Phase 2.5: deps

**入口条件**：propose 阶段完成，用户选择「完成 Propose 阶段」后自动触发。

**前置说明**：
本阶段自动执行，不需要用户交互。所有结果通过 deps.md 生成。

**行为**：

1. **生成候选列表**：读取所有已提交的 change，生成 `.zcf/.deps-candidates.json`
2. **执行依赖分析**：调用 deps.md 分析 change 间依赖
3. **输出依赖图**：生成 `.zcf/.deps-output.md`，包含 Mermaid 依赖图和推荐执行顺序
4. **展示结果**：展示依赖图、冲突检测、推荐顺序

**自动执行内容**：

```bash
# Step 1: 生成候选列表（guide-spec 负责此步骤）
mkdir -p "$PROJECT_ROOT/.zcf"
python3 -c "
import json, os, sys, subprocess

# 读取所有已提交的 change
changes_dir = '$PROJECT_ROOT/openspec/changes'
candidates = []
if os.path.isdir(changes_dir):
    for name in sorted(os.listdir(changes_dir)):
        # 检查 change 是否已提交（.openspec.yaml 在 HEAD 中存在）
        # 用 git show HEAD: 比对文件系统更准确：未提交的本地草稿不应被视作候选
        try:
            result = subprocess.run(
                ['git', 'show', f'HEAD:openspec/changes/{name}/.openspec.yaml'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                candidates.append(name)
        except (FileNotFoundError, subprocess.SubprocessError) as e:
            print(f'⚠️ git show failed for {name}: {e}', file=sys.stderr)

data = {'candidates': candidates}
with open('$PROJECT_ROOT/.zcf/.deps-candidates.json', 'w') as f:
    json.dump(data, f, indent=2)
print(f'生成候选列表: {candidates}')
"

# Step 2: 调用 deps.md 技能（静态三轴分析 + 子代理语义分析占位）
# deps.md 读取 .zcf/.deps-candidates.json，输出 .zcf/.deps-output.md
# 详细实现见 skills/deps.md
skill_use("deps")

# Step 3: 展示结果
echo "📊 依赖分析完成"
cat "$PROJECT_ROOT/.zcf/.deps-output.md"
```

**详细分析逻辑**（已迁移到 `skills/deps.md`）：

- **静态三轴分析**（文件冲突、ADR 引用、接口依赖）：见 `skills/deps.md` Step 2
- **Mermaid 图生成**（独立 change 用 subgraph、依赖用 `-->`、冲突用 `-.->|冲突|`）：见 `skills/deps.md` Step 5a
- **子代理语义分析**：见 `skills/deps.md` Step 3（占位符，后续独立 change 实现）
- **重组建议格式**（拆分/合并/重排）：见 `skills/deps.md` Step 5e

**契约**：
- **输入**: `.zcf/.deps-candidates.json`（Step 1 生成）
- **输出**: `.zcf/.deps-output.md`（由 deps.md 写入，由 Step 3 cat 展示）
- **错误处理**: 若 `.deps-candidates.json` 缺失，deps.md Step 0 退出 1，guide-spec 需在 Step 1 确保生成

**无用户交互**：本阶段自动完成。guide-spec 全部工作完成，输出 spec-done 退出信号。

---

## Phase 3: spec-done (Exit)

Triggered when all committed changes have all three artifacts (`proposal.md`, `design.md`, `tasks.md`) reachable via `git show HEAD:...`.

**Zero-change guard (P1-10):**

```bash
# P1-10: guard against zero active changes
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CHANGE_COUNT=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
if [ "$CHANGE_COUNT" -eq 0 ]; then
  echo "❌ 没有 active change,无法退出 spec-side"
  echo "   请回到 Propose 阶段至少创建一个 change"
  exit 1
fi
```

**Exit guard check:**

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# git show HEAD:<path> 要求相对于 repo root 的相对路径。
# 先 cd 进 PROJECT_ROOT,再用相对 glob 枚举 changes。
# 把循环放在子 shell 里,避免污染调用者的 cwd;再用 $? 拿子 shell 的退出码决定是否拒绝。
if (cd "$PROJECT_ROOT" 2>/dev/null && for d in openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    name=$(basename "$d")
    for artifact in proposal.md design.md tasks.md; do
        if ! git show HEAD:"$d$artifact" > /dev/null 2>&1; then
            echo "❌ $name missing committed $artifact — refuse to exit spec-side"
            exit 1
        fi
    done
done); then
    echo "✅ All changes have committed artifacts. Spec side complete."
else
    exit 1
fi
```

**Handoff state write (P2-5):**

spec-side → ship-side 交接通过 `.zcf/.handoff.json` 软状态文件传递。spec-done 验证通过后立即写入,记录 spec_complete_at、ship_started_at (初值 null)、current_change (第一个 active change 名称)。ship 端 Phase 1 入口读取并回填 ship_started_at。文件不被 git 跟踪(.gitignore 排除),缺失时 ship 端静默回退到旧行为。

```bash
# P2-5: 写入 handoff 状态,作为 spec→ship 的软交接信号
# 缺失 .zcf 目录时静默创建 (mkdir -p),写失败不阻塞 spec-done 输出
HANDOFF_FILE="$PROJECT_ROOT/.zcf/.handoff.json"
# 取第一个 active change 名作为 current_change;若没有则用空字符串
CURRENT_CHANGE=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | head -1 | xargs -n1 basename 2>/dev/null)
CURRENT_CHANGE="${CURRENT_CHANGE:-}"
mkdir -p "$PROJECT_ROOT/.zcf"
cat > "$HANDOFF_FILE" << EOF
{
  "spec_complete_at": "$(date -Iseconds)",
  "ship_started_at": null,
  "current_change": "$CURRENT_CHANGE"
}
EOF
if [ -f "$HANDOFF_FILE" ]; then
    echo "✅ Handoff state written: .zcf/.handoff.json (current_change=$CURRENT_CHANGE)"
else
    echo "⚠️  Handoff state write failed, ship 端将使用旧行为"
fi
```

**Output to user:**

```
✅ Spec-side complete. Your changes are committed.

💡 Next: skill_use("guide-ship")
   This will scan your committed changes and start worktree creation + execution.
```

Do NOT auto-invoke `guide-ship` — the user must explicitly transition to the ship side.
