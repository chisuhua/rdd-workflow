# fix-specs-auto-generate-in-design-precreated

## Why

**症状 (2026-08-31 ship 阶段, 1 个 P1 change 触发)**:

- design 阶段批准 `reduce-rdd-workflow-tool-call-friction` + `worktree-context-persistence`（P1, ship/ship, refactor）
- guide-design D1 流程生成 `proposal.md`（含 Why / What Changes / Capabilities / Impact / ## Acceptance），approval落盘 + commit artifacts
- plan 阶段 fill 生成 `design.md` + `tasks.md`，commit 到 master（commit `ec37db5 feat(plan): add ...`）
- ship 阶段 `./test.sh --full --regression` 跑出：
  ```
  ```
- `openspec validate reduce-rdd-workflow-tool-call-friction` 报：
  ```
  Change must have at least one delta. No deltas found. Ensure your change has a
  specs/ directory with capability folders (e.g. specs/http-server/spec.md)
  containing .md files that use delta headers (## ADDED/MODIFIED/REMOVED/RENAMED
  Requirements) and that each requirement includes at least one "#### Scenario:" block.
  ```
- 触发回归门 `新增失败: 1`（test_cross_repo_schemas.py::test_openspec_validate_any_active_change）
- 修复：手工写 `specs/<sub>/spec.md` 含 ADDED Requirements + Scenario blocks（22 scenarios 跨2 change），amend worktree commit，commit master
- 4 轮回归门耗时 ~32 分钟（每轮 ~8 分钟）

**根因分析**：

`guide-design/scripts/generate_full_proposal.py::generate_full_proposal()` 当前只输出 `## Why / ## What Changes / ## Capabilities / ## Impact / ## Acceptance` 段。映射表：

| source 段 | proposal.md 段 | specs/<sub>/spec.md 段 | 现状 |
|-----------|---------------|---------------------|------|
| 架构依据 | ## Why | n/a | ✅ 生成 |
| 范围 + In Scope | ## What Changes | ## ADDED Requirements | ❌ 缺失 |
| 关键场景 | n/a | #### Scenario: blocks | ❌ 缺失 |
| 技术约束 | ## Impact | ## ADDED Requirements (约束) | ❌ 缺失 |
| 验收标准 | ## Acceptance | #### Scenario: blocks (Given-When-Then) | ❌ 缺失 |
| Capabilities | ## Capabilities | n/a | ✅ 生成 |

D3 模式（D2 映射）只覆盖 `proposal.md`，缺 `specs/<sub>/spec.md` 这一对应面。openspec v1.3 时期无此强制；v1.4 升级后报错。

**影响范围**：

- 所有未来 design-pre-created change（任何由 guide-design 直接落盘的提案）都会触发同样回归门 fail
- 当前 8 个已 ship 的 design-pre-created change（含 phase-X-general-YYYYMMDD*）已通过手工或 legacy 路径规避，无回归风险
- 设计 → ship 时间被本 bug 强制拉长 30+ 分钟（regression gate 时间）

## What Changes

**In Scope**:

- 在 `generate_full_proposal()` 内部新增 `generate_spec_delta()` 子函数
- 输入：现有 `proposal.md` 内容（已生成）+ 源 `.rddf/improvements/<name>.md` 内容
- 输出：`specs/<sub>/spec.md` 内容（不含 frontmatter，纯 markdown）
- 映射规则：
- `## 验收标准` 段每个 `- [ ]` checkbox → 1 个 `### Requirement: <name>` + 1 个 `#### Scenario:` block（Given-When-Then）
- `## Capabilities` 段每条 MUST/MUST NOT → 1 个 `### Requirement: <capability>` + Scenario
- `## 关键场景` 段每条 GIVEN/WHEN/THEN → 1 个 `#### Scenario:` block 嵌入对应 Requirement
- 顶部统一加 `## ADDED Requirements` 段头（openspec v1.4 强制）
- 默认 `<sub>` 名 = `<change-name>`（与本次会话手动方案一致）
- 单元测试覆盖每种映射（acceptance / capability / scenario 路径）
- `approve_proposal.sh <name> <priority> [project_root]` 内部新增 `write_specs_file()` 步骤
- 在 `mkdir openspec/changes/<name>/` 之后、`proposal.md` 写入之前，调用 `generate_spec_delta()` 并写入 `specs/<name>/spec.md`
- 现有 idempotency 逻辑保留：`openspec/changes/<name>/specs/` 已存在则跳过（兼容本会话手工补的 case）
- `tests/integration/test_specs_generation.bats`：5 个测试覆盖 D3 路径
- `specs-generate: maps acceptance checkboxes to Requirements + Scenario blocks`
- `specs-generate: maps Capabilities MUST/MUST NOT to Requirements`
- `specs-generate: maps GIVEN/WHEN/THEN to Scenario blocks`
- `specs-generate: idempotent (existing specs/ preserved)`
- `specs-generate: validates against openspec validate v1.4 (no deltas found error)`
- AGENTS.md "D3 design-pre-created 协同" 段更新，明确 specs/ 现在由 design 阶段自动生成
- `skills/guide-design/SKILL.md` D1 编排段补 specs/ 输出说明
- **不修改** openspec CLI 内部行为
- **不修改** `validate_baseline.py` 校验逻辑（已正确，缺数据才 fail）
- **不修改** `proposal.md` 生成内容（D2 映射保持）
- **不修复** 历史 8 个 archived change 的 specs/ 缺失（它们已 ship，回归门 baseline 已稳）
- **不实现** spec delta 的 MODIFIED/REMOVED/RENAMED 复用（仅 ADDED，覆盖 design-pre-created 新增场景）

### 关键场景

### 场景 1: design 阶段 D3 路径自动生成 specs/

- **GIVEN** 用户批准 1 个 P1 proposal `reduce-rdd-workflow-tool-call-friction`（含 4 个 acceptance checkboxes + 3 个 capabilities + 3 个 scenarios）
- **WHEN** `approve_proposal.sh` 落盘阶段
- **THEN**
  - `openspec/changes/reduce-rdd-workflow-tool-call-friction/proposal.md` 写入（D2 已有）
  - `openspec/changes/reduce-rdd-workflow-tool-call-friction/specs/reduce-rdd-workflow-tool-call-friction/spec.md` 写入（新）
  - spec.md 含 1 个 `## ADDED Requirements` 段头 + 3 个 `### Requirement:` 块 + 至少 7 个 `#### Scenario:` 块（映射 4 acceptance + 3 capabilities + 3 scenarios 合并去重）
  - `openspec validate` 不再报 "No deltas found"

### 场景 2: 幂等性 — 已手工补 specs/ 不被覆盖

- **GIVEN** `openspec/changes/<name>/specs/<sub>/spec.md` 已存在（手工补过）
- **WHEN** `approve_proposal.sh` 二次运行（去重或重试场景）
- **THEN** 检测到 `specs/` 目录已存在，跳过 `write_specs_file()`，不覆盖现有内容，stdout 输出一行 `⏭️ specs already exist for <name>, skipping`

### 场景 3: 8 个 archived legacy change 行为不变

- **GIVEN** 历史上 8 个 `phase-X-general-*` change（2026-08-30 前 ship），无 specs/ 目录
- **WHEN** 本提案 ship 后重跑回归门
- **THEN** 这些 change 已被 baseline 承认（不在 KNOWN_FAILURES 也不算新增），openspec validate 仅对**活跃** change 严格校验，archive 目录不参与 validate，无 regression

### 场景 4: plan 阶段 fill 流程不变（fill 仅追加 design.md/tasks.md）

- **GIVEN** design-pre-created change 进入 plan Phase 2.5 fill
- **WHEN** `generate_design_template` + `generate_tasks_template` 被调用
- **THEN**
  - 不触碰 `specs/<sub>/spec.md`（已由 design 阶段生成）
  - design.md / tasks.md 追加内容覆盖原样
  - `openspec validate` 仍通过

### 场景 5: 缺 specs/ 的旧 active change（边界 case）

- **GIVEN** 1 个 2026-09-01 前 design-pre-created 但未 ship 的 change（缺 specs/）
- **WHEN** 本提案 ship 后重跑 validate
- **THEN**
  - `openspec validate <name>` 通过（因本提案 ship 后所有新 change 自动生成 specs/）
  - 旧缺 specs/ 的 active change 需要手动补（不在本提案范围内，由 ops 在 ship 时按需补）

**Out of Scope**:

- (no items specified)

## Capabilities

- **MUST NOT**: 改 openspec CLI 内部行为（由 vendor 决定）
- **MUST NOT**: 改 rdd-workflow core 工作流（arch/design/plan/ship/verify）阶段边界
- **MUST NOT**: 引入新依赖（仅用 Python stdlib + 现有 generate_full_proposal.py 依赖）
- **MUST NOT**: 修改 proposal.md 生成内容（D2 映射必须保持兼容）
- **MUST**: 复用现有 `generate_full_proposal.py` 的 AST/字符串处理基础设施，不重复实现 parsing
- **SHOULD**: specs/ 生成失败时 stdout 输出明确错误，但不阻断 approve（与 proposal.md 失败行为一致）
- **SHOULD**: 在 `proposal.md` 末尾追加一行 `<!-- specs/<sub>/spec.md auto-generated by guide-design D3 -->` 标识

## Impact

- (no items specified)

## Acceptance

### 单元与集成测试

- [ ] `tests/unit/test_generate_full_proposal.py` 新增 5 个测试覆盖 specs/ 生成
  - [ ] maps acceptance checkboxes to Requirements + Scenario
  - [ ] maps Capabilities MUST/MUST NOT to Requirements
  - [ ] maps GIVEN/WHEN/THEN to Scenario blocks
  - [ ] preserves manual edits (idempotency)
  - [ ] output passes openspec validate v1.4
- [ ] `tests/integration/test_specs_generation.bats` 新增 5 个 bats 测试
  - [ ] `specs-generate: end-to-end approve_proposal.sh creates specs/`
  - [ ] `specs-generate: idempotent skip when specs/ exists`
  - [ ] `specs-generate: validate against openspec CLI`
  - [ ] `specs-generate: requirements from Capabilities MUST`
  - [ ] `specs-generate: scenarios from acceptance checkboxes`
- [ ] `tests/integration/test_propose_quality.py` 已有 design-level checks 扩展为覆盖 specs/ 必填

### 端到端验证

- [ ] 复现 2026-08-31 ship 阶段场景：批准 1 个新 P1 proposal → fill → 跑 `./test.sh --full --regression` → 0 新增失败（无需手工补 specs/）
- [ ] 端到端复测 5 阶段流程 1 个新 change: 0 个 spec validation error
- [ ] `openspec validate <new-change>` 直接调 CLI 返回 `Change '<name>' is valid`
- [ ] `openspec change show <new-change> --json --deltas-only` 输出非空（含至少 1 个 ADDED Requirement）

### 文档化

- [ ] AGENTS.md "D3 design-pre-created 协同" 段更新，明确 specs/ 现在由 design 阶段自动生成（含 commit 示例）
- [ ] `skills/guide-design/SKILL.md` D1 编排段补 specs/ 输出说明（在 proposal.md 描述后）
- [ ] `docs/proposal-approved-format.md` 加新章节描述 specs/ 与 proposal.md 的对应关系

### 兼容性验证

- [ ] 复测 history 8 个 archived `phase-X-general-*` change：openspec validate 不参与 archive 目录，回归门 baseline 不变
- [ ] 复测现有 `bypass-audit-mechanism`（延迟状态）：proposal-suggestions.md 行为不变
- [ ] 与 `move-proposal-creation-to-design` (ADR-0025) 不冲突：D3 路径仍然只有 design 阶段落盘

### 副作用监测

- [ ] ship 后 30 天观察期：`guide-design approve` 调用成功率 / 回归门 0 新增率 提升 ≥ 90%（历史数据：每次 approve 后必须手工补 specs/）
- [ ] 不引入新的 KNOWN_FAILURES 条目（pre-existing WIP 不扩大）

