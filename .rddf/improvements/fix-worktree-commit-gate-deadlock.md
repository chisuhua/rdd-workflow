---
优先级: P1
来源: 2026-11-29 change `fix-commit-gate-generator-fake-green` 的 P2 实测（worktree 模式提交被 commit-gate 拒）+ 用户裁决切 lightweight
阶段: phase-3
分类: quality-gate
类型: fix
状态: 待审查
主题: worktree 模式下 commit-gate 必红 —— 6 条 root-resolver 判据按已废止的「git toplevel」契约断言
---

**优先级**: P1 | **来源**: P2 实测 + 用户裁决 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: fix

**主题**: worktree 模式下 commit-gate 必红 —— 6 条 root-resolver 判据按已废止的「git toplevel」契约断言

## 架构依据

`commit-gate` 的声明（`.rddf/commit-gate.json`）跑 `./test.sh --gates` + `./test.sh --quick`，其中
`--quick` 含 **pytest unit**（3826 例）。而以下 6 条在 **linked worktree 内恒红、在主仓恒绿**（2026-11-29 实测两遍）：

```
tests/unit/test_resolve_project_root_contract_python.py::test_python_cli_does_not_honor_env_override
tests/unit/test_resolve_project_root_contract_python.py::test_invariant_env_override_empty_falls_through[skill_wrapper-_resolve_wrapper]
tests/unit/test_resolve_project_root_contract_python.py::test_invariant_env_override_empty_falls_through[cli_dispatcher-_resolve_cli]
tests/unit/test_resolve_project_root_contract_python.py::test_invariant_git_probe_returns_toplevel_when_in_repo[skill_wrapper-_resolve_wrapper]
tests/unit/test_resolve_project_root_contract_python.py::test_invariant_git_probe_returns_toplevel_when_in_repo[cli_dispatcher-_resolve_cli]
tests/unit/test_skills_lib_python_resolve_project_root.py::test_behavioral_parity_with_dispatcher_resolver
```

**根因**：`_lib/cli/__main__.py::resolve_project_root` 的 docstring（`Behavior matrix (ADR-0033 / submodule-aware-project-root)`）
**明文规定**「linked worktree（same flag empty）⇒ 返回**主仓根**」，实现也照做；
而这 6 条用例断言的是 `git rev-parse --show-toplevel`（= worktree 自己的根）⇒ **判据比契约旧**。

失败形态：`assert '/workspace/main/rdd-workflow' == '/workspace/main/rdd-workflow/.rddf/wt/<name>'`。

**后果（本次实测）**：worktree 模式的 change **无法通过任何一次 commit**
（门禁 fail-closed：`验证命令失败 ⇒ 拒绝提交`）⇒ 只能靠切 lightweight 绕过（本次即如此）。

## 范围

**In Scope**：

- 把上述 6 条用例改成断言**现行契约**：主仓 ⇒ 主仓根；**linked worktree ⇒ 主仓根**；submodule ⇒ 自身工作树根；
- 若 design 认为契约应反向（worktree ⇒ worktree 根），则必须先改 `resolve_project_root` + docstring + ADR-0033 的边界，
  **再**改用例（二者不可各改一半）；
- 加一条跨模式守卫：在 worktree 内跑这 6 条必须绿（例：bats 里建临时 worktree 后执行）。

**Out of Scope**：

- 不改 `commit-gate` 的判据（D3 / 三判据 / `verify_commands` 选型）；
- 不动 `--quick` 的组成（它含 pytest unit 是设计选择，不是缺陷）。

## 关键场景

1. 主仓内跑这 6 条 ⇒ 绿（现状已绿，保持）。
2. **linked worktree 内**跑这 6 条 ⇒ 绿（现状红 ⇒ 修复目标）。
3. submodule 内跑 ⇒ 仍返回 submodule 自身根（既有行为不回退）。

## 技术约束

- 判据必须**从契约派生**（docstring / ADR-0033 的行为矩阵），不得凭感觉选择；
- 若改契约，必须同批改 docstring + 用例 + ADR（三者任一漏改即视为假绿）；
- 不引入对 worktree 路径的硬编码（fixture 自建临时 worktree）。

## 验收标准

- [ ] AC1（红→绿）新增「临时 linked worktree 内跑这 6 条」的用例/脚本 ⇒ 修复前红、修复后绿；
- [ ] AC2 主仓内这 6 条仍绿（非回归）；
- [ ] AC3 submodule 场景仍返回自身根（既有 `test_submodule_*` 全绿）；
- [ ] AC4 变异：把 `resolve_project_root` 改回 toplevel 语义 ⇒ AC1 必须红（证明用例真的盯契约）；
- [ ] AC5 门：`./test.sh --full --regression` 全绿；`openspec validate <change> --strict` valid。

## Capabilities

- MUST: worktree 模式下的 commit 能通过 `commit-gate`（本缺陷的直接后果）。
- MUST: 用例与 `resolve_project_root` 的 docstring/ADR 三者一致。
- MUST NOT: 单方面放宽判据来「让 worktree 绿」。

## Impact

| 面 | 影响 |
|---|---|
| `tests/unit/test_resolve_project_root_contract_python.py` | 6 条中的 5 条 |
| `tests/unit/test_skills_lib_python_resolve_project_root.py` | 1 条 |
| 所有 worktree 模式的 change | 解除「无法提交」死锁 |
