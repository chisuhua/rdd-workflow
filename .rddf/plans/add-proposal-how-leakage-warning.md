# 实施计划: add-proposal-how-leakage-warning

> 对应 Change: `openspec/changes/add-proposal-how-leakage-warning`
> 基于: tasks.md 中的 8 组 25 任务
> ADR 引用: ADR-0019 §3.1/§3.2 (保守反模式检查) + ADR-0025 §D1/D2/D4 (双层内容审查)
> 实施位置: 主线轻量模式 (`openspec/add-proposal-how-leakage-warning` branch, 无 worktree)

## 概览

| 阶段 | 任务组 | 工作量 | 风险 |
|------|--------|--------|------|
| Heuristic Definition | 1.1-1.3 | 3 任务 | 低（纯定义） |
| Implementation | 2.1-2.3 | 3 任务 | 中（新建模块） |
| Integration (双层 wiring) | 3.1-3.3 | 3 任务 | 中（修改 2 个审查层） |
| Default Behavior | 4.1-4.3 | 3 任务 | 低（不阻断） |
| Threshold Configuration | 5.1-5.2 | 2 任务 | 低 |
| Regression Coverage | 6.1-6.6 | 6 任务 | 中（新增测试覆盖） |
| Empirical Hit Collection | 7.1-7.2 | 2 任务 | 中（持久化命中） |
| Verification | 8.1-8.3 | 3 任务 | 低（验证 + 完整性） |

## 实施策略

**TDD 5 步结构**: 每个子任务按 Write failing test → Verify fail → Implement → Verify pass → Commit 顺序执行。

**顺序**: 1 (定义) → 2 (核心实现) → 5 (配置) → 3 (wiring) → 4 (默认行为验证) → 6 (测试) → 7 (命中采集) → 8 (终验)

**聚合 commit**: Phase 2.7 统一聚合 1 个 commit（不逐任务 commit）。

## 关键文件

| 文件 | 操作 | 来源任务 |
|------|------|---------|
| `skills/_lib/proposal_review.py` | CREATE | 2.1 |
| `skills/_lib/proposal_review_config.py` | CREATE | 5.1 (阈值配置) |
| `skills/guide-design/scripts/design_content_review.py` | MODIFY | 3.1 (wire detector) |
| `skills/propose/scripts/propose_quality_check.py` | MODIFY | 3.2 (wire detector) |
| `.rddf/state/.how-leakage-hits.json` | CREATE (gitignored) | 7.1 (命中采集) |
| `tests/unit/test_proposal_review.py` | CREATE | 6.1-6.5 (单元测试) |
| `tests/integration/test_how_leakage_warning.bats` | CREATE | 6.6 (集成测试) |

## 实施步骤 (TDD 5 步)

### Group 1: Heuristic Definition (Tasks 1.1-1.3)

直接定义在 `skills/_lib/proposal_review_config.py`，无 TDD 步骤（纯声明）。

### Group 2: Implementation (Tasks 2.1-2.3) — TDD

- **Step 1 (Write failing test)**: 创建 `tests/unit/test_proposal_review.py::test_detector_importable`
- **Step 2 (Verify fail)**: 跑 `python3 -m pytest tests/unit/test_proposal_review.py::test_detector_importable` → 模块不存在 → FAIL ✓
- **Step 3 (Implement)**: 创建 `skills/_lib/proposal_review.py`:
  - 4 个启发式信号（code-fence / signature / file-list / step-density）
  - `detect_how_leakage(text: str, config: dict) -> list[WarningRecord]` 接口
  - `WarningRecord` TypedDict `{signal, threshold, section, action}`
  - 预编译正则（模块级 `_compile_patterns()`）
- **Step 4 (Verify pass)**: 跑单元测试 → PASS ✓
- **Step 5 (Commit)**: 此组不入 commit（统一聚合）

### Group 3: Threshold Configuration (Tasks 5.1-5.2)

- 创建 `skills/_lib/proposal_review_config.py`，导出 `THRESHOLDS` dict + 阈值依据 docstring

### Group 4: Integration Wiring (Tasks 3.1-3.3) — TDD

- **Step 1 (Write failing test)**: `tests/integration/test_how_leakage_warning.bats` 测试 improvements + proposal 层都返回 warning
- **Step 2 (Verify fail)**: 跑 bats → 无 detector hook → FAIL ✓
- **Step 3 (Implement)**:
  - 修改 `design_content_review.py::review_improvements` 调用 `proposal_review.detect_how_leakage`
  - 修改 `propose_quality_check.py::run_design_checks` 调用同一 detector
  - 两层共用 `WarningRecord` 格式（满足 3.3）
- **Step 4 (Verify pass)**: bats 集成测试 → PASS ✓
- **Step 5 (Commit)**: 聚合 commit

### Group 5: Default Behavior Verification (Tasks 4.1-4.3)

- 单测: `test_default_warning_does_not_block` 验证默认输出 warning 但不抛 exit code
- 单测: `test_user_can_ignore_warning` 验证无副作用
- 单测: `test_no_auto_rewrite` 验证原内容 hash 一致

### Group 6: Regression Coverage (Tasks 6.1-6.6)

扩充 `tests/unit/test_proposal_review.py`:
- 6.1: 4 类信号各 1 个 test
- 6.2: `test_single_weak_signal_no_warning`
- 6.3: `test_section_aware_weighting`
- 6.4: `test_non_fatal_parse_failures` (missing section / empty file / non-standard markdown)
- 6.5: `test_no_auto_rewrite` (验证 hash)
- 6.6: `./test.sh --full --regression` 全绿

### Group 7: Empirical Hit Collection (Tasks 7.1-7.2)

- 7.1: detector 在 emit warning 时追加写入 `.rddf/state/.how-leakage-hits.json`（gitignored）
- 7.2: 在 `proposal_review.py` 顶部 docstring 记录 metric: `user_confirmed_false_positive_rate`

### Group 8: Final Verification (Tasks 8.1-8.3)

- 8.1: `openspec validate add-proposal-how-leakage-warning --type change --json` → no errors
- 8.2: 现有测试套件 PASS，无新增 LLM/向量 DB 依赖
- 8.3: git diff 确认 `proposal-suggestions.md` / 其他 proposals / ADR / 历史未受影响

## 验收标准

1. 4 个启发式信号均可独立触发且可配置
2. 默认 warning-only，不阻断 create/approve/design-done/plan-done
3. improvements 层 + proposal 层输出统一 `WarningRecord` 格式
4. 单一弱信号不触发 warning（抑制条件有效）
5. 段落级定位（`section` 字段记录触发段落）
6. 无内容改写（hash 校验）
7. 解析失败非致命（缺段/空文件/非标准 Markdown）
8. 命中统计持久化到 `.how-leakage-hits.json`
9. `./test.sh --full --regression` 全绿或仅 baseline 已知失败
10. `openspec validate` 通过

## 风险与回退

- **风险**: 启发式可能误报合法技术内容 → 配置 `multi_signal_threshold=2` + 段落加权
- **回退**: 单 PR revert，无数据迁移
- **保守模式**: 未来 strict 模式需新增独立 env var（沿用 `STRICT_*_GATE=yes` 约定）