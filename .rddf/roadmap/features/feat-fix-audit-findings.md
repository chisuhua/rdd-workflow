---
id: feat-fix-audit-findings
kind: feature
status: done
phase_refs: [phase-1, phase-2, phase-3, phase-4]
主题: 2026-08-26 文档与代码一致性审计后续修复
---

## 概述

2026-08-26 文档与代码一致性审计产出 4 个 follow-up 子提案，全部已在 2026-09-10 由 design-done 批准 + ship，归入 `improvement-approved.md` "已实施" 段（L186-189）。

| 子提案 | 优先级 | ship 时间 | 核心改动 |
|---|---|---|---|
| `fix-parametrize-planner-feedback-id-date` | P2 | 2026-09-10 | 重构 5 个 hardcode 日期测试为 `tmp_path` fixture，解决时间炸弹 |
| `fix-rebuild-adr-index-for-0049-0050` | P2 | 2026-09-10 | 重生成 `docs/adr/README.md` 索引（补 ADR-0049/0050） |
| `fix-update-doctor-main-category-count` | P2 | 2026-09-10 | 测试断言 10→11（新 gitignore category），提取 `_CATEGORY_NAMES` 常量 |
| `fix-remove-stale-filled-at-regression-test` | P3 | 2026-09-10 | 改 `TestFilledAtRegression` 用 `tmp_path` fixture（保留意图） |

> **2026-09-22 收尾**：本 fragment 仍保留为历史记账（4 子项已 ship，但 fragment prose 段长期 TBD 占位未填）。本次 status 同步 `active → done` + 概述段填充。后续跟进由 `feat-fix-archive-gaps-v2`（第二波归档治理改进，已 done）承接。

## 跨阶段拆分

### phase-1
- ✅ `fix-parametrize-planner-feedback-id-date`（P2）— 重构 `tests/unit/test_planner_feedback_id_uniqueness.py` 等 5 个 hardcode 日期测试
- ✅ `fix-rebuild-adr-index-for-0049-0050`（P2）— 触发 `adr-index-auto-sync` 实施（关联 `feat-fix-archive-gaps-v2` phase-1）

### phase-2
- ✅ `fix-update-doctor-main-category-count`（P2）— 同步 `_lib/doctor.py` 与测试断言（10→11 个 category）

### phase-3
- ✅ `fix-remove-stale-filled-at-regression-test`（P3）— `tests/integration/test_cli_all_subcommands.py::TestFilledAtRegression` 改 `tmp_path` fixture

### phase-4
- （无 phase-4 子项；4 个子项已跨 phase-1..3 分布）


## 验收标准
- [x] 4 个子提案全部 ship（2026-09-10 批量 design-done，归入 `improvement-approved.md` L186-189 "已实施" 段）
- [x] 无重叠：4 个提案触及不同测试文件（`test_planner_feedback_id_uniqueness.py` / `test_adr_index_gate.py` / `test_doctor_main.py` / `test_cli_all_subcommands.py`），无 file conflict
- [x] KNOWN_FAILURES baseline 减 10 项（5+2+2+1）
