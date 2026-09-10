---
name: rdd-builder
description: |
  Proposal approval + plan + execute + archive. Stage 3 of v4 architecture.
  Implements 6-phase internal state machine: P0 (approval, 5-option per ADR-0048),
  P1 (plan gen), P1.5 (deps + execution_mode), P2 (worktree + execute),
  P2.5 (review), P3 (archive with verifier retry loop). Per spec §3.4.
  P0 5-option includes **dispatch-quick** (per ADR-0048 §Decision 3) which
  routes the change to `rdd-quick` fast-path when `recommended_route=simple`.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
  + rddf planner + rddf-verifier installed
metadata:
  author: rdd-workflow
  version: 1.1
  evolved-from: "guide-design + guide-plan + guide-ship"
  user-invocable: true
role:
  title: "Builder (审批 + 执行 + 归档治理者)"
  perspective: "Think in terms of phase state machine progression, TDD discipline, verifier retry routing, AND dispatch-quick routing (per ADR-0048). Owns the actual change implementation lifecycle from approval to archive."
  boundaries:
    owns:
      - "openspec/changes/<name>/proposal.md (authoring via P0 approve, per ADR-0025)"
      - "openspec/changes/<name>/{tasks,design}.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
      - ".rddf/state/builder/<name>.json"
      - "openspec/specs/<name>/spec.md"
      - ".rddf/state/rdd-quick-context.json (临时, per ADR-0048)"
    not_owns:
      - "docs/adr/ADR-*.md"
      - "roadmap.md"
      - ".rddf/state/.planner-feedback.json"
      - ".rddf/plans/quick-*.md (rdd-quick owns, per ADR-0047)"
    human_involvement: "medium"
---

# rdd-builder Skill

Stage 3 of v4 architecture (per spec §3.4). 6-phase internal state machine:

```
P0 (approval, 5-option per ADR-0048) → P1 (plan) → P1.5 (deps + exec_mode)
                                       → P2 (execute) → P2.5 (review) → P3 (archive)
                                       └─── verifier retry loop (P3 → P1 or P2, max 3) ───┘
```

## P0 Approval Gate (5-option, per ADR-0048)

**入口**: rdd-planner 写完 `.planner-handoff.json` 后, 用户调用 `skill_use("rdd-builder")` 进入 P0.

**P0 读取**:
- `openspec/changes/<change>/proposal.md` (由 rdd-planner attach, 或 propose 子技能骨架, 或 P0 approve 时生成 per ADR-0025 D1/D2)
- `.rddf/state/.planner-handoff.json::recommended_route` (REQUIRED per ADR-0048)
- `openspec/changes/<change>/proposal.md` 中的 `## 验收标准` checkbox 数

**P0 prompt (HARD pause, 5-option)**:

```
 ══════════════════════════════════════════════
rdd-builder Phase 0: Approval Gate (HARD pause, LLM-augmented per ADR-0049)
══════════════════════════════════════════════

## 阶段 0.0 — LLM Pre-flight Reasoning (NEW per ADR-0049 Decision 1,2,4)

在显示 5-option 菜单之前, AI 代理（executing AI agent IS the LLM, per ADR-0045）必须执行以下推理：

### 数据源读取（按优先级）

1. **PRIMARY（必读）**: `.rddf/improvements/<change>.md` 5 段结构
   - `## Why` — 动机 / 问题
   - `## What` — 具体变更
   - `## How` — 实现路径 / 步骤
   - `## Acceptance` — 可验证标准
   - `## Capabilities` — MUST / MUST NOT
   - **若文件不存在 → 立即报错** (rdd-builder 入口保证 improvement 存在, 缺失是数据契约破坏)

2. **SECONDARY（必读）**: `.rddf/state/.planner-handoff.json`（若存在）
   - 关注 `recommended_route` 字段 (simple | complex | unknown)
   - 关注 `awaiting_builder` 数组确认 change 在列

3. **TERTIARY（选读）**: `.rddf/state/.planner-state.json`（若存在）
   - `active_projects[]` 数组提供 priority + theme 上下文

4. **FALLBACK（仅当 1 缺失时）**: `openspec/changes/<change>/proposal.md`（若存在）
   - 仅在 P0 入口前用户已用 `openspec init` 创建骨架时存在
   - 按 ADR-0025 D1/D2, P0 case 1 approve 时才会正式生成完整 proposal.md

5. **ALWAYS**: `docs/adr/ADR-*.md`（始终存在）
   - 检查 change 是否触碰已声明的架构约束（如 _lib/core/、_lib/schemas/）

### LLM 推理任务

AI 代理对上述数据源做以下推理：

- **复杂度评估**: 输出 `simple | complex | unknown`
- **Hidden complexity 检查**:
  - 是否触碰 `_lib/core/` 或 `_lib/schemas/` 路径？（查 `## What`）
  - 跨模块影响？（查 `theme` / ADR 引用）
  - Acceptance 数量 > 2 且每条都需要环境依赖（数据库 / docker / 网络）？
  - 数据迁移 / public interface / breaking change 关键词？
- **Acceptance 可量化性**: 是否 `- [ ] checkbox` 形式？是否能自动验证？
- **Capabilities MUST NOT 约束**: 是否清晰且可执行？
- **Conflict 检测**: LLM 结论 vs planner advisory 是否一致？

### 输出格式（prose 展示，不入文件）

AI 代理在 prose 中输出 **一行 LLM assessment**（在 5-option 菜单前）：

```
LLM assessment: simple | complex | unknown
LLM concerns: <bullet list or "none">
Agreement with advisory: yes | no (<advisory_value>)
```

### Decision 3 (Conflict 兜底): planner advisory 优先

- case 5 `--dispatch-quick` CLI 硬验证仍要求 `recommended_route=simple`（不变）
- LLM 与 advisory 冲突时 prose 显式标记但不改变 routing
- **冲突时暂停问用户**（per 用户 UX 需求，见 阶段 0.0.5 用户介入门控）

---

## 阶段 0.0.5 — 全自动决策逻辑 (NEW, 默认 ON, per 用户 UX 需求)

**默认行为**: AI 代理基于 LLM Pre-flight Reasoning + planner advisory + AC count **自动选择 1-5**，**不需要用户输入**。

rdd-builder / rdd-quick 默认是 **全自动推进** 模式。用户只在低置信度场景才介入（见下方"用户介入门控"）。

### 自动决策表（无需用户输入）

| Planner advisory | LLM assessment | AC count | 隐含复杂度 | AI 自动选 | 备注 |
|---|---|---|---|---|---|
| `simple` | `simple` | ≤ 2 | 无 | **case 5 (dispatch-quick)** | 全自动走 rdd-quick |
| `simple` | `simple` | > 2 | 无 | **case 1 (approve)** | 走完整 P1-P3 |
| `simple` | `complex` | 任意 | 有 | **case 1 (approve)** | LLM 警告但仍 approve（advisory 优先） |
| `simple` | `unknown` | 任意 | 未知 | **case 1 (approve)** | 保守走完整路径 |
| `complex` | 任意 | 任意 | 高 | **case 1 (approve)** | 走完整路径 |
| `unknown` | `unknown` | 任意 | 未知 | **暂停问用户** | 信号不足，需人工判断 |
| 任意 | `complex` AND advisory 不一致 | 任意 | 冲突 | **暂停问用户** | LLM 与 advisory 冲突，需人工 review |
| 任意 | `simple` 但 advisor=complex | 任意 | 冲突 | **暂停问用户** | advisor 提示 complex 不可 dispatch |
| `unknown` | `simple` | 任意 | 不一致 | **暂停问用户** | planner 信号缺失，需人工 |

### 用户介入门控（仅低置信度触发）

**默认 OFF**: AI 代理全自动推进

**触发用户介入的条件**（任一满足）：
- `planner-handoff.json::recommended_route == "unknown"`（planner 信号缺失）
- `LLM assessment == "unknown"`（LLM 也不能判定）
- LLM 与 planner advisory 冲突 (`Agreement: no`)
- LLM 检测到 `complexity_confirmed == "complex"` AND 与 advisory 不一致
- 环境变量 `RDDF_REQUIRE_USER_CONFIRM=yes`（强制用户确认）

**介入方式**（prose 中）：
```
🤔 AI 决策置信度低，需要用户确认:
  原因: <具体原因>
  Planner advisory: <value>
  LLM assessment: <value> (Agreement: no)
  LLM concerns: <list>

请选择:
  1) approve      2) reject       3) defer       4) revise       5) dispatch-quick
  或输入自定义 (例如: 'override to dispatch-quick because ...')
```

### 自动决策的 prose 展示（让用户能跟上）

即使全自动，AI 代理仍在 prose 中输出一段决策说明（让用户能 review）：

```
=== AI Auto-decision (per ADR-0049 + 用户 UX 需求) ===
变更: <change-name>
Planner advisory: simple
LLM assessment: simple (Agreement: yes)
AC count: 2
LLM concerns: none

🤖 AI 自动选择: option 5 (dispatch-quick)
理由: 三者一致 (advisory=simple + LLM=simple + AC=2) → 走 rdd-quick 路径
下一步: 委托 skill_use("rdd-quick") --from-builder
```

---

## 阶段 0.1 — 5-option 决策上下文（仅低置信度展示）

> **NOTE**: 默认情况下 AI 已自动决策 1-5, 此节仅在低置信度场景下展示给用户。

展示格式（在 LLM assessment 之后）：

```
变更: <change-name>
Planner advisory: recommended_route = <value>
LLM assessment: <value> (Agreement: yes | no)
AC 数量: N 个 (from .rddf/improvements/<change>.md ## Acceptance, 或 fallback proposal.md)

💡 推荐选项 (per advisor advisory + LLM agreement):
   - 三者一致 (advisory=simple AND LLM=simple AND AC ≤ 2)
     → 💡 推荐选项 5 (dispatch-to-quick)
   - LLM=complex 或 advisory=complex
     → 选项 1 (approve) 是常规路径, 仔细评估 LLM concerns
   - LLM 标记 conflict (Agreement: no)
     → 用户应仔细 review LLM concerns 后再决策

请选择:
  1. ✅ approve       → 继续 Phase 1 plan gen
  2. ❌ reject        → rddf feedback add --kind rejected, exit 0 (no archive)
  3. ⏸ defer         → rddf feedback add --kind blocked, exit 0 (no archive)
  4. 🔄 revise        → rddf feedback add --kind needs-revision, exit 1
  5. ⚡ dispatch-quick → 转 rdd-quick (per ADR-0047 + ADR-0048 §Decision 3)
                       仅当 recommended_route=simple 时启用
                       → 创建 .rddf/state/rdd-quick-context.json 临时文件
                       → 委托 skill_use("rdd-quick") with --from-builder flag
                       → rdd-quick 完成后: 直接 openspec archive (跳过 P1-P3)
                                          或回 P0 重新决策 (用户选择)
══════════════════════════════════════════════
```

---

## 阶段 0.2 — Case 2/3/4: LLM-generated feedback body (NEW per ADR-0049 Decision 5)

> **Decision 1 note**: case 1 approve **不调 LLM**（用户已显式 approve；LLM 重新评估无信息增益；省 token）。仅 case 2/3/4/5 触发 LLM 推理（4 case）。

> **全自动 note (per 用户 UX 需求)**: 默认情况下, AI 代理在 阶段 0.0.5 自动决策表中已根据信号自动选择 2/3/4（reject / defer / revise）。用户不再需要输入。本节描述 AI 选 2/3/4 时生成的 feedback body 格式。

AI 自动选 2/3/4 时, AI 代理必须生成 actionable feedback body 传给 rdd-planner：

### 推理步骤

1. **READ** `.rddf/improvements/<change>.md` 5 段
2. **REASON**: 为什么这个 change 被 reject / defer / revise？
   - 引用具体段落（`## Why` / `## What` / `## How` / `## Acceptance` / `## Capabilities`）
   - 生成 actionable reason（rdd-planner 收到后能照做）
3. **GENERATE** feedback body 格式（3-5 行 markdown）：

```
## LLM-generated feedback
Concern: <引用 improvement 段落>
Severity: critical | warning | info
Suggested action: <具体下一步, rdd-planner 可执行>
Related ADR: <ADR-NNNN if applicable>
```

### 执行步骤

4. **EXECUTE**（不调 bash, AI 代理在 prose 中直接调 rddf CLI）:
   - case 2 reject: `rddf feedback add <change> --from rdd-builder --kind rejected --body "<LLM-generated>"`
   - case 3 defer: `rddf feedback add <change> --from rdd-builder --kind blocked --body "<LLM-generated>"`
   - case 4 revise: `rddf feedback add <change> --from rdd-builder --kind needs-revision --body "<LLM-generated>"`
5. **EXIT** 0 (case 2/3) 或 EXIT 1 (case 4 per ADR-0048)

### 落点

LLM 生成的 feedback body 经 `rddf feedback add` 写入 `.rddf/state/.planner-feedback.json`（现有字段，无需 schema 改动）。rdd-planner 下次 stage entry 通过 `_lib/planner_feedback.compute_planner_feedback` 立即可见。

---

## 阶段 0.3 — Case 5: dispatch-quick + LLM hidden complexity check (NEW per ADR-0049 Decision 5)

> **全自动 note (per 用户 UX 需求)**: 默认情况下, AI 代理在 阶段 0.0.5 自动决策表中已根据信号（advisory=simple + LLM=simple + AC ≤ 2）自动选 case 5 (dispatch-quick)。本节描述 AI 自动选 5 时执行的 hidden complexity check + review_note 生成。

AI 自动选 case 5 时（含 `--dispatch-quick` CLI flag），AI 代理必须执行 hidden complexity check 生成 review_note：

### 推理步骤

1. **READ** `.rddf/improvements/<change>.md` 5 段
2. **CHECK**:
   - 是否触碰 `_lib/core/` 或 `_lib/schemas/` 路径？（查 `## What`）
   - 跨模块影响？（查 theme / ADR 引用）
   - Acceptance 数量 > 2 且每条都需要环境依赖？
   - 数据迁移 / public interface / breaking change 关键词？
3. **EMIT** review_note JSON：

```json
{
  "complexity_confirmed": "simple | complex | unknown",
  "concerns": ["<bullet>", "<bullet>"],
  "suggested_action": "proceed | escalate",
  "reviewed_at": "<ISO timestamp>",
  "data_source": "<绝对路径 of improvement file>"
}
```

### 执行步骤

4. **EXECUTE**（env-var pattern, 避免 bash 字符串插值, per Oracle C1）:

```bash
DISPATCH_QUICK_REVIEW_JSON='<JSON above>' \
DISPATCH_QUICK_REVIEW_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
python3 -c "
import json, os, sys
sys.path.insert(0, '<repo_root>')
from _lib.builder_handoff import write_builder_handoff, read_builder_handoff

project_root = os.environ['PROJECT_ROOT']
change_name = os.environ['CHANGE_NAME']
review = json.loads(os.environ['DISPATCH_QUICK_REVIEW_JSON'])
review['reviewed_at'] = os.environ['DISPATCH_QUICK_REVIEW_AT']

# Preserve existing fields (approval_status, current_phase 等)
existing = read_builder_handoff(project_root, change_name)
write_builder_handoff(
    project_root=project_root,
    change_name=change_name,
    current_phase=existing.get('current_phase', 'phase-0'),
    approval_status=existing.get('approval_status', 'dispatched_to_quick'),
    dispatch_quick_review=review,
)
print('dispatch_quick_review written')
"
```

5. **IF** `complexity_confirmed == "complex"`:
   - **ECHO** warning 给用户:
     ```
     ⚠️ LLM 检测到 hidden complexity (concerns: <list>)
     但用户已显式选择 dispatch-quick, 按用户选择执行 (HARD pause 保持)
     ```
   - **不阻断** — HARD pause 是用户决策, LLM 仅提示
   - 可选: `dispatch_quick_review.forced_by_user = true` 标记覆盖意图

6. **CONTINUE** to 原有 case 5 逻辑（per ADR-0048）:
   - 写 `rdd-quick-context.json`
   - 写 `builder-handoff::approval_status=dispatched_to_quick`
   - emit `DISPATCH_TO_QUICK=1 CHANGE_NAME=<change>` marker
   - 委托 `skill_use("rdd-quick") --from-builder`

### 消费者

- rdd-quick P1 读 `.planner-handoff.json::recommended_route` 作为主 advisory
- rdd-quick P1 也读 `.rddf/state/builder/<change>.json::dispatch_quick_review.concerns` 作为额外 advisory
- 若 `complexity_confirmed == "complex"` AND `forced_by_user == true`:
  - rdd-quick P1 仍按 `complex` 走强制 Metis/Oracle 审查（per ADR-0048 amendment）
```

**P0 选项 5 (dispatch-quick) 触发逻辑** (per ADR-0048 §Decision 3):
- 前置条件: `recommended_route == "simple"`
- 写 `.rddf/state/builder/<change>.json::approval_status = "dispatched_to_quick"`
- 创建 `.rddf/state/rdd-quick-context.json` 临时文件, 包含:
  ```json
  {
    "change_name": "<change>",
    "proposal_path": "openspec/changes/<change>/proposal.md",
    "from_builder": true,
    "dispatched_at": "2026-09-09T...",
    "expected_outcome": "completed|escalated|unverified"
  }
  ```
- 关闭 `stage_builder` rddf-session
- 委托 `skill_use("rdd-quick") --from-builder`
- rdd-quick 完成时:
  - outcome=completed → 直接 `openspec archive <change> --yes` (跳过 P1-P3)
  - outcome=unverified → 回 P0 重新决策
  - outcome=escalated → 回 P0 重新决策 (失败升级契约 per ADR-0047 amendment)

**Pause contract** (per spec §5.2):
- HARD pause at P0 / P2.5 (用户必须显式选择,不能跳过)
- SOFT pause at P1 / P1.5 / verifier back-route (`--no-pause` 可跳过)

**Exit codes**: 0 (success), 1 (P0 reject), 2 (plan quality), 3 (worktree/COMMIT), 4 (verifier halt), 5 (review revise), 6 (deps gate), 7 (archive gate).

Cross-stage feedback (per spec §3.5.2 batch 4):
- Phase 2 ADR-drift detection → `rddf feedback add --kind ac-fail --from rdd-builder`
- Routed via `_lib/builder_feedback_router.py` to `.planner-feedback.json`
- Architect reads via `rddf arch feedback` (advisory)

P0 → rdd-quick dispatch 通道 (NEW per ADR-0048):
- 读取 `.planner-handoff.json::recommended_route` 作主信号
- 写 `.rddf/state/rdd-quick-context.json` 临时文件
- 委托 `skill_use("rdd-quick") --from-builder`