---
name: rdd-arch
description: Architecture definition phase state machine for OpenSpec workflow — guides user through setup, ADR creation, architecture analysis, roadmap definition, and emits arch-done handoff. Called when starting architecture work or after arch-done gate. Stage 3 rename from rdd-arch; canonical Stage 3+ identity per ADR-0042.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  version: "2.1.0"
  author: sisyphus
  evolved-from: "renamed from guide-arch.md v2.0 (Stage 3 D1a rename per ADR-0042)"
  user-invocable: true
  protocol_inline: true
  protocol_data_layer: "_lib/arch/protocol.py"
  protocol_output_contract: true
role:
  title: "Architect (架构治理者)"
  perspective: "Think in terms of long-term architectural coherence, ADR-driven decision-making, and roadmap alignment. Avoid premature implementation details."
  boundaries:
    owns:
      - "docs/adr/ADR-*.md"
      - "docs/architecture/*-gap-analysis.md"
      - ".rddf/state/.arch-handoff.json"
    not_owns:
      - "openspec/changes/<name>/{proposal,design,tasks}.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
      - ".rddf/state/.planner-feedback.json"
      - "roadmap.md"
      - ".rddf/roadmap/phases/*.md"
      - ".rddf/roadmap/features/*.md"
      - ".rddf/state/.populate-state.json"
  human_involvement: "high"
---

> **Stage 3 (2026-09-03)**: 此 skill 从 `guide-arch` 重命名为 `rdd-arch`（per D1a 渐进策略）。旧名称 `guide-arch` 通过 `skills/rdd-arch/SKILL.md` 的 5 行 shim 兼容至 v3.x + 2 minor release。
> `rdd-arch` 是 canonical name；本 skill 与 `rdd-planner`、`rdd-verifier` 命名对齐。
> 提案审批（v2.1 之前在 rdd-arch Phase 5.5）已迁移到 `rdd-planner` 阶段。

# rdd-workflow 工作流 — Arch-Side Guide

本技能是 rdd-workflow 工作流 v4.0+ 的 **arch 端状态机**：负责在生成 OpenSpec change artifacts 之前的**架构定义**工作——环境检测、ADR 文档管理、架构差距分析、路线图定义。arch 阶段是**四阶段架构**（`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`，per [ADR-0043](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md)）的第一阶段，专为高人工介入、低频执行的架构治理工作而设计。

> **演进历史**：v2.0 三阶段架构（arch → plan → ship，per ADR-0003）→ v2.1 扩展为四阶段（+ design，per ADR-0025）→ v3.0+ 扩展为 5-stage（+ verify，per ADR-0034）→ v4.0+ 合并为四阶段（per ADR-0043）。

**职责边界**：
- **角色定义**：见 frontmatter `role:` 字段（ADR-0028）
- **拥有**：`role.boundaries.owns` 字段列出的文件路径
- **不拥有**：`role.boundaries.not_owns` 字段列出的文件路径
- **人工介入程度**：`role.boundaries.human_involvement` = `high`

**调用方式**：

```
skill_use("rdd-arch")   # 无参数版本
```

---

## Architecture: v4.0+ 四阶段拆分（per ADR-0043，supersedes v3.0+ 5-stage per ADR-0034）

本技能是 OpenSpec 工作流 v4.0+ 重构后的 **arch 端**实现。在 v4.0+ 重构前，v3.0+ 历经五个职责清晰的子技能（per ADR-0025 + ADR-0034）；v4.0+ 合并为四阶段 + 1 旁路（per ADR-0043 + ADR-0047）。按**人工介入程度**和**职责类型**切分：

| 子技能 | 阶段 | 职责 | 人工介入 |
|--------|------|------|---------|
| `rdd-arch`（本技能） | Stage 1 — arch | 架构定义：setup → adr-create → architecture → roadmap-define → arch-validation → arch-done | **高** |
| `rdd-planner` | Stage 2 — planner | 路线图 + 提案治理：proposal authoring → review → approve/reject/defer → design-done（v3.0 design+plan 合并，per ADR-0038/0042/0043） | **中** |
| `rdd-builder` | Stage 3 — builder | 审批 + 执行 + 归档：6-phase 内部状态机 P0 (approval) → P1 (plan) → P1.5 (deps+exec_mode) → P2 (execute) → P2.5 (review) → P3 (archive with verifier retry)，per ADR-0043 stage-merge | **中→低** |
| `rdd-verifier` | Stage 4 — verifier | 验证回环：批量 AC 验证 + 启发式分类（implementation_gap vs proposal_drift） + bounded retry → verify-done（per ADR-0034；v2.0 自包含 LLM 验证 per ADR-0045） | **低** |
| `rdd-quick` | **旁路路径**（Bypass, per ADR-0047） | 小改动的快速执行：P0 (plan gen) → P1 (complexity triage) → P2 (in-place execute) → P3 (AC verify) → P4 (complete/retry/escalate)。跳过 openspec change + worktree | **中** |
| `guide`（无状态推荐器） | — | 扫描四阶段 + 旁路状态，推荐下一步 | — |

**核心边界（arch-done 即切换点）**：

```
[rdd-arch]  --(arch-done: ADR ≥ 1, 单门控 per ADR-0048)-->  [rdd-planner]  --(planner-done: roadmap存在 + recommended_route)-->  [rdd-builder]
   arch 端                                                planner 端                                          builder 端
   owns: docs/adr/ADR-*.md,                              owns: roadmap.md, proposal-suggestions.md,             owns: openspec/changes/<name>/
        docs/architecture/*-gap-analysis.md,                  proposal-approved.md,                              proposal.md (authoring via P0 approve),
        .rddf/state/.arch-handoff.json                        .rddf/roadmap/{features,phases}/*.md,             {design,tasks}.md, .rddf/wt/<name>/,
        (roadmap 完全不写 per ADR-0048)                       .rddf/improvements/*.md,                          .rddf/plans/<name>.md,
                                                              .rddf/state/.planner-{state,feedback,handoff}.json  .rddf/state/builder/<change>.json
   exits: .rddf/state/.arch-handoff.json                 exits: .rddf/state/.planner-handoff.json              exits: .rddf/state/builder/<change>.json
       --(user manual switch)--> [rdd-planner]         --(user manual switch)--> [rdd-builder P0-P3] --(archive)--> [rdd-verifier]

[rdd-quick]  --(P0-P4 in-place, no worktree)-->  [git commit on current branch]  (bypass, per ADR-0047 + ADR-0048 §Decision 3)
   ↑ 入口分两种: (a) rdd-builder P0 选项 5 (主路径, per ADR-0048)  (b) guide 推荐器直接调用 (旁路, self-triage)
```

**为什么这样切**（节选自 ADR-0003 + ADR-0048）：

- **职责单一**：arch 不需要懂 change artifacts，plan 不需要懂架构治理；roadmap 完全归 planner（per ADR-0048）
- **人工介入匹配**：高介入（arch，需要架构师审查）→ 中介入（plan，AI 辅助生成）→ 低介入（ship，自动执行）
- **架构治理前置**：v2.0 要求"先定义架构，再生成变更"，避免"跳过架构直接编码"
- **可独立演进**：修改 ADR 格式不影响 change 生成流程；roadmap 演进由 planner 全权负责
- **可独立测试**：arch-done 是清晰契约（用 ADR 数量验证，单门控 per ADR-0048）
- **角色边界严格**（per ADR-0028 + ADR-0048）：rdd-arch 与 roadmap 完全解耦；rdd-planner 通过 `.planner-handoff.json::recommended_route` 向 rdd-builder P0 输出复杂度 advisory

**arch 端不写的文件**：

- 不写 `openspec/changes/<name>/` 下任何 artifact（属于 `rdd-builder`）
- 不创建 worktree（属于 `rdd-builder`）
- 不调用 `openspec new` / `openspec propose` 等执行类命令（属于 `rdd-builder`）
- 不做归档/清理（属于 `rdd-builder` + `rdd-verifier`）
- **不写 `roadmap.md`** (per ADR-0048, 移交给 `rdd-planner` Phase 0)
- **不写 `.rddf/roadmap/{features,phases}/*.md`** (per ADR-0048, 移交给 `rdd-planner`)
- **不写 `.rddf/state/.populate-state.json`** (per ADR-0048, 移交给 `rdd-planner`)
- **不写 `.rddf/state/.planner-feedback.json`** (per ADR-0042, 由 `rdd-planner` owns)

**arch 端必须写的文件**：

- 通过 adr-create 阶段生成/更新 `docs/adr/ADR-*.md`
- 通过 architecture 阶段生成/更新 `docs/architecture/*-gap-analysis.md`
- arch-done 时写入 `.rddf/state/.arch-handoff.json`

---

## Phase 1: setup

**入口条件**：用户调用 `skill_use("rdd-arch")` 后立即执行。

**rddf-session 入口 hook**（ADR-0017）：创建或查找当前 opencode session 的 `stage_arch` rddf-session：

```bash
# rddf-session 入口 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_entry stage_arch rdd-arch arch-phase arch-done .rddf/state/.arch-handoff.json
```

**Stage 3 行为（per ADR-0042）**: 入口后展示 rdd-arch 状态 + planner 反馈摘要。

```bash
rddf arch status --project-root "$PROJECT_ROOT"
# 例: rdd-arch: phase-1 | 3 ADRs | Planner: 1 critical, 0 warning, 1 stale
# 或: rdd-arch: (no arch-done yet) | Planner: No planner feedback
```

planner 反馈**仅 advisory**，不阻断 arch-done 门控（per ADR-0042 边界契约）。

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

✅ Env OK (cached 23m ago) | ADR:63 | Roadmap:✓

工件发现 (ADR-0016):
   ADR 目录:      docs/adr (true)
   ADR 模式:      ADR-*.md
   Roadmap:       roadmap.md (true)
   Architecture:  docs/architecture (true)

当前状态: arch 阶段初始化完成

请选择:
1. ✅ 继续 → 进入 adr-create 阶段
2. 🔄 重新检查
0. 💾 保存并退出
i. 其他输入
```

**用户输入处理（case handler）**：

```bash
case "$choice" in
  1) echo "-> 进入 adr-create 阶段..." ; echo "(跳转到 Phase 2 入口)" ;;
  r|refresh) continue ;;
  *) source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_roadmap_menu.sh"; handle_arch_menu "$choice"; [ $? -eq 2 ] && continue ;;
esac
```

> 📌 提案审批（原 Phase 5.5 选项 3）已迁移到 `skill_use("guide-design")`。

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
ADR_COUNT=$(ls -d "$ADR_DIR/ADR-0"*.md 2>/dev/null | grep -v "ADR-0000-template" | wc -l | tr -d '[:space:]')
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
  - ADR-0003: 三阶段架构重构 (arch → plan → ship) [已采纳, v3.0+ 已演进为 5-stage per ADR-0034]
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

# 门禁分类 (adr_gate.sh; SKIP_ADR_GATE=yes 旁路 → 直接按 ARCHITECTURE)
GATE_CLASS=$(bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "$ADR_SLUG")

NEW_ADR="$ADR_DIR/ADR-$NEXT_NUM_PADDED-$ADR_SLUG.md"
trap 'rm -f "${NEW_ADR}.tmp"' EXIT ERR

case "$GATE_CLASS" in
  ARCHITECTURE)
    # ── 段 1: 现状挖掘 (agent 自动, 不向用户提问可查事实) ──
    #   已有相关 ADR: ls "${DISCOVERED_ADR_DIR:-docs/adr}"/${DISCOVERED_ADR_PATTERN:-ADR-*.md} | grep -v 0000-template
    #   架构文档:     find "${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}" -type f
    #   代码模式:     grep -l "$ADR_SLUG" docs/adr/ 2>/dev/null
    #   输出 3 段式摘要: 已有相关 ADR / 架构文档 / 代码模式

    # ── 段 2: 决策对话 (严格 3-5 轮, 一次一问 + 附推荐答案) ──
    DIALOGUE_ROUND=0
    CANCELLED=no
    while [ "$DIALOGUE_ROUND" -lt 5 ] && [ "$CANCELLED" = "no" ]; do
      DIALOGUE_ROUND=$((DIALOGUE_ROUND + 1))
      echo "决策点 $DIALOGUE_ROUND/5 (输入: y 接受推荐 / 改写文本 / s 跳过; q/cancel/exit 退出):"
      read -r DECISION_ANSWER
      case "$DECISION_ANSWER" in
        q|cancel|exit) echo "⏹ 退出对话 — 未写任何文件"; CANCELLED=yes ;;
        s) echo "⏭ 跳过该决策点" ;;
        *) echo "已记录: $DECISION_ANSWER" ;;
      esac
    done
    if [ "$CANCELLED" = "yes" ]; then
      continue  # 返回菜单, 不留半成品
    fi
    if [ "$DIALOGUE_ROUND" -ge 5 ]; then
      echo "⚠️  超过 5 轮 — 强制 break。是否继续? (y/n):"
      read -r CONTINUE_ROUND
      [ "$CONTINUE_ROUND" = "y" ] || echo "⏹ 以当前信息生成草稿"
    fi

    # ── 段 3: 草稿呈现 (对话中呈现完整草稿, 覆盖模板全部 section) ──
    #   元数据行:
    #     > **状态**: 待定
    #     > **日期**: $(date +%Y-%m-%d)
    #     > **决策者**: <name(s)>
    #   顶层 section:
    #     ## Context (含 **架构依据** 子项)
    #     ## Decision (含 ### 影响范围 + ### 备选方案)
    #     ## Consequences (含 ### 正面 + ### 负面 / 风险 + ### 后续待办)
    #     ## References
    #   agent 在对话中逐段呈现完整草稿, 等用户确认

    if [ "${SKIP_ADR_CONFIRM:-no}" != "yes" ]; then
      echo "确认草稿并写入 $NEW_ADR? (y/n, q/cancel/exit 取消):"
      read -r CONFIRM
      case "$CONFIRM" in
        q|cancel|exit|n) echo "⏹ 未写入任何文件"; continue ;;
      esac
    else
      echo "⏭ SKIP_ADR_CONFIRM=yes — 跳过确认直接落盘"
    fi

    # 原子写: temp + rename
    cp "$TEMPLATE" "${NEW_ADR}.tmp"
    sed -i "s/ADR-NNNN: <标题>/ADR-$NEXT_NUM_PADDED: <$ADR_SLUG>/" "${NEW_ADR}.tmp"
    sed -i "s/^> \*\*编号\*\*: NNNN/> **编号**: $NEXT_NUM_PADDED/" "${NEW_ADR}.tmp"
    mv "${NEW_ADR}.tmp" "$NEW_ADR"
    echo "✅ 已创建: $NEW_ADR"
    ;;
  GOVERNANCE)
    echo "⚠️  该议题偏向治理/流程决策, 更适合: RELEASE.md / ci-cd.md / CONTRIBUTING.md"
    echo "   仍要创建 ADR? (y/n):"
    read -r GOV_CONFIRM
    [ "$GOV_CONFIRM" = "y" ] || continue
    cp "$TEMPLATE" "$NEW_ADR"
    sed -i "s/ADR-NNNN: <标题>/ADR-$NEXT_NUM_PADDED: <$ADR_SLUG>/" "$NEW_ADR"
    echo "✅ 已创建: $NEW_ADR"
    ;;
  IMPLEMENTATION)
    echo "⛔ 该议题是实现类工作, 不应写成 ADR。"
    echo "   替代路径: docs/ 文档 / .github/ 配置 / tasks.md 任务 / roadmap.md 子任务"
    continue
    ;;
esac
trap - EXIT ERR
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
GAP_COUNT=$(echo "$GAP_DOCS" | grep -c . || true)

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

## Arch Gap Analysis Protocol

> 本节为 `cross-stage-protocol-template.md` Analyzer Subset 的首个落地（per ADR-0046）。Analyzer Subset 是 deterministic human-curated analyzer 的协议模式，与 LLM-as-judge verifier 共享 §1（协议块）+ §2（数据层），§3/§4 永久 skip，§5 repurposed 为 Output Contract Validation（结构=硬 / 完成度=advisory）。

**数据层**：`skills/rdd-arch/scripts/arch_gap_analysis.sh`（薄 bash wrapper，Oracle C1 env-var passing）→ 委托 `_lib/arch/protocol.py`（3 纯函数 + `ValidationReport` dataclass）。

**5 节 markdown 契约**（生成时硬约束）：

| § | 中文标题 | 用途 |
|---|----------|------|
| 1 | 目标架构 | 引用 ADR 描述的目标状态 |
| 2 | 当前架构 | 项目实际架构快照 |
| 3 | 差距清单 | 表格：`# / 差距项 / 严重程度 / 优先级 / 关联 change` |
| 4 | 补齐路径 | 从当前到目标的迁移步骤 |
| 5 | 参考资料 | 关联 ADR + change artifacts |

**Output Contract Validation**（advisory 不阻断）：

- `validate_document(path)` → `ValidationReport(structural_ok, completeness, issues)`
- `structural_ok = False` → generator drift（已封堵，8 个 bats 锁定）
- `completeness ∈ {draft, partial, complete}` → 仅 advisory；人工异步策展不阻断 arch-done
- arch-done Phase 5 接线 validation 已 defer 至独立 future change（per ADR-0046 out-of-scope）

**slug 校验**（Oracle concern #3）：slug 必须 kebab-case（lowercase alphanumeric + single hyphen），否则 `ValueError`。

---

## Phase 4: arch validation (门控检查) (renumbered per ADR-0048)

**入口条件**：adr-create、architecture 两个阶段都已完成（或用户主动跳过非必要阶段）。

> **变更 (per ADR-0048, 2026-09-09)**: 原 Phase 4 roadmap-define 已**完全删除**. Roadmap 创建与管理职责已移交至 `rdd-planner` Phase 0 roadmap-bootstrap + `roadmap` 技能. arch-done 门控从双重降为单重 (仅 ADR ≥ 1, 不再检查 `roadmap.md` 存在).

**行为**：

执行 arch-done 单门控检查，验证架构定义是否完整。门控通过后进入 Phase 5 arch-done 退出。

**门控检查**：

arch-done 必须满足**单门控**才能通过 (per ADR-0048 §Decision 1):

1. **ADR 数量 ≥ 1** (必须创建至少一个架构决策记录)

> **Roadmap 检查已移除**: `.rddf/roadmap.md` 存在性检查由 `rdd-planner` Phase 5 双门控接管 (per ADR-0048 §Decision 2). arch-done 不再关心 roadmap.

```bash
# Round B: extracted to _lib/arch_done_gate.sh (L522-L559, ~38 lines, ADR-0048: 移除 roadmap 检查)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_done_gate.sh"
check_arch_done_gate || exit 1
```

**门控通过后**：

门控检查通过后，直接进入 Phase 5 arch-done 写入 handoff 状态并退出。

门控失败时提供回退选项。

**回退到其他 arch 阶段**：

门控失败时，user 可选择回到对应阶段补齐：

```
门控失败: ADR 数量为 0

请选择:
  1. ↩️  回到 adr-create 阶段创建 ADR
  2. 🔄 重新执行门控检查
  0. 💾 保存并退出
  i. 其他输入
```

**用户输入处理（case handler）**：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新执行门控检查
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  1) echo "-> 回到 adr-create 阶段..."; skill_use("rdd-arch") ;;  # 重新调用,选择 adr-create
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

---

## Phase 5: arch-done (Exit) (renumbered per ADR-0048)

**入口条件**：Phase 4 门控检查通过。arch-done 不再依赖提案审批结果。

> **变更 (per ADR-0048, 2026-09-09)**: 原 Phase X Roadmap Sync 已**完全删除**. 不再调用 `roadmap_incremental_update.sh`. `.rddf/state/.populate-state.json` 改由 `rdd-planner` 维护.

**写入 handoff 状态**：

arch -> plan 交接通过 `.rddf/state/.arch-handoff.json` 软状态文件传递。arch-done 验证通过后立即写入。文件不被 git 跟踪（`.gitignore` 已排除 `.rddf/state/`），缺失时 plan 端硬阻断。v1 schema 见 `_lib/schemas/arch_handoff_schema.json`（ADR-0016 Layer 2）。

```bash
# Round A: extracted to _lib/write_arch_handoff.{py,sh} (L618-L707, ~88 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/write_arch_handoff.sh"
write_arch_handoff
```

```bash
# rddf-session 关闭 hook (ADR-0017) - extracted to _lib/rddf_session_hooks.sh
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_close stage_arch arch-done rdd-arch
```

**Output to user**：

```
✅ Arch-side complete. Architecture is defined.

📋 架构定义交付物:
  - ADR 文档: N 个 (最新: ADR-XXXX)
  - 架构差距分析: M 个 (待 planner 阶段补齐)

💡 Next: skill_use("rdd-planner")
   This will bootstrap the roadmap (if missing), manage sprint proposals, and prepare
   for builder execution. Per ADR-0048, rdd-arch no longer owns roadmap — rdd-planner
   Phase 0 will guide you through roadmap creation if needed.
```

Do NOT auto-invoke `rdd-planner` - the user must explicitly transition. (per ADR-0048)

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
  adr-create ↔ architecture  (细化架构; roadmap 已移交给 planner per ADR-0048)
```

arch → planner 的**前向切换**：

```
arch → planner: arch-done 验证通过 (单门控: ADR ≥ 1, per ADR-0048)
                  roadmap 由 rdd-planner Phase 0 bootstrap (如缺失)
```

plan → arch 的**反向切换**（v2.0 后续支持）：

```
plan → arch: plan 阶段选择"返回 Arch 阶段" (需要更新架构)
           rdd-planner 通过 .planner-feedback.json 提供 advisory 信号 (per ADR-0042)
```

详细切换条件见 `docs/adr/ADR-0003-three-phase-architecture.md` §"阶段间循环与切换" + `docs/adr/ADR-0048-v4-stage-merge-revision.md` §Decision 1。

---

## 测试与验证

本技能的状态契约可通过以下方式验证：

```bash
# 1. 验证 skill 文件存在且 frontmatter 完整
python3 -c "
import yaml
with open('skills/rdd-arch.md') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'rdd-arch'
assert meta['metadata']['user-invocable'] is True
print('✅ rdd-arch.md frontmatter valid')
"

# 2. 验证子阶段齐全 (Phase 1-6)
grep -E "^## Phase [0-9]+:" skills/rdd-arch.md

# 3. 验证 handoff 文件路径正确
grep "\.arch-handoff.json" skills/rdd-arch.md

# 4. 验证 ADR 模板存在
ls docs/adr/ADR-0000-template.md

# 5. 验证 roadmap 文件存在
ls roadmap.md
```

<!-- 详细单元测试见 `tests/unit/test_guide_arch.py`（与本技能配套,待后续创建）。 -->

---

## 参考资料

- **ADR-0003** — v2.0 三阶段架构（arch → plan → ship）的奠基 ADR；v2.1 扩展为四阶段（+ design）见 ADR-0025；v3.0+ 扩展为 5-stage（+ verify）见 ADR-0034；v4.0+ 合并为四阶段见 ADR-0043
- **ADR-0001** — 双阶段状态机分离（v1.x 架构，guide-spec 的来源）
- **ADR-0007** — 门控机制（arch-done 双重门控的设计依据）
- **ADR-0010** — 多会话管理（arch 阶段的人工介入设计）
- **ADR-0011** — 阶段步骤化执行模型（arch 阶段的子阶段设计）
- `skills/guide-design.md` — v2.1 design 端状态机（后续阶段）
- `skills/guide-plan.md` — plan 端状态机（后续阶段，由 design-done 触发）
- `skills/guide-ship.md` — ship 端状态机（参考模式）
- `skills/roadmap.md` — 路线图管理技能（被 arch Phase 4 调用）
- `docs/adr/ADR-0000-template.md` — ADR 模板（被 arch Phase 2 使用）
- `docs/adr/README.md` — ADR 索引与规范

## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)

### Checklist (must satisfy exactly one)

- [ ] **Normal exit** → call `orchestrator_finalize` (always, on every exit)
- [ ] **Abnormal exit** → call `orchestrator_finalize` + `rddf report-issue --phase rdd-arch --exit-code <code> "<one-line>"`

### Triggers for "abnormal exit" (non-exhaustive)

- gate reports CRITICAL and it's not a usage-error / environment-error
- state machine branch enters an unexpected case
- agent cannot continue after 3 retries on the same step
- user explicitly says "this is wrong" while phase reports success

### NOT abnormal (do NOT report-issue)

- User-initiated SIGINT / SIGTERM (exit 130/143)
- Missing tools, network errors, permission errors (environment-error)
- Bad CLI flags, missing required arguments (usage-error)
