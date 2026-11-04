---
id: feat-fix-skill-manifest-drift
kind: feature
status: done
phase_refs: [phase-4]
主题: 消除 skill 清单漂移与断言硬编码 —— manifest 三向对齐 + 7 个 identity-merge shim 的 __spec__ + 日期无关的 sprint 断言
---

## 概述

2026-11-04 清理 `fix-agent-interface-contracts` 的回归基线时发现：`./test.sh --quick` 与 pytest 长期带 **13 个 pre-existing 失败**，且这些失败被 `tests/KNOWN_FAILURES.txt` 基线化——门禁因此被**旁路**，漂移可以无限期存活。逐条追根因后确认，13 个失败收敛到 **7 个根因**，全部属于「文档/清单/断言与事实脱节」，没有一处是产品逻辑错误。

| # | 根因 | 事实 | 修法 |
|---|------|------|------|
| 1 | **`package.json::skills[]` 少一个 skill** | 发布 27 个，磁盘 28 个（`rdd-session-bootstrap` 从未登记） | 补登记为 28，排序规范化 |
| 2 | **`skills/INSTALL.md` 计数与表体同时腐烂** | 正文写「全部 27 个子技能」；表内 `rdd-arch` / `rdd-planner` **各重复一行**；缺 `rdd-session-bootstrap` | 改为 28；删 2 行重复；补缺失行 |
| 3 | **`AGENTS.md` 两处计数陈旧** | `27 个子技能 symlink 完整性` / `27 SKILL.md + INSTALL.md` | 均改为 28 |
| 4 | **四个测试硬编码绝对计数**，新增 skill 时必须手改测试数字——**手改数字正是漂移不被发现的原因**（测试永远是「对着自己改」而非「对着磁盘」） | `test_docs_consistency.py` 断言 `== 27`；`test_doc_contracts.bats` 2 处断言 `26/27`；`test_writing_plans_integration.bats` 断言 `全部 26 个子技能`；`test_doctor_main.py` 维护一份与 `_CHECKERS` 平行的 `_CATEGORY_NAMES` 字面量（22 项，实际 23 个 checker 文件） | 全部改为**相对断言**：从 `package.json` / 磁盘 / 生产 `_CHECKERS` 派生期望值，数字不再出现在测试里 |
| 5 | **7 个 identity-merge shim 的 `__spec__` 为 `None`** | `types.ModuleType()` 手工构造的模块没有 spec，`importlib.util.find_spec()` 对其抛 `ValueError: <name>.__spec__ is None`。触发是**导入顺序相关**的（先 import 真模块则正常，先 import shim 则崩），因此单跑绿、组合跑红 | 7 个 shim 统一用 `importlib.util.spec_from_file_location()` 补 `__spec__`；新增 lint `test_skills_lib_shim_coverage.py::test_identity_merge_shims_declare_a_module_spec` |
| 6 | **两处硬编码绝对路径** | `skills/rdd-session-bootstrap/README.md` 与 change 的 `tasks.md` 写了 `/workspace/main/...` | 改为占位符（`<rdd-workflow-repo>` / `<rdd-workflow-e2e-repo>`） |
| 7 | **`test_planner_cmd.bats` 依赖挂钟** | 两个用例硬编码 `sprint-2026-11` / `sprint-2026-12`；当wall clock 走到 2026-11 时，「推进到含当前月的 sprint」被 `planner advance-sprint` 以「must move forward from」拒绝 → 测试**到点自坏** | 新增 `_next_sprint()` helper，从今天算下一个月，两个用例改为日期无关 |

## Acceptance

| AC | 判据 | 状态 |
|----|------|------|
| AC-1 | `package.json::skills[]` == 磁盘 `skills/*/SKILL.md` == `INSTALL.md` 表体，三向差集为空 | ✅ 28 / 28 / 28 |
| AC-2 | `skills/INSTALL.md` 表内无重复 skill 名 | ✅ |
| AC-3 | `AGENTS.md` 两处计数 == 磁盘数 | ✅ 28 |
| AC-4 | 四个测试文件不再出现绝对 skill / category 计数 | ✅ 改由 `package.json` / 磁盘 / `_CHECKERS` 派生 |
| AC-5 | 7 个 shim 的 `importlib.util.find_spec()` 均返回非 `None` 且 `spec.name` 与公开名一致 | ✅ 7/7 |
| AC-6 | 新增 shim lint 能捕获缺失 `__spec__`（变异验证） | ✅ 删掉任一 shim 的 `__spec__` → 用例变红 |
| AC-7 | `test_no_hardcoded_workspace_paths.py` 全绿（含本次新增的占位符替换） | ✅ 3/3 |
| AC-8 | `test_planner_cmd.bats` 在两个用例上不依赖当前月份 | ✅ 15/15 |
| AC-9 | `pytest tests/unit/` 无失败 | ✅ 3207 passed / 0 failed |
| AC-10 | `pytest tests/integration/` 无失败 | ✅ 201 passed / 0 failed |
| AC-11 | `./test.sh --quick` exit 0 | ✅ ALL PASSED |
| AC-12 | `bash tests/scripts/report_regression.sh` 新增失败 0、zombie 0 | ✅ 11 known / 0 new / 0 zombie |
| AC-13 | 外部 e2e 测试床 | ✅ 48/48 |

## Test Plan

```bash
python3 -m pytest tests/unit/ -q            # 3207 passed
python3 -m pytest tests/integration/ -q     # 201 passed
./test.sh --quick                           # exit 0
bash tests/scripts/report_regression.sh     # 0 new failures, 0 zombies
RDD_WORKFLOW_REPO="$HOME/.agents/skills/rdd-workflow" bats -r <rdd-workflow-e2e-repo>/tests/
```

## 基线处理（为什么手工删条目，而不用 `refresh_known_failures.sh`）

`refresh_known_failures.sh` 的 selective 模式会**吸收新失败**进基线——这正是漂移得以长期隐身的那台机器；且它的失败名归一规则与 `report_regression.sh` 不一致，盲目刷新会注入重复条目。故本次**只手工删除 `report_regression.sh` 判定为 zombie 的条目**，并在 `tests/KNOWN_FAILURES.txt` 末尾写明该约束与刷新前的复核步骤。

## References

- `tests/KNOWN_FAILURES.txt`（移除 3 条已修条目 + 刷新说明）
- `tests/scripts/report_regression.sh`（zombie 判定权威口径）
- `skills/_lib/` 下 7 个 identity-merge shim
