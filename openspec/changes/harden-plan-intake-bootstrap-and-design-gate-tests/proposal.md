# harden-plan-intake-bootstrap-and-design-gate-tests

## Why

- ADR-0016（arch artifact discovery contract）：`.arch-handoff.json` v1 schema 含 `adr_dir`/`roadmap_path`/`architecture_dir`/`adr_pattern`/`discovered` 字段，下游 consumer 优先读 handoff + fallback 默认值
- ADR-0025（design proposal creation）：`.design-handoff.json` v2 schema 含 `changes_pre_created` 数组 + `version: 2`；`plan_intake.sh::check_design_handoff` 接受 v1 与 v2
- ADR-0018（arch_quality_gate）+ ADR-0019（change_alignment）：gate 机制 reference，约束 `propose_quality_check.py::run_design_checks` 的 3 项检查（≥500 chars / ADR refs / In-Out Scope）
- ADR-0024（deps-driven execution mode）：`.plan-handoff.json` schema reference，约束 `current_change`/`execution_mode_decisions` 字段
- AGENTS.md 状态文件清单（`iteration.json` 是多 hook 写入 view 文件，handoff 文件由单端写入）：handoff reader 应做 staleness 检查
- 现有 test patterns（参考 follow）：
  - `tests/integration/test_plan_intake_staleness.bats` — tmpdir + `source plan_intake.sh` + `SKIP_ARCH_HANDOFF=yes` + `RDDF_PROJECT_ROOT` export in `setup()`
  - `tests/integration/test_plan_intake_design_handoff_v2.bats` — v2 handoff happy path
  - `tests/integration/test_plan_intake_design_pre_created.bats` — `changes_pre_created` happy path
- Oracle 审查（2026-08-13）：dogfooding ADR-0016/0025 implementation 后识别 4 类 test gaps
- 仓库现状佐证 gap-1 真实存在：`.plan-handoff.json` 当前 `current_change` 指向已归档的 `complete-third-party-replay-and-upstream-reporting`，与空 `openspec/changes/` 不一致，正是 gap-1 的"stale handoff"用例

核心原则：**测试覆盖深度比实现修改更重要**。harden 测试等于 harden 契约，实现 bug 通过后续 fix proposal 独立修复。

## What Changes

**In Scope**:

1. **Gap 1 — plan_intake bootstrap edge cases**（最高优先级，entry gate blast radius）：
   - 缺失 `.design-handoff.json`（用户跳 design 直接跑 plan）
   - v1 ↔ v2 schema 混合（同一 handoff 文件 `version: 2` 但缺 `changes_pre_created`）
   - stale timestamp（`design_complete_at` 距今 >30d 的降级处理）
   - empty `changes_pre_created: []`（design 阶段无提案时）
2. **Gap 4 — bootstrap failure semantics**：trace 中断 + rddf-session 异常恢复路径
3. **Gap 3 — cross-phase integration**：design-done → plan-intake happy path（写 v2 handoff → plan 读）+ sad path（v2 handoff 缺字段 → plan 报错）
4. **Gap 2 — design gate characterization tests**（最低优先级）：`propose_quality_check.py::run_design_checks` 3 项检查的 pytest unit tests，**锁当前行为**作为 baseline

**Out of Scope**:

- 不修改 `skills/guide-plan/scripts/plan_intake.sh` 既有逻辑
- 不修改 `skills/propose/scripts/propose_quality_check.py` 阈值
- 不修改 ADR-0016 / ADR-0025 既有 schema
- 不修改 `STRICT_DESIGN_GATE` env var 行为
- 不引入新测试框架（pytest-bdd / hypothesis / coverage）

## Capabilities

- `tests/integration/test_plan_intake_bootstrap_edges.bats` 覆盖 4 类缺失场景
- `tests/integration/test_plan_intake_failure_semantics.bats` 覆盖 trace/session 异常恢复
- `tests/integration/test_plan_intake_cross_phase.bats` 覆盖 design→plan 跨阶段 handoff 传递
- `tests/unit/test_propose_quality_check_characterization.py` 锁当前 `run_design_checks` 行为为 baseline
- 测试遵循 `tests/README.md` 约定（tmpdir + `source plan_intake.sh` + `SKIP_ARCH_HANDOFF=yes`）
- 新增 `@pytest.mark.characterization` 标记区分 baseline 测试与功能测试

## Impact

- 不修改既有实现代码（`plan_intake.sh` / `propose_quality_check.py` 字节级不变）
- 不修改 ADR-0016 / ADR-0025 既有 schema 字段
- 新增 4 个 bats 文件 + 1 个 pytest 文件（共 ~600 行测试代码）
- `tests/README.md` 新增"characterization tests"小节说明 `@pytest.mark.characterization` 用途
- 行数约束：单 bats 文件 ≤150 行，单 pytest 文件 ≤200 行（与现有 `test_plan_intake_staleness.bats` 量级一致）

## Acceptance

- [ ] Gap 1: `tests/integration/test_plan_intake_bootstrap_edges.bats` ≥4 cases（缺失 handoff / v2 缺字段 / stale timestamp / empty array）
- [ ] Gap 4: `tests/integration/test_plan_intake_failure_semantics.bats` ≥2 cases（中断 trace / abandoned session）
- [ ] Gap 3: `tests/integration/test_plan_intake_cross_phase.bats` ≥2 cases（v2 happy path 增强 / v2 sad path fallback）
- [ ] Gap 2: `tests/unit/test_propose_quality_check_characterization.py` ≥3 tests（用 `@pytest.mark.characterization`：合法 improvement / 缺 `**类型**` / In-Out Scope 缺失）
- [ ] 验证命令：`./test.sh --full --regression` 全绿，且 `tests/KNOWN_FAILURES.txt` baseline 无新增失败条目
- [ ] 行数约束：单 bats 文件 ≤150 行，单 pytest 文件 ≤200 行
- [ ] 零实现改动：`git diff --stat skills/guide-plan/scripts/plan_intake.sh skills/propose/scripts/propose_quality_check.py` 输出为空
- [ ] 文档更新：`tests/README.md` 新增"characterization tests"小节，说明 `@pytest.mark.characterization` 用途（锁当前行为 vs 期待通过）