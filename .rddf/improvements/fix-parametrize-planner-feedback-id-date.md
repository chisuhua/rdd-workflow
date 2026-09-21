---
优先级: P2
来源: 2026-09-10 KNOWN_FAILURES baseline (5 个 pytest unit 失败)
阶段: v4.x
分类: test-fix
类型: bugfix
主题: 多方对称 + 回归
---
**优先级**: P2 | **来源**: 2026-09-10 KNOWN_FAILURES baseline (5 个 pytest unit 失败)
**阶段**: v4.x | **分类**: test-fix | **类型**: bugfix
**主题**: 多方对称 + 回归

## Why

`tests/unit/test_planner_feedback_id_uniqueness.py` 5 个测试**时间炸弹**:硬编码 `pf-20260905-NNN` 日期字符串。生产代码 `_lib/planner_feedback.py::compute_planner_feedback()` 用 `datetime.now(timezone.utc).strftime("%Y%m%d")` 生成 prefix,任何非 2026-09-05 的运行日都失败(今天 2026-09-10 触发)。简单改 hardcode 只是把炸弹推到未来某天。正确做法:**测试不依赖真实当前日期**。

## What Changes

- 重构 `tests/unit/test_planner_feedback_id_uniqueness.py` 5 个失败测试用 `tmp_path` fixture + `date_prefix="20260115"` 固定 reference date 替代 `_today_prefix()`
- 或通过 monkeypatch `datetime.now(timezone.utc)` 返回固定 datetime
- 测试在任意 UTC 日期运行都保持绿

## 架构依据

- Wave 4 Sub-task 1.2 (`compute_fingerprint` / counter logic) — 设计为按日 prefix 避免跨日 collision
- Hardcoded date 测试违反"test in isolation"原则
- pytest fixture 标准实践:用 `tmp_path` + parametrize 而非依赖系统时间

## 范围

- **In Scope**:
  - `tests/unit/test_planner_feedback_id_uniqueness.py` 5 个失败测试重构
  - conftest.py 加 `_fixed_utc_now` fixture(若其他测试也需)
- **Out of Scope**:
  - 不动 `_lib/planner_feedback.py` 产品代码(其行为正确)
  - 不动 `_today_prefix()` 内部逻辑
  - 不回填 KNOWN_FAILURES.txt(本提案完成后应移至"已修复"段)

## Capabilities

- MUST 使用 pytest fixture / parametrize / monkeypatch,**禁止** `time.sleep()` / `freezegun` 依赖
- MUST 保留原测试语义(same-day recompute / counter at max+1 / cross-day isolation / malformed skip / missing-key skip)
- MUST NOT 改变 `_today_prefix()` 语义
- SHOULD 在 conftest 加 `_fixed_utc_now` fixture 共享时间锚点
- SHOULD 加 regression test 锁住"测试不依赖系统时间"meta-invariant

## Impact

- 关联: KNOWN_FAILURES.txt 的 5 个 `test_planner_feedback_id_uniqueness.py::*` 条目应在本提案完成后移除
- 关联: 与 `fix-rebuild-adr-index-for-0049-0050` / `fix-update-doctor-main-category-count` / `fix-remove-stale-filled-at-regression-test` 同期处理(都是 2026-09-10 baseline 失败)
- 不影响产品行为,纯测试代码

## Acceptance

见上「验收标准」段。

## 验收标准

- [ ] `pytest tests/unit/test_planner_feedback_id_uniqueness.py` 5 个失败测试全绿
- [ ] 测试在任意 UTC 日期运行稳定(`date` shell 命令验证 3 个不同日期都绿)
- [ ] 测试不依赖系统时间(可通过 `faketime` 或 monkeypatch `datetime.now` 验证)
- [ ] 修改前先加 regression test 锁住"硬编码日期应被替换"
- [ ] `git diff --stat` 净增 ≤ 100 行
