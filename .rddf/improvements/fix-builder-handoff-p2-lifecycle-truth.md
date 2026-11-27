---
优先级: P1
来源: 2026-11-26 CppTLM 立项会话（session ses_de7dcca7fffeOvO830nfolajk4）—— P2 建好 worktree 即写 execution_status=completed（实测中断态）+ oracle/critic 双审（2026-11-26）
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 已批准·待立项（planner 2026-11-27 · W4 = U5 · 独立 change · 消费方已裁决 = P2.5 review · 7 条 AC 含 TDD 三段）
主题: P2 生命周期真实性 —— setup 完成 ≠ 实现完成 + worktree 与主仓分叉的可检出性
---

**优先级**: P1 | **来源**: 2026-11-26 CppTLM 立项会话实测 | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **「消费方」未定 ⇒ AC4 不可写** ⇒ 已标「design 裁决前不可写」，并保留「找不到消费方 ⇒ 降级 noted」的退出条件。
- **AC3 会连带打红既有** `tests/unit/test_builder_handoff.py:30/47`（用的正是 `in-progress`）⇒ 须**同批**改（归一到 `running` 或补进 schema enum，design 裁决）。
- **AC5 的「基线」语义未定义**（P2 前 worktree 尚不存在）⇒ 钉死 = 上次 P2 记录的 `branch_base_sha`。
- 旧 handoff 兼容：存量 `.rddf/state/builder/*.json` 全是 setup 语义的 `completed` ⇒ 「按 setup 解释」在 archive gate 类消费方会产生新歧义 ⇒ 需迁移或豁免策略（design 阶段补）。
- 已改：AC3 连带修改说明；AC4 可写性标注；AC5 基线语义。


**主题**: P2 生命周期真实性 —— setup 完成 ≠ 实现完成 + worktree 与主仓分叉的可检出性

## 架构依据

**问题 1 · 状态骗人**：`skills/rdd-builder/scripts/phase2_execute.sh:288` 在**准备阶段结束**（worktree 建好）时写
`execution_status="completed"`。CppTLM 会话实测：会话在 TDD Task 1/2 中途中断时，worktree 内 5 个文件已改**未提交**、
`tasks.md` 全未勾，而 handoff 已写 `execution_status: completed` ⇒ 续接会话 / 看板 / 任何读 handoff 的下游都会
误判「实现已完成」。

**问题 2 · 无消费方 ⇒ 拆分是纯化妆**：实测 `execution_status` 在**生产代码里只有写入方**
（`phase2_execute.sh:288` + `_lib/builder_handoff.py:40/96` 默认值），**没有任何门控读它** ⇒ 只改字面量没有行为收益。

**问题 3 · 主仓与 worktree 静默分叉**：`_carry_artifacts()`（`phase2_execute.sh:98-115`）只搬
`openspec/changes/<name>` 与 `.rddf/plans/<name>.md`；`git worktree add` 从 **HEAD** 建 ⇒ **P2 之后**主仓才 commit 的产物
（如授权台账 Entry）不在 worktree 内。CppTLM 会话实测：台账 Entry #556 在主仓 commit 后，需 agent 手工
`git -C $WT merge --ff-only` 才能让 worktree 看见。

## delta 载体（P0 生成输入）

**delta**: added builder-lifecycle-truth
**语义要求**: Builder handoff SHALL distinguish setup from completion | `execution_status` SHALL reflect the real implementation state, never the setup step: Phase 2 setup writes `running` (never `completed`), and `completed` is written only when the change is archived. The Phase 2.5 review — the merge decision point — SHALL display the implementation's true progress (checked tasks over total) and SHALL report an inconsistency when the handoff claims `completed` while tasks remain unchecked. Legacy handoffs written under the old setup semantics SHALL stay readable and SHALL be interpreted without crashing. | A setup-only handoff does not claim completion | Phase 2 setup finished while no task is checked yet | the handoff records `running` instead of `completed`, and the Phase 2.5 review shows the unchecked task count

## 范围

**In Scope**:

- `_lib/builder_handoff.py` + `_lib/schemas/builder_handoff_schema.json`：`execution_status` 语义拆分 ——
  区分「**setup 完成**」与「**tasks 完成**」（新增字段或加态），旧值**兼容读**（存量 handoff 全是 setup 语义）；
  顺带收敛枚举外野值 `in-progress`（`tests/unit/test_builder_handoff.py:30/47` 已在用，schema 未收录 ⇒ 落盘不校验 enum）；
- `phase2_execute.sh`：setup 完成时**不**再置 `completed`；改为置 setup 语义；
- **补消费方**（否则本条降级 noted）：明确哪个门控按新语义判定（候选：P2.5 review 前置 / archive gate / dashboard 展示），
  并在 design 阶段裁决唯一消费方；
- 分叉可检出性：P2 前置检查 —— 主仓有未提交的 tracked 改动，或主仓 HEAD 领先于 worktree 基线 ⇒ 明确提示
  「先把授权类产物 commit，再建 worktree」；carry 覆盖清单写进 `skills/rdd-builder/SKILL.md` 的 P2 前置清单；
- 与 backlog `preship-dirty-check`（P2，仅管 archive 前主仓脏）**划界**：本条管 P2 建 worktree 前 + 分叉，不是同一面。

**Out of Scope**:

- 不改 `_is_eligible` / 归档门语义；
- 不改 `_carry_artifacts` 的**搬运实现**（只补「哪些路径属于授权类产物」的清单与前置检查）；
- 不实现「自动把主仓新 commit 同步进 worktree」（风险高，改为**检出 + 提示**）；
- 不动 `.rddf/state/`（gitignored 运行态）的其它文件。

## 关键场景

1. P2 准备完成但实现未开始 ⇒ handoff 的状态**不**显示「完成」（当前显示 completed）。
2. 会话在 P2 中途终止后新会话接手 ⇒ 从 handoff 能看出「setup 已完成、tasks 未完成」。
3. 主仓在 P2 之后有新 commit（worktree 看不到）⇒ P2 前的检查**报出**该差异（commit sha + 文件清单）。
4. 主仓有未提交的 tracked 改动 ⇒ P2 前检查提示「先 commit 授权类产物」。
5. 存量 handoff（旧 `completed` 值）被读取 ⇒ 按 setup 语义解释，不炸、不误判完成。

## 技术约束

- **必须有消费方**：若 design 阶段找不到「按新语义判定」的门控点 ⇒ 本条降级为 noted（只改字段无行为收益），
  **不得**提交一个纯化妆的 schema 变更；
- 兼容：旧 handoff 读取不炸（存量 `.rddf/state/builder/*.json` 全是 setup 语义）；必要时双读 + 迁移函数；
- enum 收敛：`in-progress` 归一为 schema 枚举内的值（`running`）或补进枚举（**二选一，design 阶段裁决**）；
- 前置检查**只读**（不得自动 commit / 自动 merge）。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_builder_handoff_lifecycle.py`：用例「P2 准备完成后 `execution_status` ≠ `completed`」
      ⇒ 修复前红 ⇒ 修复后绿；
- [ ] **AC2（红→绿）** 同文件用例：旧 handoff（`completed`）读取**不炸**且按 setup 语义解释（兼容读）；
- [ ] **AC3（红→绿）** 同文件用例：`in-progress` 落盘后 schema 校验**通过**（枚举收敛）⇒ 修复前红 ⇒ 修复后绿；
      ⚠ **连带修改**：既有 `tests/unit/test_builder_handoff.py:30/47` 用的正是 `in-progress` ⇒ 本 AC 落地会
      **打红那两处**，必须**同批**改（归一到 `running` 或补进 schema enum，**design 阶段裁决**）；
- [ ] **AC4（消费方）** 用例：存在**至少一个**门控点按新语义判定（以该门控的既有测试扩展断言，命名注明消费方）
      ⇒ 若找不到消费方，本 AC 不可满足 ⇒ 触发「降级 noted」的退出条件；
      ⚠ **本 AC 在 design 裁决消费方之前不可写**（先定消费方，再落断言）；
- [ ] **AC5（红→绿）** 新增 `tests/integration/test_phase2_prereq_check.bats`：构造「主仓 HEAD 领先 worktree 基线」
      ⇒ P2 前检查输出含 commit sha 与文件清单 ⇒ 修复前红 ⇒ 修复后绿；
      ⚠ **「基线」语义钉死 = 上次 P2 记录的 `branch_base_sha`**（`phase2_execute.sh` 已写入 handoff）⇒ 不是「当前 HEAD」；
- [ ] **AC6（变异）** 把 `phase2_execute.sh:288` 的值改回 `completed` ⇒ AC1 用例必须红（判别力证明）；
- [ ] **AC7（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。

## Capabilities

- MUST: handoff 区分「setup 完成」与「tasks 完成」，续接者不会误判实现已完成。
- MUST: 存量 handoff 兼容读（不炸、不回退语义）。
- MUST: P2 前能检出「主仓领先 worktree」与「主仓有未提交 tracked 改动」。
- MUST NOT: 在没有消费方的情况下提交 schema 变更（无行为收益的纯化妆）。
- MUST NOT: 自动 commit / 自动 merge 主仓内容到 worktree。

## Impact

| 面 | 影响 |
|---|---|
| `_lib/builder_handoff.py` + `_lib/schemas/builder_handoff_schema.json` | 状态字段语义拆分 + 枚举收敛 |
| `skills/rdd-builder/scripts/phase2_execute.sh` | setup 语义 + P2 前置检查 |
| `skills/rdd-builder/SKILL.md` | P2 前置清单（carry 覆盖 + 授权产物先 commit） |
| `tests/unit/` + `tests/integration/` | 新增 2 处测试 |
| backlog `preship-dirty-check` | 需声明边界（archive 前主仓脏 ≠ P2 前分叉） |
