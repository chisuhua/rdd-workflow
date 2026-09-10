---
name: rdd-builder-phase0-llm-integration
priority: P2
theme_ref: rdd-builder-evolution
roadmap_ref:
  project_id: rdd-workflow
  phase: phase-3
  theme: rdd-builder-evolution
---

## Why

当前 rdd-builder Phase 0 的 5-option HARD pause 仅依赖两个 deterministic 信号：
1. `planner-handoff.json::recommended_route`（来自 `_compute_recommended_route` 启发式，15 个关键词匹配）
2. 用户在 HARD pause 处手动输入 1-5

这造成三个问题：

**问题 1: 推荐信号弱**。heuristic 关键词匹配对"看似 simple 但实际 hidden complexity"的 change 无法识别。例如：
- improvement 5 段文字不包含 `_COMPLEX_KEYWORDS` 但实际触及 `_lib/core/` 路径
- 没有 priority = P0/P1 但跨多个模块边界
- AC 数量 ≤ 2 但每条都需要环境依赖（数据库 / docker / 网络）

**问题 2: 反馈生成空**。当前 case 2/3/4 调 `rddf feedback add` 的 body 是固定字符串（`"Rejected in Phase 0"` / `"Deferred in Phase 0"`），回写给 rdd-planner 的 planner-feedback 信息密度极低。rdd-planner 下次 stage entry 只能看到"被拒绝"，不知道具体原因和下一步建议。

**问题 3: dispatch-quick 无审查**。当前 case 5 仅做 `recommended_route=simple` 硬验证 + AC ≤ 2 hint，但 LLM 级别的"hidden complexity check"缺失。LLM 推理（executing AI agent IS the LLM, per ADR-0045）可捕获 planner 看不到的信号。

**真实流程观察（user 关键纠正）**：进入 Phase 0 时，`openspec/changes/<change>/proposal.md` **可能不存在**。LLM 数据源应是 `.rddf/improvements/<change>.md` 5 段结构，proposal.md 仅作 fallback（若存在）。

## What

在 `rdd-builder` Phase 0 引入 LLM Pre-flight Reasoning，遵循 **"executing AI agent IS the LLM"** 架构（per ADR-0045）：

1. **Phase 0 LLM Pre-flight Reasoning 块**（SKILL.md 新增）
   - AI 代理读 `.rddf/improvements/<change>.md` 5 段
   - 读 `.planner-handoff.json::recommended_route`
   - 推理：复杂度评估 + hidden complexity 检查 + 与 advisory 一致性
   - prose 输出 LLM assessment（不写入文件）

2. **Case 2/3/4 LLM feedback body 生成**（SKILL.md 新增）
   - 选 reject/defer/revise 时，AI 代理生成 actionable feedback body
   - 走现有 `rddf feedback add --body "<LLM-generated>"` API
   - 写入 `.rddf/state/.planner-feedback.json`（现有字段，无需 schema 改动）

3. **Case 5 hidden complexity check**（SKILL.md 新增）
   - 选 dispatch-quick 时，AI 代理生成 review_note JSON
   - 写入 `.rddf/state/builder/<change>.json::dispatch_quick_review`（新增字段）
   - 若 complexity_confirmed == "complex"，echo 警告但不阻断（HARD pause 保持）

4. **LLM 数据源修正**（关键观察）
   - 主源：`.rddf/improvements/<change>.md` 5 段（Why/What/How/Acceptance/Capabilities）
   - fallback：`openspec/changes/<change>/proposal.md`（若存在）
   - 不存在报错：`doc/adr/ADR-*.md`（始终存在，用于架构约束检查）

5. **Conflict 兜底**：planner advisory > LLM assessment
   - case 5 --dispatch-quick 硬验证仍要求 `recommended_route=simple`（不变）
   - LLM 与 advisory 冲突时 prose 显式标记但不改变 routing
   - 用户始终是最终决策者（HARD pause 不变）

6. **Bug fix**：builder_handoff_schema.json::approval_status enum 同步添加 `dispatched_to_quick`（`_lib/builder_handoff.py` L58 实际接受但 schema 未同步）

## How

### 数据流

```
Phase 0 入口:
  AI 代理读 .rddf/improvements/<change>.md 5 段   ← 主数据源 (始终存在)
  AI 代理读 .planner-handoff.json::recommended_route ← advisory 信号
  AI 代理读 .planner-state.json::active_projects    ← priority + theme 上下文
  AI 代理 (optional) 读 proposal.md                  ← fallback only
  AI 代理读 docs/adr/ADR-*.md                       ← 架构约束检查

LLM Pre-flight Reasoning (prose):
  → 输出 LLM assessment (单行: simple|complex|unknown + concerns + agreement)
  → 不写入文件, 仅 prose 展示

5-option 菜单 + 三重信号:
  → Planner advisory: <route>
  → LLM assessment: <route>
  → 💡 推荐: <merged_recommendation>

User 输入 1-5 (HARD pause):
  case 1 approve    → 不调 LLM (用户已显式选)
  case 2 reject     → AI 生成 feedback body → rddf feedback add (kind=rejected)
  case 3 defer      → AI 生成 feedback body → rddf feedback add (kind=blocked)
  case 4 revise     → AI 生成 feedback body → rddf feedback add (kind=needs-revision)
  case 5 dispatch-quick → AI 生成 review_note → write_builder_handoff(...)
                              + 原有 rdd-quick-context.json + DISPATCH_TO_QUICK marker
```

### Schema 改动

`_lib/schemas/builder_handoff_schema.json`：
- L34 `approval_status` enum 添加 `dispatched_to_quick`（bug fix）
- 新增 `dispatch_quick_review` optional object 字段

`_lib/builder_handoff.py::write_builder_handoff`：
- 新增 kwarg `dispatch_quick_review: Optional[Dict] = None`
- 验证 `complexity_confirmed ∈ {simple, complex, unknown}`
- 验证 `suggested_action ∈ {proceed, escalate}`
- 不 bump schema version（保持 v1 + additionalProperties:true）

### SKILL.md 改造

在 `skills/rdd-builder/SKILL.md` Phase 0 段落新增 3 块自然语言指令（约 80-100 行新增）：
- Block A: LLM Pre-flight Reasoning (≥ 25 行)
- Block B: Case 2/3/4 LLM feedback generation (≥ 20 行)
- Block C: Case 5 LLM hidden complexity check (≥ 25 行)

### 测试

新增 2 个测试文件：
1. `tests/unit/test_dispatch_quick_review.py` (pytest, ~120 行, 6 cases)
   - write_builder_handoff 新字段支持
   - complexity_confirmed / suggested_action 验证
   - round-trip preservation
2. `tests/integration/test_rdd_builder_phase0_llm.bats` (bats, ~250 行, 10-12 cases)
   - SKILL.md 改造的存在性 (3 块)
   - SKILL.md 引用 ADR-0049
   - phase0_approval.sh case 5 读 dispatch_quick_review (warn if complex)
   - schema approval_status enum bug fix
   - --dispatch-quick CLI flag 仍要求 recommended_route=simple (不变)

## Acceptance

| # | AC | 验证 |
|---|---|---|
| 1 | ADR-0049 写完，引用 ADR-0045 + ADR-0048 + ADR-0025 | review |
| 2 | SKILL.md Phase 0 含 LLM Pre-flight Reasoning 段 (≥ 25 行) | bats L1 |
| 3 | SKILL.md case 2/3/4 含 LLM feedback generation 段 (≥ 20 行) | bats L2 |
| 4 | SKILL.md case 5 含 LLM hidden complexity check 段 (≥ 25 行) | bats L3 |
| 5 | SKILL.md 引用 ADR-0049 ≥ 1 处 | grep -c |
| 6 | `write_builder_handoff` 支持 dispatch_quick_review kwarg | pytest L1-6 |
| 7 | builder_handoff_schema.json 修正 approval_status enum | bats L8 |
| 8 | phase0_approval.sh case 5 读 dispatch_quick_review 不阻断 | bats L9 |
| 9 | 全部 ADR-0048 测试零 regression (61 bats + 40 pytest) | regression suite |
| 10 | 全部 ADR-0049 测试通过 (10-12 bats + 6 pytest) | new suite |
| 11 | docs (v4-pipeline-data-flow.md + workflow-phases.md) 同步 | review |

## Capabilities

### MUST

1. SKILL.md Phase 0 必须包含 LLM Pre-flight Reasoning 指令块（用自然语言指示 AI 代理执行 LLM 推理）
2. SKILL.md case 2/3/4 必须包含 LLM feedback body 生成指令
3. SKILL.md case 5 必须包含 LLM hidden complexity check 指令
4. LLM 数据源主源必须是 `.rddf/improvements/<change>.md` 5 段（不依赖 proposal.md 存在）
5. planner advisory 优先级必须 > LLM assessment（advisory 兜底）
6. case 5 --dispatch-quick 硬验证必须仍要求 `recommended_route=simple`（不变）
7. HARD pause 必须仍由用户最终决策（AI 代理是执行者不是替代者）

### MUST NOT

1. 不引入 ANTHROPIC_API_KEY / OPENAI_API_KEY env var
2. 不引入 llm_client 模块或 SDK 依赖
3. 不改变 `_compute_recommended_route` 启发式（deterministic 不变）
4. 不改变 `planner-handoff.json::recommended_route` schema
5. 不改变 `rddf feedback add` API（LLM 仅生成 body 参数）
6. 不让 LLM 替代用户做 1-5 选择（HARD pause 不变）

## Why not (alternatives)

### 为什么不引入 ANTHROPIC_API_KEY + llm_client 模块？

- 与 ADR-0045 "executing AI agent IS the LLM" 模式冲突（rdd-verifier 已验证此模式可工作）
- 引入新 provider 抽象，增加密钥管理负担
- 与 v4.0+ 自包含理念不一致
- 当前 SKILL.md 已用自然语言指示 AI 推理，verifier 验证过可行

### 为什么 case 1 approve 不调 LLM？

- 用户已显式 approve，LLM 重新评估无信息增益
- 节省 ~30-40% token 消耗
- ADR-0048 "HARD pause user override" 精神保持更强：用户决策不被 LLM 干扰

### 为什么 LLM 不优先 override advisory？

- planner advisory 是上游契约（rdd-planner → rdd-builder 边界）
- LLM 在 P0 决策点没有全局上下文（不见 roadmap / deps / cross-repo）
- advisory 优先 + LLM 提示更稳健

### 为什么 LLM 数据源不用 proposal.md？

- P0 入口 proposal.md 可能不存在（per user 关键观察）
- `.rddf/improvements/<change>.md` 5 段在 P0 入口保证存在（rdd-planner attach 必写）
- proposal.md 仅 fallback（若存在则用 ## Acceptance / ## Capabilities）

## Related

- ADR-0048 §Decision 3 (5-option P0 + dispatch-quick) — AMENDED by ADR-0049
- ADR-0045 (rdd-verifier self-contained LLM) — PATTERN reused
- ADR-0025 (design proposal creation D1/D2) — Data source .rddf/improvements/*.md 5 段
- ADR-0037 (single-writer feedback add) — case 2/3/4 落点仍走 rddf feedback add
- ADR-0042 (rdd-arch ↔ rdd-planner bidirectional feedback) — LLM feedback 流入 .planner-feedback.json
