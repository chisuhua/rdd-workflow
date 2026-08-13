# harden-plan-intake-bootstrap-and-design-gate-tests

**优先级**: P1 | **来源**: Oracle 审查（ADR-0016/ADR-0025 follow-up）
**阶段**: v2.1 | **分类**: core-test
**类型**: functional
**主题**: 不适用

## 架构依据

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

## 范围

### In Scope

按 Oracle 优先级：

1. **Gap 1 — plan_intake bootstrap edge cases**（最高优先级，entry gate blast radius）：
   - 缺失 `.design-handoff.json`（用户跳 design 直接跑 plan）
   - v1 ↔ v2 schema 混合（同一 handoff 文件 `version: 2` 但缺 `changes_pre_created`）
   - stale timestamp（`design_complete_at` 距今 >30d 的降级处理）
   - empty `changes_pre_created: []`（design 阶段无提案时）
2. **Gap 4 — bootstrap failure semantics**：trace 中断 + rddf-session 异常恢复路径
3. **Gap 3 — cross-phase integration**：design-done → plan-intake happy path（写 v2 handoff → plan 读）+ sad path（v2 handoff 缺字段 → plan 报错）
4. **Gap 2 — design gate characterization tests**（最低优先级）：`propose_quality_check.py::run_design_checks` 3 项检查的 pytest unit tests，**锁当前行为**作为 baseline

### Out Scope

- 不修改 `skills/guide-plan/scripts/plan_intake.sh` 既有逻辑
- 不修改 `skills/propose/scripts/propose_quality_check.py` 阈值
- 不修改 ADR-0016 / ADR-0025 既有 schema
- 不修改 `STRICT_DESIGN_GATE` env var 行为
- 不引入新测试框架（pytest-bdd / hypothesis / coverage）

### 不修复 / Deferred（独立提案）

- **Option B 重构**（拆分 plan_intake.sh 为 testable 函数如 `validate_design_handoff()`）：交付物 = 重构 + 重测，规模超本提案范围。如需推进，新开 `.rddf/improvements/refactor-plan-intake-testability.md`
- **Option C property-based testing**（hypothesis / quickcheck 随机 JSON 生成）：违反 `tests/README.md` "do not add mocking/coverage frameworks" 约定，且 `plan_intake.sh` 是 bash，property-based 收益有限。永久拒绝
- **Gap 2 假阳性根因修复**：若 characterization tests 揭示 `run_design_checks` 真实 false positives，新开 `.rddf/improvements/fix-propose-quality-check-false-positives.md`，附 pytest 失败用例为证据

## 关键场景

- GIVEN 用户跳过 `guide-design` 直接跑 `guide-plan`，WHEN plan_intake 执行，THEN 检测到 `.design-handoff.json` 缺失并退出非零 + 输出引导信息（不静默通过）。
- GIVEN `.design-handoff.json` 标 `version: 2` 但缺 `changes_pre_created` 字段，WHEN plan_intake 验证，THEN 按 v1 fallback 处理（`changes_pre_created` 视为空数组）+ warning 日志，不阻断。
- GIVEN `.design-handoff.json` 的 `design_complete_at` 距今 >30 天，WHEN plan_intake 验证，THEN 输出"handoff is stale, consider re-running guide-design"警告 + 不阻断（保留用户决策权）。
- GIVEN `.design-handoff.json` 的 `changes_pre_created: []`（design 阶段无提案），WHEN plan_intake 验证，THEN 输出"no proposals to plan, exiting" + 退出非零，引导用户跑 `guide-design` 先创建提案。
- GIVEN `.rddf/state/trace/` 包含中断 trace（缺 `finalize_at`），WHEN plan_intake 启动前做 stale check，THEN 输出"interrupted trace from <timestamp>, run `rddf orchestrate show <phase>` to triage"提示 + 不阻断 plan intake。
- GIVEN `sessions.json` 含 abandoned session（`end_reason: user-abandoned-via-guide-design-transition`），WHEN plan_intake 启动，THEN 标记 session 为 orphan + 提示用户运行 `rddf-session archive-history` 清理，不阻断。
- GIVEN `guide-design` 写出 v2 design-handoff 含 `changes_pre_created: ["new-prop"]`，WHEN `guide-plan` intake 执行，THEN 读取 `changes_pre_created` 并跳过 plan 阶段的 propose 步骤（v2 happy path 已有 test_plan_intake_design_pre_created.bats，本提案加固 sad path）。
- GIVEN `guide-design` 写出的 v2 handoff 缺 `version` 字段但有 `changes_pre_created`，WHEN `guide-plan` intake 执行，THEN 警告"incomplete v2 handoff, treating as v1" + 走 v1 fallback 路径。
- GIVEN 合法 improvement 文件（head frontmatter 完整 + 5 段齐全 + ADR refs ≥1），WHEN `propose_quality_check.py::run_design_checks` 执行，THEN pytest 锁当前 3 项检查通过率（characterization baseline）。
- GIVEN 已知边缘 improvement 文件（head 缺 `**类型**` 字段），WHEN `run_design_checks` 执行，THEN 锁当前返回结果（characterization baseline，**不修复**，仅文档化）。

## 技术约束

- MUST 复用 `test_plan_intake_staleness.bats` 的 fixture pattern（tmpdir + `source plan_intake.sh` + `SKIP_ARCH_HANDOFF=yes` + `RDDF_PROJECT_ROOT` in `setup()`）。
- MUST 使用现有 bats + pytest 框架，遵循 `tests/README.md` 约定。
- MUST 每个 bats 测试用独立 tmpdir，避免状态污染。
- MUST characterization tests（Gap 2）锁**当前** `run_design_checks` 行为，**不修改**实现，**不期待**特定结果（接受 false positive 也接受 false negative）。
- MUST NOT 引入新测试框架（mocking/coverage/property-based）— `tests/README.md` 明确禁止。
- MUST NOT 修改 `plan_intake.sh` / `propose_quality_check.py` 既有实现。
- MUST NOT 修改 ADR-0016 / ADR-0025 既有 schema。
- MUST 接受标准：每条 AC 命名具体验证命令（`./test.sh --full --regression` 或 targeted pytest/bats 路径）。
- SHOULD 在测试失败信息中包含 handoff 字段路径（如 `design-handoff.changes_pre_created`），便于排错。
- SHOULD characterization tests 用 `@pytest.mark.characterization` 标记，与功能测试视觉区分。

## 验收标准

1. **Gap 1 测试**：新增 `tests/integration/test_plan_intake_bootstrap_edges.bats` ≥4 cases：
   - 缺失 `.design-handoff.json` → plan_intake 失败 + 引导信息
   - v2 handoff 缺 `changes_pre_created` → 走 v1 fallback
   - stale `design_complete_at` → warning 但不阻断
   - empty `changes_pre_created: []` → 退出 + 引导跑 design

2. **Gap 4 测试**：新增 `tests/integration/test_plan_intake_failure_semantics.bats` ≥2 cases：
   - 中断 trace → warning 提示 + 不阻断
   - abandoned rddf-session → orphan 标记 + 不阻断

3. **Gap 3 测试**：新增 `tests/integration/test_plan_intake_cross_phase.bats` ≥2 cases：
   - design v2 happy path（含 `changes_pre_created`）→ plan 跳过 propose（增强既有 `test_plan_intake_design_pre_created.bats` 的 edge case）
   - design v2 sad path（缺 `version`）→ warning + v1 fallback

4. **Gap 2 测试**：新增 `tests/unit/test_propose_quality_check_characterization.py` ≥3 tests（用 `@pytest.mark.characterization`）：
   - 合法 improvement → 3 项检查通过率
   - 缺 `**类型**` head 字段 → 当前行为锁
   - In-Out Scope 缺失 → 当前行为锁

5. **验证命令**：所有新增测试通过 `./test.sh --full --regression` 验证全绿，且 `tests/KNOWN_FAILURES.txt` baseline 无新增失败条目。

6. **行数约束**：单 bats 文件 ≤150 行（与现有 `test_plan_intake_staleness.bats` 量级一致）；单 pytest 文件 ≤200 行。

7. **零实现改动**：`git diff --stat skills/guide-plan/scripts/plan_intake.sh skills/propose/scripts/propose_quality_check.py` 输出为空（验证"测试 only"约束）。

8. **文档更新**：`tests/README.md` 新增"characterization tests"小节，说明 `@pytest.mark.characterization` 用途（锁当前行为 vs 期待通过）。