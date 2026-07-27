---
name: guide-arch
description: Architecture definition phase state machine for OpenSpec workflow — guides user through setup, ADR creation, architecture analysis, roadmap definition, and emits arch-done handoff. Called when starting architecture work or after arch-done gate.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  version: "2.0"
  author: sisyphus
  evolved-from: "extracted from guide-spec.md v1.0 (Phase 1 + Phase 1.5)"
  user-invocable: true
---

# OpenSpec 工作流 — Arch-Side Guide

本技能是 OpenSpec 工作流 v2.0 的 **arch 端状态机**：负责在生成 OpenSpec change artifacts 之前的**架构定义**工作——环境检测、ADR 文档管理、架构差距分析、路线图定义。arch 阶段是三阶段架构（arch → plan → ship，ADR-0003）的第一阶段，专为高人工介入、低频执行的架构治理工作而设计。

**职责边界**：
- **拥有**：`docs/adr/ADR-*.md`（架构决策记录）、`roadmap.md` + `roadmap-meta.yaml`（路线图）、`docs/architecture/*-gap-analysis.md`（架构差距分析）
- **不拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md`（属于 `guide-plan`）、git worktree（属于 `guide-ship`）
- **状态持久化**：arch-done 时写入 `.rddf/state/.arch-handoff.json`（不被 git 跟踪，缺失时 plan 端静默回退）
- **人工介入程度**：**高** —— arch 阶段是三阶段中人工介入最多的，需要架构师思考、审查、决策

**调用方式**：

```
skill_use("guide-arch")   # 无参数版本
```

---

## Architecture: v2.0 三阶段拆分

本技能是 OpenSpec 工作流 v2.0 重构后的 **arch 端**实现。在 v2.0 重构前，所有 spec 端工作由单一 `guide-spec` 驱动；v2.0 拆分为三个职责清晰的子技能，按**人工介入程度**和**职责类型**切分：

| 子技能 | 阶段 | 职责 | 人工介入 |
|--------|------|------|---------|
| `guide-arch`（本技能） | arch | 架构定义：setup → adr-create → architecture → roadmap-define → arch-validation → proposal-review → arch-done | **高** |
| `guide-plan`（后续） | plan | 变更生成：审批提案消费 → propose → deps → plan-done | **中** |
| `guide-ship`（后续） | ship | 变更执行：plan → execute → archive → cleanup → ship-done | **低** |
| `guide`（无状态推荐器） | — | 扫描三阶段状态，推荐下一步 | — |

**核心边界（arch-done 即切换点）**：

```
[guide-arch]  --(arch-done: ADR ≥ 1 + roadmap.md)-->  [guide-plan]
   arch 端                                              plan 端
   owns: docs/adr/ADR-*.md, roadmap.md,                owns: openspec/changes/<name>/
         docs/architecture/*-gap-analysis.md                  {proposal,design,tasks}.md
   exits: .rddf/state/.arch-handoff.json                     exits: .rddf/state/.plan-handoff.json
```

**为什么这样切**（节选自 ADR-0003）：

- **职责单一**：arch 不需要懂 change artifacts，plan 不需要懂架构治理
- **人工介入匹配**：高介入（arch，需要架构师审查）→ 中介入（plan，AI 辅助生成）→ 低介入（ship，自动执行）
- **架构治理前置**：v2.0 要求"先定义架构，再生成变更"，避免"跳过架构直接编码"
- **可独立演进**：修改 ADR 格式不影响 change 生成流程
- **可独立测试**：arch-done 是清晰契约（用 ADR 数量 + roadmap.md 存在性验证）

**arch 端不写的文件**：

- 不写 `openspec/changes/<name>/` 下任何 artifact（属于 `guide-plan`）
- 不创建 worktree（属于 `guide-ship`）
- 不调用 `openspec new` / `openspec propose` 等执行类命令（属于 `guide-plan`）
- 不做归档/清理（属于 `guide-ship`）

**arch 端必须写的文件**：

- 通过 adr-create 阶段生成/更新 `docs/adr/ADR-*.md`
- 通过 architecture 阶段生成/更新 `docs/architecture/*-gap-analysis.md`
- 通过 roadmap-define 阶段生成/更新 `roadmap.md` + `roadmap-meta.yaml`（委托给 `roadmap` 技能）
- arch-done 时写入 `.rddf/state/.arch-handoff.json`

---

## Phase 1: setup

**入口条件**：用户调用 `skill_use("guide-arch")` 后立即执行。

**rddf-session 入口 hook**（ADR-0017）：创建或查找当前 opencode session 的 `stage_arch` rddf-session：

```bash
# rddf-session 入口 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_entry stage_arch guide-arch arch-phase arch-done .rddf/state/.arch-handoff.json
```

**行为**：

执行环境检测，检查清单：

```bash
# Round A: extracted to _lib/arch_env_check.sh (L92-L189, ~96 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_env_check.sh"
run_arch_env_check || exit 1
```

**展示环境状态 + 选项**：

```
环境检查结果：

✅ openspec CLI: 1.3.1 (/home/ubuntu/.npm-global/bin/openspec)
✅ git 工作区干净
📌 当前分支: master
✅ 构建目录存在
📋 现有 ADR: 3
📋 Roadmap: 已定义
📋 架构差距分析: 0
📋 活动 changes: 2

当前状态: arch 阶段初始化完成

请选择:
1. ✅ 继续 → 进入 adr-create 阶段
2. 🔄 重新检查
0. 💾 保存并退出
i. 其他输入
```

**用户输入处理（case handler）**：

当用户输入不在上述有效选项内时，调用共享菜单处理器处理（extracted to scripts/arch_roadmap_menu.sh）：

```bash
# Phase 1 setup menu - shared handler (extracted from inline case block)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_roadmap_menu.sh"
handle_arch_menu "$choice"
[ $? -eq 2 ] && continue  # r|refresh -> 重新展示菜单
```

**步骤 2：进入对应阶段**

根据当前阶段跳转到对应入口。

---

## Phase 2: adr-create

**入口条件**：setup 已完成，且当前阶段为 adr-create。

**行为**：

管理 ADR 文档：创建新 ADR、查看列表、编辑已有 ADR。arch 阶段是**高人工介入**阶段，ADR 创建需要架构师深度思考和审查，本阶段不提供自动化生成。

**展示当前 ADR 状态**：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# ADR-0016: read DISCOVERED_ADR_DIR set by Phase 1 Step 5; fallback to docs/adr
ADR_DIR="$PROJECT_ROOT/${DISCOVERED_ADR_DIR:-docs/adr}"

echo "=== ADR 文档管理 ==="
echo ""

# 统计 ADR 数量
ADR_COUNT=$(ls -d "$ADR_DIR/ADR-0"*.md 2>/dev/null | grep -v "ADR-0000-template" | wc -l)
echo "当前 ADR 数量: $ADR_COUNT"

# 列出最新 5 个 ADR
echo ""
echo "现有 ADR 列表 (最新 5 个):"
if [ "$ADR_COUNT" -gt 0 ]; then
    ls -t "$ADR_DIR"/${DISCOVERED_ADR_PATTERN:-ADR-*.md} 2>/dev/null | grep -v "ADR-0000-template" | head -5 | while read -r adr_file; do
        name=$(basename "$adr_file" .md)
        title=$(grep -m1 "^# " "$adr_file" 2>/dev/null | sed 's/^# //' | head -c 60)
        status=$(grep -m1 "状态" "$adr_file" 2>/dev/null | head -c 30)
        echo "  - $name: $title [$status]"
    done
else
    echo "  (暂无 ADR)"
fi
```

**菜单示例**：

```
=== ADR 文档管理 ===

当前 ADR 数量: 3
最新 ADR:
  - ADR-0003: 三阶段架构重构 (arch → plan → ship) [已采纳]
  - ADR-0002: 目标驱动接口与交互模式配置 [已采纳]
  - ADR-0001: rdd-workflow 状态机分相 [已替代为 ADR-0002+0003]

请选择:
  1. 创建新 ADR（从模板复制）
  2. 查看完整 ADR 列表
  3. 查看指定 ADR 详情
  4. 编辑已有 ADR
  5. ✅ 完成 ADR 阶段 → 进入 architecture 分析
  0. 💾 保存并退出
  i. 其他输入
```

**用户输入处理（case handler）**：

```bash
# Phase 2 adr-create menu - shared handler (extracted from inline case block)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_roadmap_menu.sh"
handle_arch_menu "$choice"
[ $? -eq 2 ] && continue  # r|refresh -> 重新展示菜单
```

**选项 1（创建新 ADR）执行内容**：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ADR_DIR="$PROJECT_ROOT/docs/adr"
TEMPLATE="$ADR_DIR/ADR-0000-template.md"

# 找到下一个可用编号
NEXT_NUM=$(ls -d "$ADR_DIR"/${DISCOVERED_ADR_PATTERN:-ADR-*.md} 2>/dev/null | grep -v "ADR-0000-template" | sed 's|.*/ADR-||;s|\.md$||' | sort -n | tail -1)
NEXT_NUM=${NEXT_NUM:-0}
NEXT_NUM=$((NEXT_NUM + 1))
NEXT_NUM_PADDED=$(printf "%04d" "$NEXT_NUM")

echo "📝 创建新 ADR: ADR-$NEXT_NUM_PADDED"
echo ""
echo "请提供 ADR 标题 (kebab-case, ≤ 50 字符):"
read -r ADR_SLUG

if [ -z "$ADR_SLUG" ]; then
    echo "❌ 标题不能为空"
    continue
fi

# 复制模板并替换占位符
NEW_ADR="$ADR_DIR/ADR-$NEXT_NUM_PADDED-$ADR_SLUG.md"
cp "$TEMPLATE" "$NEW_ADR"

# 替换标题占位符
sed -i "s/ADR-NNNN: <标题>/ADR-$NEXT_NUM_PADDED: <$ADR_SLUG>/" "$NEW_ADR"
sed -i "s/^> \*\*编号\*\*: NNNN/> **编号**: $NEXT_NUM_PADDED/" "$NEW_ADR"

echo "✅ 已创建: $NEW_ADR"
echo "   请编辑该文件完成 ADR 内容"
```

**选项 3（查看指定 ADR 详情）执行内容**：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ADR_DIR="$PROJECT_ROOT/docs/adr"

# 列出所有 ADR 供选择
ls -t "$ADR_DIR"/${DISCOVERED_ADR_PATTERN:-ADR-*.md} 2>/dev/null | grep -v "ADR-0000-template" | head -10 | nl -w2 -s". "
echo ""
echo "请输入 ADR 编号 (1-10):"
read -r adr_choice

SELECTED=$(ls -t "$ADR_DIR"/${DISCOVERED_ADR_PATTERN:-ADR-*.md} 2>/dev/null | grep -v "ADR-0000-template" | sed -n "${adr_choice}p")
if [ -z "$SELECTED" ]; then
    echo "❌ 无效选择"
    continue
fi

echo "=== $(basename "$SELECTED") ==="
cat "$SELECTED"
```

**与 architecture 阶段的衔接**：

用户选择「完成 ADR 阶段」后，进入 Phase 3 (architecture) 进行架构差距分析。arch 阶段内部可形成循环：adr-create → architecture → roadmap-define → adr-create（循环细化）。

---

## Phase 3: architecture

**入口条件**：adr-create 阶段完成（或用户跳过 ADR 直接进入此阶段）。

**行为**：

生成/管理**架构差距分析文档**（`docs/architecture/*-gap-analysis.md`）。差距分析是 arch 阶段的核心交付物之一——通过对比当前架构与目标架构（ADR 中定义的），识别需要补齐的差距。

**展示当前架构文档状态**：

```bash
 PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
 # ADR-0016: read DISCOVERED_ARCHITECTURE_DIR set by Phase 1 Step 5; fallback to docs/architecture
 ARCH_DIR="$PROJECT_ROOT/${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"

 echo "=== 架构差距分析 ==="
 echo ""

# 检查架构目录是否存在
if [ ! -d "$ARCH_DIR" ]; then
    echo "⚠️  架构目录不存在: $ARCH_DIR"
    echo "   将在选项 1 首次生成时创建"
    mkdir -p "$ARCH_DIR"
fi

# 列出已有差距分析
GAP_DOCS=$(ls "$ARCH_DIR/"*-gap-analysis.md 2>/dev/null)
GAP_COUNT=$(echo "$GAP_DOCS" | grep -c . || echo 0)

echo "现有架构差距分析: $GAP_COUNT"
if [ "$GAP_COUNT" -gt 0 ]; then
    echo ""
    echo "差距分析列表:"
    echo "$GAP_DOCS" | while read -r gap_file; do
        name=$(basename "$gap_file" .md)
        echo "  - $name"
    done
fi
```

**菜单示例**：

```
=== 架构差距分析 ===

现有架构差距分析: 2
  - v1-to-v2-migration-gap-analysis
  - loop-engine-design-gap-analysis

请选择:
  1. 生成新的架构差距分析
  2. 查看现有分析报告
  3. 编辑已有差距分析
  4. ✅ 完成架构分析 → 进入 roadmap-define
  0. 💾 保存并退出
  i. 其他输入
```

**用户输入处理（case handler）**：

```bash
# Phase 3 architecture menu - shared handler (extracted from inline case block)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_roadmap_menu.sh"
handle_arch_menu "$choice"
[ $? -eq 2 ] && continue  # r|refresh -> 重新展示菜单
```

**选项 1（生成新差距分析）执行内容**：

```bash
# Round B: extracted to _lib/arch_gap_analysis.sh (L343-L399)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_gap_analysis.sh"

echo "📝 生成新架构差距分析"
echo ""
echo "请提供差距分析主题 (kebab-case, ≤ 50 字符):"
read -r GAP_SLUG

generate_gap_analysis "$GAP_SLUG" || continue
```

**选项 2（查看现有分析）执行内容**：

```bash
# Round B: extracted to _lib/arch_gap_analysis.sh (L403-L431)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_gap_analysis.sh"
list_gap_analyses || continue

# Interactive viewer stays inline
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ARCH_DIR="$PROJECT_ROOT/${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"
GAP_DOCS=$(ls "$ARCH_DIR/"*-gap-analysis.md 2>/dev/null || true)

echo ""
echo "请输入要查看的编号 (1-$(echo "$GAP_DOCS" | wc -l)):"
read -r gap_choice

SELECTED=$(echo "$GAP_DOCS" | sed -n "${gap_choice}p")
if [ -z "$SELECTED" ]; then
    echo "❌ 无效选择"
    continue
fi

cat "$SELECTED"
```

**与 roadmap-define 阶段的衔接**：

用户选择「完成架构分析」后，进入 Phase 4 (roadmap-define) 定义路线图。差距分析是 roadmap 阶段的核心输入——roadmap 的任务分类与优先级应来源于差距分析。

---

## Phase 4: roadmap-define

**入口条件**：architecture 阶段完成（或用户跳过此阶段直接进入）。

**行为**：

定义/更新项目路线图。本阶段将所有路线图管理逻辑**委托给 `roadmap` 技能**，guide-arch 只负责调用入口与状态展示。

**检测现有路线图**：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# ADR-0016: read DISCOVERED_ROADMAP_PATH set by Phase 1 Step 5; fallback to roadmap.md
ROADMAP_FILE="$PROJECT_ROOT/${DISCOVERED_ROADMAP_PATH:-roadmap.md}"
STATE_FILE="$PROJECT_ROOT/.rddf/state/.roadmap-state.json"

echo "=== 路线图定义 ==="
echo ""

if [ -f "$ROADMAP_FILE" ]; then
    echo "✅ roadmap.md 已存在"
    echo "   位置: $ROADMAP_FILE"
    echo ""
    # 读取当前阶段
    CURRENT_PHASE=$(grep -m1 "当前阶段" "$ROADMAP_FILE" 2>/dev/null | head -c 80 || echo "(未指定)")
    echo "   当前阶段: $CURRENT_PHASE"
else
    echo "⚠️  未发现 roadmap.md"
    echo "   路线图用于管理项目阶段和 change 分类。"
    echo "   如果没有路线图，所有 change 将被标记为'未分类'。"
    echo ""
    echo "→ 自动调用 skill_use(\"roadmap\", \"init\") 进入模板选择..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    skill_use("roadmap", "init")
fi

# P1-6 兼容模式检测：当 roadmap.md 不存在但 .rddf/state/.roadmap-state.json 仍存在
# 说明: 之前启用过 roadmap,后来切换到兼容模式;或 roadmap.md 被误删/未提交
# 此时不自动恢复,只提示用户,避免误覆盖用户数据
if [ ! -f "$ROADMAP_FILE" ] && [ -f "$STATE_FILE" ]; then
    echo ""
    echo "⚠️  roadmap.md 已不存在，但 .rddf/state/.roadmap-state.json 存在"
    echo "   推测：roadmap 模式已切换为兼容模式"
    echo "   已有的 roadmap-meta.yaml 不会自动更新 .roadmap-state.json"
    echo "   如需重新启用 roadmap，请运行：skill_use(\"roadmap\", \"init\")"
fi
```

**菜单示例**：

```
=== 路线图定义 ===

当前状态: phase-1 (基础架构)
进度:
  - arch-design: 1/2 ✅
  - infra-setup: 0/1 ⏳
  - core-impl: 0/0

请选择:
  1. ✏️  编辑路线图（修改阶段或任务分类）
  2. 📊 查看路线图状态
  3. 📈 查看阶段门控报告
  4. ⏭️  强制推进到下一阶段
  5. ✅ 完成路线图定义 → 进入 arch validation
  0. 💾 保存并退出
  i. 其他输入
```

**用户输入处理（case handler）**：

```bash
# Phase 4 roadmap-define menu - shared handler (extracted from inline case block)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_roadmap_menu.sh"
handle_arch_menu "$choice"
[ $? -eq 2 ] && continue  # r|refresh -> 重新展示菜单
```

**选项 1（编辑路线图）执行内容**：

```bash
# 委托给 roadmap 技能
skill_use("roadmap", "edit")
```

**选项 2（查看路线图状态）执行内容**：

```bash
# 委托给 roadmap 技能
skill_use("roadmap", "status")
```

**选项 3（查看阶段门控报告）执行内容**：

```bash
# 委托给 roadmap 技能
skill_use("roadmap", "gate-report")
```

**选项 4（强制推进到下一阶段）执行内容**：

```bash
# 委托给 roadmap 技能
skill_use("roadmap", "advance")
```

**roadmap.md 缺失时的特殊行为**：

如果 `roadmap.md` 不存在，本阶段会自动调用 `skill_use("roadmap", "init")` 引导用户通过 4 个模板创建初始路线图：

1. C++ 库项目（基础 → 核心 → 高级）
2. Web 应用（MVP → 功能 → 优化）
3. 空白模板（自定义）
4. 基于现有 ADR 生成

详细模板内容见 `skills/roadmap.md` §命令：init。

**与 Phase 5 的衔接**：

用户选择「完成路线图定义」后，进入 Phase 5 (arch validation) 执行最终验证 + 提案审批 + 写 handoff。roadmap.md 是 arch-done 门控检查的两个关键文件之一（另一个是 ADR ≥ 1）。

---

## Phase 5: arch validation (门控检查)

**入口条件**：adr-create、architecture、roadmap-define 三个阶段都已完成（或用户主动跳过非必要阶段）。

**行为**：

执行 arch-done 双重门控检查，验证架构定义是否完整。门控通过后进入 Phase 5.5 提案审批，再进入 Phase 6 arch-done 退出。

**门控检查**：

arch-done 必须满足**双重门控**才能通过：

1. **ADR 数量 ≥ 1**（必须创建至少一个架构决策记录）
2. **roadmap.md 存在**（必须定义项目路线图）

```bash
# Round B: extracted to _lib/arch_done_gate.sh (L522-L559, ~38 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_done_gate.sh"
check_arch_done_gate || exit 1
```

**门控通过后**：

门控检查通过后，不直接退出，而是进入 Phase 5.5（提案审批）让用户审查 `improvements/` 目录下的待讨论提案。门控失败时提供回退选项。

**回退到其他 arch 阶段**：

门控失败时，user 可选择回到对应阶段补齐：

```
门控失败: ADR 数量为 0

请选择:
  1. ↩️  回到 adr-create 阶段创建 ADR
  2. ↩️  回到 roadmap-define 阶段定义路线图（如果 roadmap 缺失）
  3. 🔄 重新执行门控检查
  0. 💾 保存并退出
  i. 其他输入
```

**用户输入处理（case handler）**：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新执行门控检查
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  1) echo "-> 回到 adr-create 阶段..."; skill_use("guide-arch") ;;  # 重新调用,选择 adr-create
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

---

## Phase 5.5: 提案管理 — 创建 + 审批

**入口条件**：arch 阶段完成架构定义后（Phase 5 门控通过），用户选择进入提案管理。

**行为**：

1. **创建新改进提案** — 通过 `add-improve` 交互式创建 `improvements/<name>.md` 并注册到 `proposal-suggestions.md`
2. **审查待讨论提案** — 扫描 `proposal-suggestions.md` 索引表，逐一展示 `improvements/` 目录下的提案，支持批准/拒绝/延迟

**菜单**：

```
提案审批阶段

📂 improvements/ 目录中: X 个待审查提案

选择操作:
  1. ➕  创建新提案（add-improve 交互式创建）
  2. 📋 查看所有待审查提案
  3. ✅ 批量批准所有提案
  s   跳过审批，直接 arch-done
  q   返回上级菜单
```

**选项 1（创建新提案）**：

```bash
echo "-> 启动 add-improve 创建新改进提案..."
skill_use("add-improve")
# add-improve 会调用 rdd-workflow-brainstorm 完成设计 → 创建 improvements/<name>.md → 注册到 proposal-suggestions.md
echo "-> 创建完成，返回提案审批界面"
continue  # 重新展示提案列表
```

**执行步骤**：

```bash
# 加载共享函数
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/state.sh"

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
IMPROVEMENTS_DIR="$PROJECT_ROOT/improvements"
APPROVED_FILE="$PROJECT_ROOT/proposal-approved.md"
SUGGESTIONS_FILE="$PROJECT_ROOT/proposal-suggestions.md"

# 确定哪些提案在 suggestions 索引中但未在 approved 索引中
APPROVED_NAMES=""
if [ -f "$APPROVED_FILE" ]; then
  APPROVED_NAMES=$(grep -oP '\|\s*\[([^\]]+)\]\(improvements/' "$APPROVED_FILE" | sed 's/.*\[//;s/\].*//')
fi

echo "## 提案审批阶段"
echo ""
echo "📂 improvements/ 目录中的提案:"
echo ""

echo "🔍 检测已归档提案..."
ARCHIVED_COUNT=0
PENDING_COUNT=0
for f in "$IMPROVEMENTS_DIR"/*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .md)
  
  # 跳过已批准的
  if echo "$APPROVED_NAMES" | grep -qFx "$name"; then
    continue
  fi
  
  # 检测是否已归档：已归档的自动批准到 completed
  if ls -d "$PROJECT_ROOT/openspec/changes/archive/"*"-$name" 2>/dev/null | grep -q .; then
    priority=$(grep -m1 '^\*\*优先级\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*优先级\*\*: *//' | cut -d'|' -f1 | xargs)
    mark_approved_completed "$PROJECT_ROOT" "$name" 2>/dev/null
    ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
    continue
  fi
  
  PENDING_COUNT=$((PENDING_COUNT + 1))
  
  # 提取优先级和来源
  priority=$(grep -m1 '^\*\*优先级\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*优先级\*\*: *//' | cut -d'|' -f1 | xargs)
  source=$(grep -m1 '^\*\*优先级\*\*:' "$f" 2>/dev/null | sed 's/.*| \*\*来源\*\*: *//' | xargs)
  
  echo "  ${PENDING_COUNT}. [${priority:-?}] $name - ${source:-?}"
done

echo ""
if [ "$ARCHIVED_COUNT" -gt 0 ]; then
  echo "📦 已归档自动批准: $ARCHIVED_COUNT 个（跳过审查）"
fi
echo "📋 待审查: $PENDING_COUNT 个"

if [ "$PENDING_COUNT" -eq 0 ]; then
  echo "  (无待讨论提案)"
  echo ""
  echo "-> 跳过审批，直接进入 arch-done"
  return 0
fi

echo ""
echo "选择操作:"
echo "  <编号>        - 查看并审批该提案（批准/拒绝/延迟）"
echo "  a             - 全部批准"
echo "  s             - 跳过审批，直接 arch-done"
echo "  q             - 返回上级菜单"

# 用户选择
read -r CHOICE

case "$CHOICE" in
  q|quit|exit)
    return 0  # 返回上级菜单
    ;;
  s|skip)
    echo "-> 跳过提案审批"
    return 0
    ;;
  a|all)
    echo "批量批准所有提案..."
    for f in "$IMPROVEMENTS_DIR"/*.md; do
      [ -f "$f" ] || continue
      name=$(basename "$f" .md)
      if echo "$APPROVED_NAMES" | grep -qFx "$name"; then
        continue
      fi
      priority=$(grep -m1 '^\*\*优先级\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*优先级\*\*: *//' | cut -d'|' -f1 | xargs)
      bash "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/approve_proposal.sh" "$name" "${priority:-P1}" "$PROJECT_ROOT"
    done
    ;;
  *)
    # 处理编号选择
    # 展示单个提案内容并审批
    ;;
esac
```

**单个提案审批交互**：

```
提案: add-propose-content-review (P1)
来源: Oracle 架构分析 2026-07-21
分类: quality - 阶段: v2.1

## 架构依据
...

选择:
  y   - 批准（添加到 proposal-approved.md）
  n   - 拒绝（保留在 suggestions.md，标记 rejected）
  d   - 延迟（保持待讨论状态）
  s   - 跳过
```

批准时调用:
```bash
bash "$SCRIPT_DIR/scripts/approve_proposal.sh" "<name>" "<priority>" "$PROJECT_ROOT"
```

**与 Phase 6 的衔接**：

提案审批完成后（或用户选择跳过），进入 Phase 6 (arch-done) 写入 handoff 状态并退出。

---

## Phase 6: arch-done (Exit)

**入口条件**：Phase 5 门控检查通过 + Phase 5.5 提案审批完成（或跳过）。

**写入 handoff 状态**：

arch -> plan 交接通过 `.rddf/state/.arch-handoff.json` 软状态文件传递。arch-done 验证通过后立即写入。文件不被 git 跟踪（`.gitignore` 已排除 `.rddf/state/`），缺失时 plan 端硬阻断。v1 schema 见 `skills/_lib/schemas/arch_handoff_schema.json`（ADR-0016 Layer 2）。

```bash
# Round A: extracted to _lib/write_arch_handoff.{py,sh} (L618-L707, ~88 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/write_arch_handoff.sh"
write_arch_handoff
```

```bash
# rddf-session 关闭 hook (ADR-0017) - extracted to _lib/rddf_session_hooks.sh
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_close stage_arch arch-done guide-arch
```

**Output to user**：

```
✅ Arch-side complete. Architecture is defined.

📋 架构定义交付物:
  - ADR 文档: N 个 (最新: ADR-XXXX)
  - Roadmap: 已定义 (当前阶段: ...)
  - 架构差距分析: M 个 (待 roadmap 阶段补齐)
  - 已批准提案: K 个 (待 plan 阶段处理)

💡 Next: skill_use("guide-plan")
   This will consume approved proposals and start change generation (propose -> deps -> plan-done).
```

Do NOT auto-invoke `guide-plan` - the user must explicitly transition to the plan side.

**架构质量门（ADR-0018）**：

arch-done 双重门控（ADR ≥ 1 + roadmap.md 存在）通过后，自动运行 4 个 warning 级质量检查，输出到 `.rddf/state/.arch-quality-report.json`：

```bash
# Round B: extracted to _lib/arch_quality_report.sh (L564-L595, ~32 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_quality_report.sh"
run_arch_quality_report
```

**严格模式 (CI)**：当 `STRICT_ARCH_GATE=yes` 时，warning 自动升级为 error 并 exit 1。本地开发默认关闭。

---

## 阶段间循环与切换

arch 阶段内部支持**循环迭代**（细化架构）：

```
arch 内部循环:
  adr-create → architecture → roadmap-define → adr-create (循环细化)
```

arch → plan 的**前向切换**：

```
arch → plan: arch-done 验证通过 (ADR ≥ 1 + roadmap.md 存在)
```

plan → arch 的**反向切换**（v2.0 后续支持）：

```
plan → arch: plan 阶段选择"返回 Arch 阶段" (需要更新架构)
```

详细切换条件见 `docs/adr/ADR-0003-three-phase-architecture.md` §"阶段间循环与切换"。

---

## 测试与验证

本技能的状态契约可通过以下方式验证：

```bash
# 1. 验证 skill 文件存在且 frontmatter 完整
python3 -c "
import yaml
with open('skills/guide-arch.md') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'guide-arch'
assert meta['metadata']['user-invocable'] is True
print('✅ guide-arch.md frontmatter valid')
"

# 2. 验证子阶段齐全 (Phase 1-6 + Phase 5.5)
grep -E "^## Phase [0-9.]+:" skills/guide-arch.md

# 3. 验证 handoff 文件路径正确
grep "\.arch-handoff.json" skills/guide-arch.md

# 4. 验证 ADR 模板存在
ls docs/adr/ADR-0000-template.md

# 5. 验证 roadmap 文件存在
ls roadmap.md
```

<!-- 详细单元测试见 `tests/unit/test_guide_arch.py`（与本技能配套,待后续创建）。 -->

---

## 参考资料

- **ADR-0003** — 三阶段架构重构（arch → plan → ship），本技能的架构依据
- **ADR-0001** — 双阶段状态机分离（v1.x 架构，guide-spec 的来源）
- **ADR-0007** — 门控机制（arch-done 双重门控的设计依据）
- **ADR-0010** — 多会话管理（arch 阶段的人工介入设计）
- **ADR-0011** — 阶段步骤化执行模型（arch 阶段的子阶段设计）
- `skills/guide-spec.md` — v1.x spec 端状态机（本技能的 source）
- `skills/guide-ship.md` — ship 端状态机（参考模式）
- `skills/roadmap.md` — 路线图管理技能（被 arch Phase 4 调用）
- `docs/adr/ADR-0000-template.md` — ADR 模板（被 arch Phase 2 使用）
- `docs/adr/README.md` — ADR 索引与规范
