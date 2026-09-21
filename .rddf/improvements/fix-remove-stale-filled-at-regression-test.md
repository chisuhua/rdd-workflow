---
优先级: P3
来源: 2026-09-10 KNOWN_FAILURES baseline (1 个 pytest unit 失败)
阶段: v4.x
分类: test-fix
类型: bugfix
主题: 多方对称 + 回归
---
**优先级**: P3 | **来源**: 2026-09-10 KNOWN_FAILURES baseline (1 个 pytest unit 失败)
**阶段**: v4.x | **分类**: test-fix | **类型**: bugfix
**主题**: 多方对称 + 回归

## Why

`tests/unit/test_cli_all_subcommands.py::TestFilledAtRegression::test_actual_repo_iteration_json_validates_after_fix` 断言:

```python
has_filled_at = any("filled_at" in change for change in data.get("changes", []))
assert has_filled_at, ("Repo iteration.json no longer contains filled_at — "
                       "this test has lost its purpose; remove or update it.")
```

但 `.rddf/state/iteration.json` 的 `changes[]` **没有任何 change 含 `filled_at`**。错误消息自己就说"this test has lost its purpose; remove or update it"。

**测试设计意图**: commit `fix-iteration-schema-filled-at` (历史 archive 2026-06-09) 修复 iteration v5 schema 拒绝 `filled_at` 字段的 bug。v6 schema 应"接受 as-is"。测试用 repo 自己的 `iteration.json` 作为 fixture 验证 schema 不拒绝。**测试不该依赖真实仓库文件**,因为仓库状态会随 archive 流变化 — 测试应是独立可重现的(create tmp_path fixture)。

## What Changes

- **推荐选项 B**(保留意图,消除依赖):
  - 把 fixture 改为 `tmp_path`:构造一个含 `filled_at` 的临时 iteration.json
  - 测试函数:`schema validator 接受含 filled_at 的 iteration.json`
  - 测试逻辑不变,只换 fixture 来源
- 或 **选项 A**(若意图不再有意义):直接删除整个 `TestFilledAtRegression` class

## 架构依据

- `_lib/iteration/store.py` schema v6 已稳定接受 `filled_at`
- pytest fixture 标准:`tmp_path` 让测试独立可重现,不依赖仓库 state
- AGENTS.md 顶部 v3.0+ 状态注释说测试不应依赖真实文件

## 范围

- **In Scope**:
  - 重写或删除 `tests/unit/test_cli_all_subcommands.py::TestFilledAtRegression::test_actual_repo_iteration_json_validates_after_fix`
  - 提取 `tmp_path` fixture 或构造最小 valid iteration.json
- **Out of Scope**:
  - 不动 `_lib/iteration/store.py` 或 schema(产品代码稳定)
  - 不回填 `.rddf/state/iteration.json` 的 `filled_at`(那是数据层)
  - 不改 `TestFilledAtRegression` 内其他非失败测试(若它们已用 tmp_path)

## Capabilities

- MUST 使用 `tmp_path` fixture 而非依赖仓库真实文件
- MUST 保留原意图(schema validator 接受 `filled_at`)—若选选项 B
- SHOULD 加注释解释"为什么不依赖真实 iteration.json"
- SHOULD 把 docstring 反映新意图
- SHOULD NOT 改测试断言为逆命题("schema REJECTS filled_at")— 与历史修复方向相反

## Impact

- 关联: KNOWN_FAILURES.txt 的 `test_actual_repo_iteration_json_validates_after_fix` 条目应在本提案完成后移除
- 关联: 与 `fix-parametrize-planner-feedback-id-date` / `fix-rebuild-adr-index-for-0049-0050` / `fix-update-doctor-main-category-count` 同期处理
- 不影响产品行为,纯测试代码

## Acceptance

见上「验收标准」段。

## 验收标准

- [ ] `pytest tests/unit/test_cli_all_subcommands.py::TestFilledAtRegression::test_actual_repo_iteration_json_validates_after_fix` 通过
- [ ] 测试函数体内 grep `.rddf/state/iteration.json` 命中 0 行
- [ ] 测试函数用 `tmp_path` 构造 fixture
- [ ] 测试 docstring 反映新意图
- [ ] `pytest tests/unit/test_cli_all_subcommands.py` 全套不引入新失败
