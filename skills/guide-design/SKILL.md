---
name: guide-design
description: Design phase state machine for OpenSpec workflow — guides user through arch-handoff context display, add-improve proposal creation, proposal review (approve/reject/defer), design-done gate, and emits design-handoff. Called after arch-done or when creating improvement proposals.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "extracted from guide-arch.md v2.0 Phase 5.5"
  user-invocable: true
---

# rdd-workflow 工作流 — Design-Side Guide

本技能是 rdd-workflow 工作流 v2.1 的 **design 端状态机**：负责在构架定义之后、变更生成之前的设计管理工作——创建改进提案、审查未审批提案、批准/拒绝/延迟决策、设计完成交接。design 阶段是三阶段架构（arch → design → plan → ship）的第二阶段，专为中介入、提案管理而设计。

**职责边界**：
- **拥有**：`improvements/<name>.md`（提案文件）、`proposal-suggestions.md`（提案池索引）、`proposal-approved.md`（已批准提案索引，与 guide-plan 共享读取）
- **不拥有**：`docs/adr/ADR-*.md`（属于 `guide-arch`）、`openspec/changes/<name>`（属于 `guide-plan`）、git worktree（属于 `guide-ship`）
- **状态持久化**：design-done 时写入 `.rddf/state/.design-handoff.json`（不被 git 跟踪，plan 端硬依赖）
- **人工介入程度**：**中** —— design 阶段 AI 辅助提案审查，用户做决策（批准/拒绝/延迟）

**调用方式**：
```
skill_use("guide-design")   # 无参数版本
```

## Architecture: v2.1 四阶段拆分

| 子技能 | 阶段 | 职责 | 人工介入 |
|--------|------|------|---------|
| `guide-arch`（前序） | arch | 架构定义：setup → adr-create → architecture → roadmap-define → arch-done | **高** |
| `guide-design`（本技能） | design | 设计管理：提案创建 → 审查 → 批准/拒绝/延迟 → design-done | **中** |
| `guide-plan`（后续） | plan | 变更生成：审批提案消费 → propose → deps → plan-done | **中** |
| `guide-ship`（后续） | ship | 变更执行：plan → execute → archive → cleanup → ship-done | **低** |

**核心边界（design-done 即切换点）**：
```
[guide-arch] --(arch-done)--> [guide-design] --(design-done)--> [guide-plan] --(plan-done)--> [guide-ship]
```

## Phase 1: setup

**入口条件**：用户调用 `skill_use("guide-design")` 后立即执行。

**rddf-session 入口 hook**（ADR-0017）：创建或查找当前 opencode session 的 `stage_design` rddf-session（parent=latest stage_arch）：

```bash
# rddf-session 入口 hook (ADR-0017) - extracted to _lib/rddf_session_hooks.sh
# stage_design parent: latest stage_arch (auto-resolved by helper)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
rddf_session_hook_entry stage_design guide-design design-phase design-done .rddf/state/.design-handoff.json
```

**硬依赖检查**：`.rddf/state/.arch-handoff.json` 必须存在。缺失时拒绝并提示先运行 `skill_use("guide-arch")`：

```bash
if [ ! -f ".rddf/state/.arch-handoff.json" ]; then
  echo "❌ arch-done 未完成，无法进入 design 阶段"
  echo "   请先运行: skill_use(\"guide-arch\")"
  return 1
fi
```

**环境健康快照**（rdd-env-check cache 接入，命中输出单行）：

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/design_env_check.sh"
run_design_env_check
```

**展示 arch 上下文**：

```
📋 架构上下文:
  - ADR 数量: N 个
  - 路线图阶段: phase-1
  - 差距分析: M 个
```

## Phase 2: 提案管理

**入口条件**：Phase 1 环境检查通过后直接进入。

**菜单**：
```
设计阶段 - 提案管理

📂 提案池:
  - 待审查: N 个
  - 已归档(自动批准): M 个
  - 已推迟: K 个（按 v 查看全部）

选择操作:
  1. ➕ 创建新提案（add-improve 交互式创建）
  2. 📋 审查待批准提案
  3. ✅ 批量批准所有提案
  4. ✅ 完成设计阶段 → 进入设计门控
  0. 💾 保存并退出
```

**选项 1（创建新提案）**：
```bash
echo "-> 启动 add-improve 创建新改进提案..."
skill_use("add-improve")
echo "-> 创建完成，返回提案列表"
continue
```

## Phase 3: 提案审查

**入口条件**：用户从 Phase 2 菜单选择选项 2，或调用 `design_proposal_review.sh`。

**行为**：调用 `skills/guide-design/scripts/design_proposal_review.sh` 执行双源扫描和审查交互。

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/design_proposal_review.sh"
design_proposal_review "$PROJECT_ROOT" "phase1"
```

审查支持：y(批准)/n(拒绝)/d(延迟)/s(跳过)/a(全部批准)。批准时调用 `skills/guide-design/scripts/approve_proposal.sh`。

### D1 编排: generate → confirm → fall-through

v2.0.6+ 起，批准动作升级为「生成完整 proposal.md → 用户确认 → 落盘」(D1 of move-proposal-creation-to-design)。
approve_proposal.sh 在落盘前提供以下两步编排：

#### Step 1: 生成 proposal.md 草稿
```bash
CHANGE_NAME="<name>" IMPROVEMENTS_PATH="$PROJECT_ROOT/improvements/<name>.md" \
    python3 "$PROJECT_ROOT/skills/guide-design/scripts/generate_full_proposal.py" \
    > /tmp/proposal-draft.md
```

`generate_full_proposal.py` 按 D2 映射将 improvements 5 段转换：
- 架构依据 → ## Why
- 范围 + 关键场景 → ## What Changes (In/Out Scope)
- 技术约束 → ## Capabilities / ## Impact
- 验收标准 → ## Acceptance (checkboxes 保留)

#### Step 2: 用户确认
**AI 不自动确认** — 必须由用户明确同意。

```bash
echo "━━━ 生成的 proposal.md 草稿 ━━━"
cat /tmp/proposal-draft.md
echo ""
echo "接受并继续? [y/N]: "
read -r user_reply
```

#### Step 3: 落盘 + 状态写入
on `y`：
```bash
# 由 approve_proposal.sh 完成（无需手动调用）
# - mkdir openspec/changes/<name>/
# - .openspec.yaml + proposal.md (full version)
# - roadmap-meta.yaml (含 change_type, 从 improvements head 解析)
# - iteration.json (status=planned, idempotent)
# 检查人工 hook: DESIGN_PROPOSAL_AUTO_ACCEPT=no 时(y/N 需手工回答)
```

回落到 approve_proposal.sh 的现有追加逻辑 + 状态写入。
若 `SKIP_DESIGN_HANDOFF=yes` 既存路径:跳过创建，留给 plan 阶段处理。

design 两层内容审查（warning 默认）:
- improvements 层: `skills/guide-design/scripts/design_content_review.sh`
- openspec proposal 层: `skills/propose/scripts/propose_quality_check.py::run_design_checks`
  (D5:仅 3 项 proposal-level 检查,不含 tasks/roadmap)

`STRICT_DESIGN_GATE=yes` 升级 warning 为阻断;`SKIP_CONTENT_REVIEW=yes` 跳过整个审查。

## Phase 4: design-done 门控

**入口条件**：用户从 Phase 2 菜单选择选项 4，或所有提案审查完毕。

**设计门控检查**：遍历 `proposal-suggestions.md`，所有条目的 `状态` 列必须在 {已批准, 已拒绝, 延迟} 中。

```bash
check_design_done_gate() {
  local pending=$(grep -E '^\s*\|\s*\[' "$PROJECT_ROOT/proposal-suggestions.md" 2>/dev/null | \
    while IFS='|' read -r _ _ _ _ _ status _; do
      status=$(echo "$status" | xargs)
      if [ "$status" != "已批准" ] && [ "$status" != "已拒绝" ] && [ "$status" != "延迟" ]; then
        echo "$status"
      fi
    done)
  if [ -n "$pending" ]; then
    echo "❌ design-done 失败: 以下提案尚无决策:"
    echo "$pending"
    return 1
  fi
  echo "✅ 所有提案已有决策，design-done 门控通过"
  return 0
}
```

门控通过后写入 handoff。失败时列出未决策提案并返回 Phase 2 菜单。

## Phase 5: design-done (Exit)

**入口条件**：Phase 4 门控检查通过，且用户确认退出。

**写入 handoff 状态** (v2 schema with changes_pre_created)：
```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/write_design_handoff.sh"
# Collect change names created during this design session (approved + auto-created)
# Pass as positional args (preferred) or via CHANGES_PRE_CREATED env var
write_design_handoff "$proposals_reviewed" ${created_change_names[@]}
```

**rddf-session 关闭 hook**：
```bash
# rddf-session 关闭 hook (ADR-0017) - graceful degradation when skill_root.sh missing
source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/_lib/skill_root.sh"
if command -v resolve_rdd_skill_dir >/dev/null 2>&1; then
    source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
    rddf_session_hook_close stage_design design-done guide-design
else
    echo "⚠️  resolve_rdd_skill_dir 不可用, 跳过 rddf-session 关闭 hook (graceful degradation)" >&2
fi
```

**Output to user**：
```
✅ Design phase complete.

📋 设计阶段交付物:
  - 提案审查: N 个 (已批准: K, 已拒绝: R, 延迟: D)
  - 已批准提案: 写入 proposal-approved.md

💡 Next: skill_use("guide-plan")
```

## 重复运行处理

- 如果 `.rddf/state/.design-handoff.json` 已存在且无新增待审提案 → NOOP，提示 "design-done 已完成，无新提案"
- 如果存在新增待审提案 → 仅审查新增条目，完成后更新 handoff（覆盖写，时间戳刷新）