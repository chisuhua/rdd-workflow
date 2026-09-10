# ADR-0049: rdd-builder Phase 0 LLM Integration (Pre-flight Reasoning + Feedback Generation + Hidden Complexity Check)

> **Date**: 2026-09-10
> **Status**: 待采纳
> **Supersedes**: (none)
> **Amends**: [ADR-0048 §Decision 3](ADR-0048-v4-stage-merge-revision.md)
> **Author**: rdd-builder evolution

## Context

[ADR-0048](ADR-0048-v4-stage-merge-revision.md) v4.0.1 引入了 rdd-builder Phase 0 的 5-option HARD pause（approve / reject / defer / revise / dispatch-quick）。但当前 P0 决策仅依赖两个 deterministic 信号：

1. `planner-handoff.json::recommended_route`（来自 `_compute_recommended_route` 启发式）
2. 用户在 HARD pause 处手动输入 1-5

**问题 1: 推荐信号弱**。`_COMPLEX_KEYWORDS` 15 个词匹配 + `priority ∈ {P0,P1}` 判定 → 对"看似 simple 但实际 hidden complexity"的 change 无法识别（例如：simple 文本但触及 `_lib/core/` 路径、跨模块边界、AC 不可量化）。

**问题 2: 反馈生成空**。当前 case 2/3/4 调 `rddf feedback add` 的 body 是固定字符串（`"Rejected in Phase 0"` / `"Deferred in Phase 0"`），回写给 rdd-planner 的 planner-feedback 信息密度极低。

**问题 3: dispatch-quick 无审查**。当前 case 5 仅做 `recommended_route=simple` 硬验证 + AC ≤ 2 hint，但 LLM 级别的"hidden complexity check"缺失。

**真实流程观察（user 关键纠正）**：进入 Phase 0 时，`openspec/changes/<change>/proposal.md` **可能不存在**。LLM 数据源应是 `.rddf/improvements/<change>.md` 5 段结构（Why/What/How/Acceptance/Capabilities），proposal.md 仅作 fallback（若存在）。

## Decision

在 `rdd-builder` Phase 0 引入 LLM Pre-flight Reasoning，遵循 **"executing AI agent IS the LLM"** 架构（per [ADR-0045](ADR-0045-inline-ac-verifier-into-rdd-verifier.md)）：

### Decision 1: 触发边界 — 4 case 调 LLM, 1 case 不调

| Case | LLM 调用 | 原因 |
|---|---|---|
| **1 (approve)** | ❌ 不调 | 用户已显式选择；LLM 无信息增益；省 token |
| **2 (reject)** | ✅ 调 | 生成 actionable feedback body |
| **3 (defer)** | ✅ 调 | 生成 blocker reason + suggested next step |
| **4 (revise)** | ✅ 调 | 生成具体 revision points |
| **5 (dispatch-quick)** | ✅ 调 | hidden complexity check + review_note |

### Decision 2: LLM 架构 — executing AI agent IS the LLM

- **不引入** ANTHROPIC_API_KEY / OPENAI_API_KEY env var
- **不引入** llm_client 模块 / SDK 依赖
- SKILL.md 用自然语言指示 AI 代理（用户当前会话中的 AI）执行 LLM 推理
- 与 rdd-verifier (ADR-0045) 完全对称 — 已经验证过此模式可工作

### Decision 3: Conflict 兜底 — planner advisory 优先

```
planner advisory (deterministic) > LLM assessment (advisory)
```

- case 5 硬验证仍要求 `recommended_route=simple`（不变）
- LLM 与 advisory 冲突时, LLM 输出在 prose 中显式标记 `"Agreement with advisory: no (<advisory_value>)"`，但不改变 routing
- 用户始终是最终决策者（HARD pause 不变）

### Decision 4: LLM 数据源 — `.rddf/improvements/<change>.md` 5 段为主源

| 数据源 | 可用性 | 用途 |
|---|---|---|
| `.rddf/improvements/<change>.md` | ✅ **P0 入口一定存在** | **主源** (Why/What/How/Acceptance/Capabilities) |
| `.rddf/state/.planner-handoff.json` | ✅ planner stage-exit 后存在 | advisory 信号 |
| `.rddf/state/.planner-state.json` | ✅ 可能存在 | priority + theme 上下文 |
| `openspec/changes/<change>/proposal.md` | ⚠️ **可能不存在** | **fallback only**（若存在则用 ## Acceptance / ## Capabilities） |
| `docs/adr/ADR-*.md` | ✅ 始终存在 | 检查 change 是否触碰已声明架构约束 |

### Decision 5: LLM 输出落点

| LLM 输出 | 写入位置 | 消费者 |
|---|---|---|
| LLM Pre-flight Assessment | prose 展示（不入文件） | user 决策时可见 |
| case 2/3/4 feedback body | `rddf feedback add --body "<LLM-generated>"` → `.rddf/state/.planner-feedback.json` | rdd-planner 下次 stage entry 读取 |
| case 5 review_note JSON | `.rddf/state/builder/<change>.json::dispatch_quick_review` | rdd-quick P1 读取作为额外 advisory |

## Schema Changes

### `_lib/schemas/builder_handoff_schema.json` v1 → v2

新增 `dispatch_quick_review` optional 字段（顶层 v1 → bump 顶层 `version` 字段待评估；OR 保持 v1 + 增加字段即可）。

**保留 v1 + additionalProperties:true + 新字段**（向后兼容；不需 bump schema version）：

```json
"dispatch_quick_review": {
  "type": "object",
  "description": "LLM-generated hidden complexity check (per ADR-0049 Decision 5)",
  "properties": {
    "complexity_confirmed": {"enum": ["simple", "complex", "unknown"]},
    "concerns": {"type": "array", "items": {"type": "string"}},
    "suggested_action": {"enum": ["proceed", "escalate"]},
    "reviewed_at": {"type": "string", "format": "date-time"},
    "data_source": {"type": "string", "description": "Path of source improvement file (.rddf/improvements/...)"}
  }
}
```

### `_lib/schemas/planner_feedback_schema.json` (existing)

**不需要新增字段**。LLM 生成的 feedback body 走现有 `rddf feedback add --body "<text>"` API，落入现有 `feedbacks[]::body` 字段（已是 string 类型）。

### `_lib/builder_handoff.py::write_builder_handoff` 接口扩展

新增 kwarg：
```python
def write_builder_handoff(
    project_root: str,
    change_name: str,
    current_phase: str = "phase-0",
    approval_status: str = "pending",
    ...
    dispatch_quick_review: Optional[Dict] = None,  # NEW per ADR-0049
    ...
):
```

行为：
- 若 `dispatch_quick_review` 非 None，merge 到 `handoff["dispatch_quick_review"]`
- 验证 `complexity_confirmed ∈ {simple, complex, unknown}`（raise ValueError 否则）
- 不 bump schema version

### `approval_status` enum schema 修正 (bug fix)

`_lib/schemas/builder_handoff_schema.json` L34 当前 enum 缺少 `dispatched_to_quick`，但 `_lib/builder_handoff.py` L58 实际接受 → **schema 必须同步**：

```json
"approval_status": {"enum": ["pending", "approved", "rejected", "deferred", "revising", "dispatched_to_quick"]}
```

## SKILL.md Changes (per ADR-0049 Decision 5)

在 `skills/rdd-builder/SKILL.md` Phase 0 段落（L74 之前）新增 3 块自然语言指令：

### Block A: LLM Pre-flight Reasoning (NEW, ~30 lines)

```markdown
## Phase 0: Approval Gate (HARD pause, LLM-augmented per ADR-0049)

### LLM Pre-flight Reasoning (NEW per ADR-0049)
在显示 5-option 菜单之前, AI 代理必须:

1. READ `.rddf/improvements/<change>.md` 5 段:
   - ## Why / ## What / ## How / ## Acceptance / ## Capabilities
   - 若文件不存在 → 立即报错 (rrd-builder 入口保证 improvement 存在)

2. READ `.rddf/state/.planner-handoff.json` (if exists) 关注 `recommended_route`

3. REASON via own LLM capability:
   - 复杂度评估: simple | complex | unknown
   - 是否有 hidden complexity (跨模块 / _lib/core/ / _lib/schemas/ 路径)
   - Acceptance 是否可量化验证 (- [ ] checkbox 形式)
   - Capabilities MUST NOT 约束是否清晰
   - 与 planner advisory 是否一致

4. EMIT 一行 LLM assessment (prose):
   ```
   LLM assessment: simple | complex | unknown
   LLM concerns: <bullet or "none">
   Agreement with advisory: yes | no (<advisory_value>)
   ```

5. THEN 显示 5-option 菜单 + 三重信号 (advisory + LLM + 合并推荐)
```

### Block B: Case 2/3/4 LLM feedback generation (NEW, ~25 lines)

```markdown
### Case 2/3/4: LLM-generated feedback body (NEW per ADR-0049)
当 user 选 2/3/4 时, AI 代理必须:

1. READ `.rddf/improvements/<change>.md` 5 段
2. REASON: 为什么被 reject / defer / revise?
   - 引用具体段落 (Why / What / How / Acceptance / Capabilities)
   - 生成 actionable reason (rdd-planner 收到后能照做)
3. GENERATE feedback body 格式 (3-5 lines):
   ```
   ## LLM-generated feedback
   Concern: <引用 improvement 段落>
   Severity: critical | warning | info
   Suggested action: <具体下一步>
   Related ADR: <ADR-NNNN if applicable>
   ```
4. EXECUTE:
   `rddf feedback add <change> --from rdd-builder --kind {rejected|blocked|needs-revision} --body "<LLM-generated>"`
5. EXIT 0 (case 2/3) 或 EXIT 1 (case 4 per ADR-0048)
```

### Block C: Case 5 hidden complexity check (NEW, ~30 lines)

```markdown
### Case 5: dispatch-quick — LLM hidden complexity check (NEW per ADR-0049)
当 user 选 5 时 (含 --dispatch-quick CLI flag), AI 代理必须:

1. READ `.rddf/improvements/<change>.md` 5 段
2. CHECK:
   - 是否触碰 _lib/core/ 或 _lib/schemas/ 路径? (查 ## What)
   - 跨模块影响? (查 theme / ADR 引用)
   - Acceptance 数量 > 2 且每条都需要环境依赖?
   - 数据迁移 / public interface / breaking change 关键词?

3. EMIT review_note JSON:
   ```json
   {
     "complexity_confirmed": "simple | complex",
     "concerns": [...],
     "suggested_action": "proceed | escalate",
     "reviewed_at": "ISO timestamp",
     "data_source": "绝对路径 of improvement file"
   }
   ```

4. EXECUTE python3 (env var 模式, 非 bash 字符串插值):
   `python3 -c "from _lib.builder_handoff import write_builder_handoff; ..."`

5. APPEND to `.rddf/state/builder/<change>.json::dispatch_quick_review`

6. IF complexity_confirmed == "complex":
   - ECHO: "⚠️ LLM 检测到 hidden complexity, 但 user 已显式选择 dispatch-quick, 按 user 选择执行"
   - 不阻断 (HARD pause 保持)
   - dispatch_quick_review.forced_by_user = true (extra field, optional)

7. CONTINUE to original case 5 logic (per ADR-0048):
   - 写 rdd-quick-context.json
   - emit DISPATCH_TO_QUICK=1 marker
```

## Test Strategy

### pytest unit tests (NEW file: `tests/unit/test_dispatch_quick_review.py`)

覆盖 `write_builder_handoff` 新字段：
1. dispatch_quick_review=None → 不写入 (backward compat)
2. dispatch_quick_review=valid dict → 正确写入
3. dispatch_quick_review=invalid complexity_confirmed → ValueError
4. dispatch_quick_review=invalid suggested_action → ValueError
5. round-trip (write → read) preserves dispatch_quick_review
6. update_builder_handoff partial merge preserves dispatch_quick_review

### bats integration tests (NEW file: `tests/integration/test_rdd_builder_phase0_llm.bats`)

覆盖 SKILL.md 改造 + phase0_approval.sh：
1. SKILL.md contains "LLM Pre-flight Reasoning" 段
2. SKILL.md contains "Case 2/3/4: LLM-generated feedback body" 段
3. SKILL.md contains "Case 5: dispatch-quick — LLM hidden complexity check" 段
4. SKILL.md 引用 ADR-0049
5. phase0_approval.sh case 5 读 dispatch_quick_review (warn if complex, 不阻断)
6. phase0_approval.sh --dispatch-quick CLI 仍要求 recommended_route=simple (不变)
7. rddf feedback add 在 case 2/3/4 被调用 (mock test)
8. schema approval_status enum 包含 dispatched_to_quick (修正 bug)

**不测 LLM 输出内容** — executing AI agent 的推理无固定 ground truth (符合 ADR-0045 模式)。

## Boundary Preservation (per ADR-0048)

- ✅ HARD pause 仍由 user 选择, AI 代理是执行者
- ✅ case 5 --dispatch-quick 硬验证仍要求 recommended_route=simple
- ✅ _compute_recommended_route 启发式不变 (deterministic)
- ✅ planner-handoff.json::recommended_route schema 不变
- ✅ rddf feedback add API 不变 (LLM 仅生成 body 参数)

## Rollout

**Step 1**: Schema + Python 接口扩展 (low risk, backward compat)
**Step 2**: SKILL.md 改造 (no code change, pure documentation)
**Step 3**: phase0_approval.sh case 5 读 dispatch_quick_review (读不写, 零破坏)
**Step 4**: 测试覆盖
**Step 5**: docs 同步 (v4-pipeline-data-flow.md + workflow-phases.md)

每步独立 commit + 验证测试零 regression。

## Alternatives Considered

### Alt 1: 引入 ANTHROPIC_API_KEY + llm_client 模块
**否决理由**：
- 与 ADR-0045 "executing AI agent IS the LLM" 模式冲突
- 引入新 provider 抽象, 增加密钥管理负担
- 与 v4.0+ 自包含理念不一致
- 当前 SKILL.md 已用自然语言指示 AI 推理, 工作良好 (verifier 验证)

### Alt 2: case 1 也调 LLM
**否决理由**：
- 用户已显式 approve, LLM 重新评估无信息增益
- 节省 ~30-40% token 消耗
- ADR-0048 "HARD pause user override" 精神保持更强

### Alt 3: LLM 优先 (override advisory)
**否决理由**：
- planner advisory 是上游契约 (rdd-planner → rdd-builder 边界)
- LLM 在 P0 决策点没有全局上下文 (不见 roadmap / deps / cross-repo)
- advisory 优先 + LLM 提示更稳健

### Alt 4: data_source 用 proposal.md
**否决理由**：
- P0 入口 proposal.md 可能不存在 (per user 关键观察)
- `.rddf/improvements/<change>.md` 5 段在 P0 入口保证存在
- proposal.md 仅 fallback (若存在则用)

## Acceptance Criteria

| # | AC | 验证 |
|---|---|---|
| 1 | SKILL.md Phase 0 含 LLM Pre-flight Reasoning 段 (≥ 25 行) | bats L1-4 |
| 2 | SKILL.md case 2/3/4 含 LLM feedback generation 段 (≥ 20 行) | bats L2 |
| 3 | SKILL.md case 5 含 LLM hidden complexity check 段 (≥ 25 行) | bats L3 |
| 4 | SKILL.md 引用 ADR-0049 ≥ 1 处 | grep -c "ADR-0049" |
| 5 | `write_builder_handoff` 支持 dispatch_quick_review kwarg | pytest L1-6 |
| 6 | builder_handoff_schema.json 修正 approval_status enum | bats L8 |
| 7 | phase0_approval.sh case 5 读 dispatch_quick_review 不阻断 | bats L5 |
| 8 | 全部 ADR-0048 测试零 regression | 跑 test_rdd_builder_dispatch_quick.bats 等 |
| 9 | 全部 ADR-0049 测试通过 | pytest + bats 全绿 |

## Cross-references

- ADR-0048 §Decision 3 (5-option P0 + dispatch-quick) — AMENDED by ADR-0049 Decision 1
- ADR-0045 (rdd-verifier self-contained LLM) — PATTERN reused by ADR-0049 Decision 2
- ADR-0025 (design proposal creation D1/D2) — Data source .rddf/improvements/*.md 5 段
- ADR-0037 (single-writer feedback add) — case 2/3/4 落点仍走 rddf feedback add
- ADR-0042 (rdd-arch ↔ rdd-planner bidirectional feedback) — LLM feedback 流入 .planner-feedback.json
