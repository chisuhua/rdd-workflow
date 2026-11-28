---
优先级: P1
来源: 2026-11-29 change `fix-commit-gate-generator-fake-green` 归档实测——worktree 内修好的 delta 没有回到主仓，归档用的是 P0 的陈旧副本
阶段: phase-3
分类: quality-gate
类型: fix
状态: 待审查
主题: worktree 内对 openspec/changes/** 的修改不会回主仓 ⇒ 归档用的是陈旧 delta（且 openspec validate 不报）
---

**优先级**: P1 | **来源**: 归档实测 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: fix

**主题**: worktree 内对 `openspec/changes/**` 的修改不会回主仓 ⇒ 归档用的是陈旧 delta（且 validate 不报）

## 架构依据

P2 把 change artifacts **单向**搬进 worktree（`skills/rdd-builder/scripts/phase2_execute.sh::_carry_artifacts`，
清单 = `openspec/changes/<name>` + `.rddf/plans/<name>.md`）；
P3 在 `openspec_tracked=false` 时**回主仓归档**，`openspec archive` 读的是**主仓**的
`openspec/changes/<name>/specs/…` —— **没有任何一步把 worktree 里的改动搬回来**。

**本次实测（2026-11-29，change `fix-commit-gate-generator-fake-green`）**：

1. P0 在主仓生成了 delta（当时生成器未修 ⇒ D 形态：旧场景 + 同名新场景，共 2 条）；
2. P2 在 worktree 里修好生成器后**重生成** delta（同名场景 **1** 条），`openspec validate --strict` valid（在 worktree 内）；
3. P3 归档 ⇒ 主 spec 出现**两条同名、THEN 互相矛盾**的场景；`openspec validate --specs` **169 passed / 0 failed**（不报）。

⇒ 归档产物与「被验收的东西」不是同一份，而唯一的守卫（validate）对此**无感**。

## 范围

**In Scope**：

- 归档前把 worktree 内的 change artifacts 同步回主仓（或改判「归档以 worktree 副本为准」），
  并在 design 写清**哪个副本权威**；
- 加一条守卫：归档后主 spec 里**同一 requirement 下不得有同名 Scenario**
  （openspec 只按场景名查守恒，查不出重复标题 ⇒ 必须本地断言）；
- 覆盖 lightweight 模式：该模式没有 worktree，天然不受影响，但守卫要一并覆盖。

**Out of Scope**：

- 不改 `openspec archive` 的语义（第三方 CLI）；
- 不改 P2 的 carry 清单（它只负责**搬进去**）。

## 关键场景

1. worktree 内改 delta ⇒ 归档后主 spec 用的是**新** delta（现状用旧的 ⇒ 修复目标）。
2. 主 spec 出现同名 Scenario ⇒ 守卫报错并拒绝归档（现状静默）。
3. lightweight 模式 ⇒ 行为不变（主仓即工作区）。

## 技术约束

- 同步必须**只**搬 change artifacts（`openspec/changes/<name>` + `.rddf/plans/<name>.md`），不得 `git add -A`；
- 守卫必须可机判（`grep -c '^#### Scenario:'` per requirement），不得靠人读；
- 冲突（两侧都改）⇒ fail-closed 并指名，不静默择一。

## 验收标准

- [ ] AC1（红→绿）fixture：worktree 内改 delta 后归档 ⇒ 主 spec 反映**新**语义（现状反映旧的 ⇒ 红）；
- [ ] AC2（红→绿）fixture：人为造同名 Scenario ⇒ 归档前守卫拒绝（现状静默通过 ⇒ 红）；
- [ ] AC3 变异：关掉同步 ⇒ AC1 红；关掉守卫 ⇒ AC2 红；
- [ ] AC4 lightweight 模式行为不变（既有归档用例全绿）；
- [ ] AC5 门：`./test.sh --full --regression` 全绿；`openspec validate --all --strict` valid。

## Capabilities

- MUST: 归档所用的 change artifacts 与验收时的副本一致。
- MUST: 同名 Scenario 必须被本地守卫拦下（openspec 查不出）。
- MUST NOT: 用 `git add -A` 之类的宽粒度同步把别的 change 改动带进来。

## Impact

| 面 | 影响 |
|---|---|
| `skills/rdd-builder/scripts/phase3_archive.sh` | 归档前的同步 / 守卫挂载点 |
| `_lib/archive.sh` | 同名 Scenario 守卫 |
| 所有 worktree 模式的 change | 归档产物与验收对象一致 |
