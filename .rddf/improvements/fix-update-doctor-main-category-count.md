---
优先级: P2
来源: 2026-09-10 KNOWN_FAILURES baseline (2 个 pytest unit 失败)
阶段: v4.x
分类: test-fix
类型: bugfix
主题: 多方对称 + 回归
---
**优先级**: P2 | **来源**: 2026-09-10 KNOWN_FAILURES baseline (2 个 pytest unit 失败)
**阶段**: v4.x | **分类**: test-fix | **类型**: bugfix
**主题**: 多方对称 + 回归

## Why

`tests/unit/test_doctor_main.py` 2 个测试断言 rdd-doctor 类别数 **exactly 10**,但产品代码实际有 **11 个类别**:

```
skills/rdd-doctor/scripts/checks/  (排除 __init__.py)
├── docs_consistency_check.py
├── gitignore_check.py            ← 新增 (commit add-gitignore-hard-protection 2026-09-10)
├── migration_residue_check.py
├── orphan_gates_check.py
├── plan_tdd_check.py
├── proposal_section_check.py
├── proposal_table_check.py
├── roadmap_meta_check.py
├── roadmap_refs_check.py
├── state_schema_check.py
└── tasks_checkbox_check.py
= 11 个 run_check() 函数
```

测试逻辑"exactly N categories wired"本身对,只是 N 漂移了。修测试断言比动产品更合适 — 产品已稳定 5 个月,改动风险大于收益。

## What Changes

- `tests/unit/test_doctor_main.py::test_aggregate_runs_all_10_categories` 集合增补 `"gitignore"` 条目
- `tests/unit/test_doctor_main.py::test_checkers_dict_has_10_entries` 断言 `len(_CHECKERS) == 10` → `== 11`
- docstring 数字更新: "all 10 categories" → "all 11 categories" / "exactly 10 categories wired" → "exactly 11 categories wired (10 baseline + gitignore)"
- 提取 `_CATEGORY_NAMES = frozenset({...})` 常量(下次新增只改一处)

## 架构依据

- rdd-doctor v1.0+ 设计:每个 category 一个独立 check 文件,便于第三方项目选择性启用
- `add-gitignore-hard-protection` (2026-09-10) 新增 gitignore 类别是为了检测 `.rddf/project.yaml` `git.openspec_tracked` × `.gitignore` `openspec/` 一致性,详见 AGENTS.md rdd-doctor 段
- 测试"exactly N categories"是 regression lock,数字应自动随产品变更

## 范围

- **In Scope**:
  - 修测试断言(2 处)
  - 提取 `_CATEGORY_NAMES` 常量(防下次同样漂移)
- **Out of Scope**:
  - 不动 `skills/rdd-doctor/scripts/checks/` 任何文件
  - 不动 `rdd-doctor/SKILL.md` 类别列表(已 11)
  - 不回填 KNOWN_FAILURES.txt(本提案完成后应移至"已修复"段)

## Capabilities

- MUST 更新断言数字 10 → 11
- MUST 集合硬编码补 `"gitignore"` 条目
- SHOULD 用 `_CATEGORY_NAMES = frozenset({...})` 常量替代硬编码
- SHOULD 在 docstring 写明"baseline 10 + gitignore"避免下次漂移
- SHOULD NOT 改测试断言的"≥ N"风格(失去 regression lock)
- SHOULD 加 sanity assertion:`len(os.listdir('skills/rdd-doctor/scripts/checks')) - 1 == len(_CHECKERS)` 锁住"目录文件数 == 类别数"不变量

## Impact

- 关联: KNOWN_FAILURES.txt 的 2 个 `test_doctor_main.py::*` 条目应在本提案完成后移除
- 关联: 与 `fix-parametrize-planner-feedback-id-date` / `fix-rebuild-adr-index-for-0049-0050` / `fix-remove-stale-filled-at-regression-test` 同期处理
- 不影响产品行为,纯测试代码

## Acceptance

见上「验收标准」段。

## 验收标准

- [ ] `pytest tests/unit/test_doctor_main.py::test_aggregate_runs_all_10_categories` 通过
- [ ] `pytest tests/unit/test_doctor_main.py::test_checkers_dict_has_10_entries` 通过
- [ ] `_CATEGORY_NAMES` 常量定义并被两个测试使用
- [ ] docstring 数字与 assertion 一致
- [ ] `git diff tests/unit/test_doctor_main.py` 仅显示 10 → 11 / 集合增项,无其他逻辑变更
