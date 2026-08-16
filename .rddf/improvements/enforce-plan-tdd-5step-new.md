# enforce-plan-tdd-5step-new

**优先级**: P2 | **来源**: rdd-doctor 诊断 2026-08-16 — plan-tdd 类别 63 WARNING(全是 06-08 月老 plans)
**阶段**: v2.2 | **分类**: quality
**类型**: debt

## 架构依据

- **`rdd-workflow-writing-plans` skill**(已实施): 内置 TDD 5 步结构 plan 生成器,要求 step markers:
 1. Write the failing test
 2. Run test to verify it fails
 3. Write minimal implementation
 4. Run test to verify it passes
 5. Defer commit
- **rdd-doctor plan-tdd 类别**(已实施): 检测 `.rddf/plans/*.md` 中 5 个 step markers 完整性
- **现状缺陷**: 06-08 月老 plans(63 个)缺失 TDD markers — 这些是历史债务。但若未来新 plans 也缺失 markers,会破坏 `execute` step-by-step 解析(`execute` 可能误读 steps,见 AGENTS.md "常见陷阱")
- **类比 anchor**: 与 `add-full-regression-gate` 同类问题 — 都是"已经实施过,但缺强制 gate"

## 范围

- **In Scope**:
 - 在 `guide-ship/SKILL.md` Phase 2 execute 之前(或 Phase 3 archive 之前)添加 `plan-tdd-check` step
 - `plan-tdd-check` 调用 `rddf doctor --category plan-tdd --quiet`,失败时返回非零
 - 失败时引导用户:(a) 修复 plan 后重试 / (b) 显式 `SKIP_PLAN_TDD_CHECK=yes` 跳过(留 audit trail)
 - 添加 `tests/integration/test_guide_ship_plan_tdd_check.bats` 覆盖 3 个场景:compliant plan / non-compliant plan / explicit skip
- **Out Scope**:
 - **NOT backfill 63 个老 plans**(noise reduction)— 老 plans 是历史债务,backfill 会触发大量 git churn,价值低
 - **NOT 修改 `rdd-doctor` 检测逻辑**(已正确检测)— 只加 enforcement
 - **NOT 修改 `rdd-workflow-writing-plans` plan 模板**(已是 canonical 5-step)— 只加 enforcement

## 关键场景

- GIVEN 新 change 提交,plan 含完整 5 个 TDD markers
- WHEN `guide-ship` Phase 2 execute 启动前调用 `plan-tdd-check`
- THEN check 退出 0,execute 正常启动

- GIVEN 新 change 提交,plan 缺失 `Defer commit` step
- WHEN `plan-tdd-check` 运行
- THEN 返回 `ERROR: missing TDD step markers: Defer commit`,archive 阻断

- GIVEN 老 plan(写于 canonical 5-step 纪律之前)需要 ship
- WHEN 用户设置 `SKIP_PLAN_TDD_CHECK=yes` 并 re-run
- THEN 跳过 check,留 audit log(包含 plan 文件路径 + skip reason)

## 技术约束

- MUST 与 `rdd-workflow-writing-plans` skill 的 5-step canonical markers 完全匹配
- MUST NOT 阻塞 `SKIP_PLAN_TDD_CHECK=yes` opt-out(老 plans 必须能 ship)
- MUST 留下 audit log(包括跳过原因) — 防止"所有人都跳过"反模式
- SHOULD 仅对 06-08 月前的 plans 推荐 skip(新 plans 强制要求)— 在 `plan-tdd-check` 输出中给出建议

## 验收标准

- `tests/integration/test_guide_ship_plan_tdd_check.bats` 3 个 case 全 PASS
- `guide-ship` Phase 3 archive 前会调用 `plan-tdd-check`,CRITICAL 时阻断
- 新 plan 缺失任何 1 个 canonical step marker 时,`rddf doctor --category plan-tdd` 报 ERROR(severity 升级)
- `SKIP_PLAN_TDD_CHECK=yes` opt-out 工作正常,audit log 记录