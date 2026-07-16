---
name: guide-plan
description: Change generation phase state machine for OpenSpec workflow — guides user through scan, propose, deps, and emits plan-done handoff. Called after arch-done or when creating new changes. Owns openspec/changes/<name>/ artifacts.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  version: "2.0"
  author: sisyphus
  evolved-from: "extracted from guide-spec.md v1.0 (Phase 2 + Phase 2.5)"
  user-invocable: true
---

# OpenSpec 工作流 — Plan-Side Guide

本技能是 OpenSpec 工作流 v2.0 的 **plan 端状态机**：负责在生成 OpenSpec change artifacts 阶段的**变更生成**工作——扫描候选、创建 change、依赖分析、变更生成完成交接。plan 阶段是三阶段架构（arch → plan → ship，ADR-0003）的第二阶段，专为中人工介入、AI 辅助生成场景设计。

**职责边界**：
- **拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md`（change artifacts）、`proposal-suggestions.md`（候选列表）
- **不拥有**：`docs/adr/ADR-*.md`（属于 `guide-arch`）、git worktree + Prometheus 计划（属于 `guide-ship`）
- **状态持久化**：plan-done 时写入 `.rddf/state/.plan-handoff.json`（不被 git 跟踪，缺失时 ship 端静默回退）
- **人工介入程度**：**中** —— plan 阶段 AI 辅助生成 change 提案，用户主要做决策（选择候选、确认依赖关系）

**调用方式**：

```
skill_use("guide-plan")   # 无参数版本
```

---

## Architecture: v2.0 三阶段拆分

本技能是 OpenSpec 工作流 v2.0 重构后的 **plan 端**实现。在 v2.0 重构前，所有 spec 端工作由单一 `guide-spec` 驱动；v2.0 拆分为三个职责清晰的子技能，按**人工介入程度**和**职责类型**切分：

| 子技能 | 阶段 | 职责 | 人工介入 |
|--------|------|------|---------|
| `guide-arch`（前序） | arch | 架构定义：setup → adr-create → architecture → roadmap-define → arch-done | **高** |
| `guide-plan`（本技能） | plan | 变更生成：scan → propose → deps → plan-done | **中** |
| `guide-ship`（后续） | ship | 变更执行：plan → execute → archive → cleanup → ship-done | **低** |
| `guide`（无状态推荐器） | — | 扫描三阶段状态，推荐下一步 | — |

**核心边界（arch-done 即切换点）**：

```
[guide-arch]  --(arch-done: ADR ≥ 1 + roadmap.md)-->  [guide-plan]  --(plan-done: ≥1 change + all artifacts committed)-->  [guide-ship]
    arch 端                                                 plan 端                                                ship 端
    owns: docs/adr/ADR-*.md, roadmap.md,                  owns: openspec/changes/<name>/                        owns: worktree, .rddf/plans/,
          docs/architecture/*-gap-analysis.md                    {proposal,design,tasks}.md                              execute, archive
    exits: .rddf/state/.arch-handoff.json                     exits: .rddf/state/.plan-handoff.json                     exits: 归档的 change 目录
```

**为什么这样切**（节选自 ADR-0003）：

- **职责单一**：plan 不需要懂架构治理（arch 端的事），也不需要懂 worktree 创建（ship 端的事）
- **人工介入匹配**：高介入（arch）→ 中介入（plan，AI 辅助生成 + 用户决策）→ 低介入（ship，自动执行）
- **可独立演进**：修改 change artifact 格式不影响 arch/ship 阶段
- **可独立测试**：plan-done 是清晰契约（用 change 数量 + artifacts 提交性验证）

**plan 端不写的文件**：

- 不写 `docs/adr/ADR-*.md`（属于 `guide-arch`）
- 不写 `roadmap.md`（属于 `guide-arch`）
- 不创建 worktree（属于 `guide-ship`）
- 不调用 `openspec` 的执行类命令（属于 `guide-ship`）
- 不做归档/清理（属于 `guide-ship`）

**plan 端必须写的文件**：

- 通过 scan 阶段生成/更新 `proposal-suggestions.md`（plan 端唯一持久化候选列表）
- 通过 propose 阶段创建 `openspec/changes/<name>/{proposal.md, design.md, tasks.md, .openspec.yaml}`
- 通过 deps 阶段生成 `.rddf/state/.deps-candidates.json`（输入契约）和 `.rddf/state/.deps-output.md`（分析输出）
- plan-done 时写入 `.rddf/state/.plan-handoff.json`（plan → ship 的软交接信号）

---

## Phase 1: scan

**入口条件**：用户调用 `skill_use("guide-plan")` 后立即执行；或 `guide-arch` 完成后用户主动切换到 plan 端。

**rddf-session 入口 hook**（ADR-0017）：创建或查找当前 opencode session 的 `stage_plan` rddf-session（parent=最新 stage_arch）：

```bash
# rddf-session 入口 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
# stage_plan parent: latest stage_arch (auto-resolved by helper)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/rddf_session_hooks.sh"
rddf_session_hook_entry stage_plan guide-plan plan-phase plan-done .rddf/state/.plan-handoff.json
```

**行为**：

执行环境检测，然后**将扫描完全委托给 `propose` 技能**。guide-plan 不直接扫描 ADR / 架构差距分析 / TODO / 测试缺口——所有扫描逻辑由 `propose` 技能统一处理。

**执行环境检测**：

```bash
# Round A: extracted to _lib/plan_intake.sh (L95-L175, ~79 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/plan_intake.sh"
run_plan_intake || exit 1
```

**扫描委托**：

```bash
# 将扫描完全委托给 propose 技能
# propose 会: 扫描 ADR → 扫描架构差距 → 扫描 TODO → 扫描测试缺口 → 生成 proposal-suggestions.md
skill_use("propose")
```

**环境状态展示**：

```
Plan 阶段环境检查结果：

✅ openspec CLI: 1.3.1 (/home/ubuntu/.npm-global/bin/openspec)
✅ git 工作区干净
📌 当前分支: master
📋 ADR 数量: 3 (from arch-handoff)
📋 Roadmap 阶段: phase-1
📋 ADR 编号: 0001,0003,0013
📋 当前活跃 changes: 0
✅ arch-done handoff 已验证 (硬交接)

请选择:
  1. 🔍 扫描新 change 候选（委托 propose）
  2. ➡️  跳过扫描，直接进入 propose（使用已有 proposal-suggestions.md）
  3. 🔄 重新检查环境
  0. 💾 保存并退出
  i. 其他输入
```

**用户输入处理（case handler）**：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新展示菜单
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

**步骤 2：进入对应阶段**

根据当前阶段跳转到对应入口。scan 完成后进入 Phase 2 (propose)。

---

## Phase 2: propose

**入口条件**：scan 阶段完成（proposal-suggestions.md 已生成或已存在）。

**行为**：

展示扫描结果，让用户从候选列表中选择并创建 change。本阶段**显示与执行分离**：guide-plan 负责展示候选列表和接收选择，但创建操作通过调用 `propose` 技能完成。

**展示当前已创建 changes**：

```bash
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
```

**读取 proposal-suggestions.md**：

```bash
if [ -f "proposal-suggestions.md" ]; then
    echo ""
    echo "📂 已有的建议列表 (proposal-suggestions.md)"
    # 用 python 解析后格式化输出（而不是 cat 原始 JSON）
    # 这样 description 字段的多行内容能正确显示
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
    echo "🆕 未发现 proposal-suggestions.md，请先回到 scan 阶段扫描"
    continue
fi
```

**队列概览**（v2.0.1 新增，调用 `iteration` 模块的 4 个 query 函数）：

```bash
# 5 队列可视化: 让用户一眼看到"我现在能做什么"
# 调用 iteration.list_planned/list_blocked/list_ready_for_ship
# 失败时降级为内联过滤, 不阻断菜单显示
echo ""
echo "📊 当前队列状态:"
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/state.sh"
PENDING_SUGGESTIONS_COUNT=$(count_pending_suggestions "$PROJECT_ROOT")
PY_PROJECT_ROOT="$PROJECT_ROOT" PENDING_SUGGESTIONS_COUNT="$PENDING_SUGGESTIONS_COUNT" python3 << 'PYEOF' 2>/dev/null
import os, sys, json
from datetime import datetime, timezone
project_root = os.environ.get("PY_PROJECT_ROOT", ".")

# P3-3b: candidates sourced from _lib/state.sh via env var (set by bash caller)
candidates = int(os.environ.get("PENDING_SUGGESTIONS_COUNT", "0"))

try:
    from skills._lib import iteration as it
    d = it.load(project_root)
    planned = it.list_planned(d)
    blocked = it.list_blocked(d)
    ready = it.list_ready_for_ship(d)
    changes_for_stale = d.get("changes", [])
except Exception:
    planned = blocked = ready = []
    changes_for_stale = []

now = datetime.now(timezone.utc)
stale = 0
for c in changes_for_stale:
    if c.get("status") not in ("proposed", "in_worktree"):
        continue
    last = c.get("last_deps_at")
    if not last:
        stale += 1
        continue
    try:
        age_hours = (now - datetime.fromisoformat(last.replace("Z", "+00:00"))).total_seconds() / 3600
        if age_hours > 24:
            stale += 1
    except (ValueError, TypeError):
        stale += 1

print(f"  🆕 候选: {candidates} [💡 选 1 个创建]")
print(f"  📋 骨架: {len(planned)}")
print(f"  ⏸️  阻塞: {len(blocked)} [⚠️ 等待 blocker 解除]")
ready_marker = " [✅ 满足 plan-done 门控]" if ready else ""
print(f"  🚀 可 ship: {len(ready)}{ready_marker}")
print(f"  ⚠️  deps 过期: {stale} [> 24h 未更新]")
PYEOF
```

**Feature 进度**（v2.0.1 新增，从 change name 前缀派生，无需 schema 变更）：

```bash
echo ""
echo "📌 Feature 进度:"
PY_PROJECT_ROOT="$PROJECT_ROOT" python3 << 'PYEOF' 2>/dev/null
import os, sys
try:
    from skills._lib import iteration as it
    d = it.load(os.environ.get("PY_PROJECT_ROOT", "."))
    progress = it.feature_progress(d)
except Exception:
    progress = {}

if not progress:
    print("  (无 multi-change feature)")
else:
    # 按完成比例升序排序（未完成的靠前）
    sorted_features = sorted(progress.items(), key=lambda kv: (kv[1][0] / kv[1][1]) if kv[1][1] > 0 else 0)
    for feature, (done, total) in sorted_features:
        if total == 0:
            continue
        if done == total:
            marker = "✅"
            note = "所有 sub-change 已归档"
        elif done == 0:
            marker = "⏳"
            note = f"尚未归档 ({total} 个子 change)"
        else:
            marker = "⚙️"
            remaining = total - done
            note = f"还有 {remaining} 个 sub-change 未归档"
        print(f"  {marker} {feature}: {done}/{total} {note}")
PYEOF
```

**菜单示例**：

```
=== Plan 阶段 - 变更生成 ===

当前项目状态:
  Active Changes: [N] 个
  Roadmap 阶段: [phase] (完成度: [N]%)

当前已创建的 Changes:
  - fix-ns-pollution  [Artifacts: ✅]
  - add-stream-pipes  [Artifacts: ⏳]

建议列表（来自 ADR 扫描 + 代码 TODO）:

🔴 高优先级
  1. fix-circular-deps — 修复循环依赖 (ADR-033, 3 个任务) [pending]
  2. add-stream-pipes  — 实现 Stream 管道操作符 (ADR-022, 5 个任务) [pending]

🟡 中优先级
  3. add-cdc-support   — 跨时钟域支持 (架构差距分析) [pending]

请选择操作:
  1. 扫描新 change 候选
  2. 创建 change (从 ADR/TODO/测试缺口)
  3. 填充骨架 change (fill) — 将 planned 升级为 proposed
  4. 运行依赖分析
  5. 查看 changes 状态
  6. 完成变更生成 → 进入 Ship 阶段
  0. 💾 保存并退出
  i. 手动输入 change 名称
```

**选项 2（创建 change）执行内容**：

```bash
if [ "$choice" = "2" ]; then
    # 询问用户要创建哪个候选
    echo "请输入要创建的 change 名称（或编号）:"
    read -r target_name

    # 验证输入
    if [ -z "$target_name" ]; then
        echo "❌ change 名称不能为空"
        continue
    fi

    # 委托给 propose 技能执行创建
    # propose 会: openspec new change → instructions → 创建 proposal.md/design.md/tasks.md
    skill_use("propose", "--create", "$target_name")

    echo "✅ Change '$target_name' 创建完成"
    echo "   请在 openspec/changes/$target_name/ 中查看 artifacts"
fi
```

**用户输入处理（case handler）**：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新展示菜单
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

**创建后循环**：

每次创建完成后，重新检查建议列表 + 活跃 changes，重新展示选项菜单（循环）。用户在 proposal-suggestions.md 中已选的候选会自动标记为 `[created]`。

**Propose 阶段完成条件**：

用户选择「6. 完成变更生成」后，验证至少有一个 change 的 artifacts 已提交（proposal.md、design.md、tasks.md 都通过 `git show HEAD:` 可访问），然后推进到 **deps 阶段**（依赖分析）。

**Propose → Deps 流程**：

```
用户选择「完成变更生成」
    ↓
验证 artifacts 已提交
    ↓
【自动执行】调用 deps.md 分析候选 change 依赖
    ↓
展示依赖图和推荐执行顺序
    ↓
guide-plan 阶段完成（plan-done）
    ↓
交接给 guide-ship
```

---

## Phase 2.5: fill

**入口条件**：deps 已运行（推荐），用户从 Phase 2 菜单选择「3. 填充骨架 change」。

**用途**：将已存在的 `planned` 状态 change（仅含骨架 artifacts）升级为 `proposed` 状态（完整 artifacts），按 deps 推荐的执行顺序（blocker 已清除者优先）。

**行为**：

1. 扫描 `openspec/changes/` 目录找出所有 `planned` 状态的 change
2. 读取 `.rddf/state/iteration.json` 获取每个的 blocker/parallel_group
3. 按 parallel_group 升序排序（无 blocker 的 group 0 优先）
4. 展示候选列表，让用户选择
5. 对选中的 change：
   - 读取 `proposal-suggestions.md` 中对应条目的 `description` 字段（完整需求描述）
   - 调用 `openspec instructions design --change "<name>" --json` 获取 design.md 模板
   - 写入 design.md
   - 调用 `openspec instructions tasks --change "<name>" --json` 获取 tasks.md 模板
   - 写入 tasks.md
   - 更新 `iteration.json`：`status` 从 `planned` → `proposed`
   - 更新 `proposal-suggestions.md`：条目 `status` 从 `skeleton` → `已完成`
6. 失败容错：单 change 填充失败不中断整体流程，继续下一个

**示例输出**：

```
=== Plan 阶段 - 填充骨架 change (fill) ===

📋 可填充的骨架 change（按 deps 推荐顺序）:
  1. fix-tcgen05-coverage (planned, parallel_group=0, no blockers)
  2. cleanup-wmma-namespace (planned, parallel_group=0, no blockers)
  3. tcgen05-docs (planned, parallel_group=1, blocked_by=fix-tcgen05-coverage)

请选择要填充的 change（多选用逗号分隔, 0 取消）:
```

**关键约束**：
- fill 不修改骨架 change 的 proposal.md（保留 Why + What Changes）
- fill 仅追加 design.md 和 tasks.md
- iteration.json 的更新由 `iteration.add_or_update_change()` 统一管理

---

## Phase 3: deps

**入口条件**：propose 阶段完成，用户选择「完成变更生成」后自动触发。

**前置说明**：

本阶段自动执行，不需要用户交互。所有结果通过 deps.md 生成。deps.md 是 OpenSpec 工作流的子技能，专门负责静态三轴分析 + AI 语义分析（实验性）+ Mermaid 依赖图生成。

**行为**：

1. **生成候选列表**：读取所有已提交的 change，生成 `.rddf/state/.deps-candidates.json`
2. **执行依赖分析**：调用 deps.md 分析 change 间依赖
3. **输出依赖图**：生成 `.rddf/state/.deps-output.md`，包含 Mermaid 依赖图和推荐执行顺序
4. **展示结果**：展示依赖图、冲突检测、推荐顺序

**自动执行内容**：

```bash
# Round B: extracted to _lib/plan_deps_candidates.{py,sh} (L451-L488, ~38 lines)
# Oracle C1 fix: bash wrapper passes PROJECT_ROOT env var only
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/plan_deps_candidates.sh"
generate_deps_candidates

# Step 2: 调用 deps.md 技能（静态三轴分析 + 子代理语义分析占位）
# deps.md 读取 .rddf/state/.deps-candidates.json，输出 .rddf/state/.deps-output.md
# 详细实现见 skills/deps.md
skill_use("deps")

# Step 3: 展示结果
echo "📊 依赖分析完成"
cat "$PROJECT_ROOT/.rddf/state/.deps-output.md"
```

**详细分析逻辑**（已迁移到 `skills/deps.md`）：

- **静态三轴分析**（文件冲突、ADR 引用、接口依赖）：见 `skills/deps.md` Step 2
- **Mermaid 图生成**（独立 change 用 subgraph、依赖用 `-->`、冲突用 `-.->|冲突|`）：见 `skills/deps.md` Step 5a
- **子代理语义分析**：见 `skills/deps.md` Step 3（占位符，后续独立 change 实现）
- **重组建议格式**（拆分/合并/重排）：见 `skills/deps.md` Step 5e

**契约**：

- **输入**: `.rddf/state/.deps-candidates.json`（Step 1 生成）
- **输出**: `.rddf/state/.deps-output.md`（由 deps.md 写入，由 Step 3 cat 展示）
- **错误处理**: 若 `.deps-candidates.json` 缺失，deps.md Step 0 退出 1，guide-plan 需在 Step 1 确保生成

**无用户交互**：本阶段自动完成。guide-plan 全部工作完成，输出 plan-done 退出信号。

---

## Phase 4: plan-done (Exit)

**入口条件**：用户选择「6. 完成变更生成」后，至少有一个 change 的 artifacts 已提交（`proposal.md`、`design.md`、`tasks.md` 都通过 `git show HEAD:...` 可访问），且门控检查通过。

**门控检查**：

plan-done 必须满足**双重门控**才能通过：

1. **至少 1 个 active change**（必须创建至少一个 change）
2. **所有 change 的三个 artifacts 已提交**（proposal.md、design.md、tasks.md 都可通过 `git show HEAD:` 访问）

```bash
# Round A: extracted to _lib/plan_done_gate.{py,sh} (L517-L677, ~150 lines)
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/plan_done_gate.sh"
run_plan_done_gate || exit 1
# Gate 0 skip sentinel: when user accepts Deps suggestions, no handoff is written
# (matches original 'exit 0' semantics before extraction)
if [ "${PLAN_GATE_0_SKIPPED:-}" = "true" ]; then
    echo "⚠️  Gate 0 skipped (user accepted Deps suggestions), no handoff written"
    exit 0
fi
write_plan_handoff || exit 1
\`\`\`

**rddf-session 关闭 hook**（ADR-0017）：plan-done 验证通过后，将 `stage_plan` rddf-session 标记为 completed：

```bash
# rddf-session 关闭 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/rddf_session_hooks.sh"
rddf_session_hook_close stage_plan plan-done guide-plan
```

**Output to user**：

```
✅ Plan-side complete. Changes are committed and analyzed.

📋 变更生成交付物:
  - Active Changes: N 个
  - Artifacts: 全部已提交
  - 依赖分析: .rddf/state/.deps-output.md

💡 Next: skill_use("guide-ship")
   This will scan your committed changes and start worktree creation + execution.
```

Do NOT auto-invoke `guide-ship` — the user must explicitly transition to the ship side.

**回退到其他 plan 阶段**：

门控失败时，user 可选择回到对应阶段补齐：

```
门控失败: Active changes 数量为 0

请选择:
  1. ↩️  回到 scan 阶段扫描候选
  2. ↩️  回到 propose 阶段创建 change
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
  1) echo "→ 回到 scan 阶段..."; skill_use("guide-plan") ;;  # 重新调用,选择 scan
  2) echo "→ 回到 propose 阶段..."; skill_use("guide-plan") ;;  # 重新调用,选择 propose
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

---

## 阶段间循环与切换

plan 阶段内部支持**循环迭代**（细化变更生成）：

```
plan 内部循环:
  scan → propose → deps → propose (循环添加 change)
  scan → propose → deps → scan (重新扫描候选)
```

plan → ship 的**前向切换**：

```
plan → ship: plan-done 验证通过 (≥1 change + all artifacts committed)
```

plan → arch 的**反向切换**（v2.0 后续支持）：

```
plan → arch: plan 阶段选择"返回 Arch 阶段" (需要更新架构)
```

arch → plan 的**前向切换**：

```
arch → plan: arch-done 验证通过 (ADR ≥ 1 + roadmap.md 存在)
```

详细切换条件见 `docs/adr/ADR-0003-three-phase-architecture.md` §"阶段间循环与切换"。

---

## 测试与验证

本技能的状态契约可通过以下方式验证：

```bash
# 1. 验证 skill 文件存在且 frontmatter 完整
python3 -c "
import yaml
with open('skills/guide-plan.md') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'guide-plan'
assert meta['metadata']['user-invocable'] is True
print('✅ guide-plan.md frontmatter valid')
"

# 2. 验证四个子阶段齐全
grep -E "^## Phase [0-9]+:" skills/guide-plan.md

# 3. 验证 handoff 文件路径正确
grep "\.plan-handoff.json" skills/guide-plan.md

# 4. 验证 deps 候选列表路径正确
grep "\.deps-candidates.json" skills/guide-plan.md

# 5. 验证 4 个子技能引用（propose/deps/guide-arch/guide-ship）
grep -E "skill_use\(\"(propose|deps|guide-arch|guide-ship)\"\)" skills/guide-plan.md
```

<!-- 详细单元测试见 `tests/integration/test_guide_plan_skill.bats`（与本技能配套,待后续创建）。 -->

---

## 参考资料

- **ADR-0003** — 三阶段架构重构（arch → plan → ship），本技能的架构依据
- **ADR-0001** — 双阶段状态机分离（v1.x 架构，guide-spec 的来源）
- **ADR-0007** — 门控机制（plan-done 双重门控的设计依据）
- **ADR-0011** — 阶段步骤化执行模型（plan 阶段的子阶段设计）
- `skills/guide-arch.md` — arch 端状态机（前序阶段，本技能的 source）
- `skills/guide-spec.md` — v1.x spec 端状态机（Phase 2 + Phase 2.5 的 source）
- `skills/guide-ship.md` — ship 端状态机（后续阶段）
- `skills/propose.md` — 变更候选扫描与创建技能（被 plan Phase 1 + Phase 2 调用）
- `skills/deps.md` — 依赖分析技能（被 plan Phase 3 调用）
- `docs/adr/ADR-0003-three-phase-architecture.md` — 三阶段架构详细说明