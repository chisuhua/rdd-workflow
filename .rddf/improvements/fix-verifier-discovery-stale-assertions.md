---
优先级: P1
来源: 2026-11-29 `./test.sh --full --regression` 实测（8 条「新增失败」）+ 主仓 HEAD 复现（与 change fix-commit-gate-generator-fake-green 无关）
阶段: phase-3
分类: quality-gate
类型: fix
状态: 待审查
主题: verifier 队列发现的 8 条 bats 判据停留在「iteration.json 派生」时代，disk 派生后恒红
---

**优先级**: P1 | **来源**: `--full --regression` 实测 + 主仓 HEAD 复现 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: fix

**主题**: verifier 队列发现的 8 条 bats 判据停留在「iteration.json 派生」时代，disk 派生后恒红

## 架构依据

`--regression` 报 8 条「新增失败」（不在 `tests/KNOWN_FAILURES.txt`），主仓 HEAD 同样失败（2026-11-29 两处复现）：

```
test_rdd_verifier_helpers.bats  : scan_queue.sh: filters implemented task-complete changes
                                  scan_queue.sh: honors RDDF_VERIFIER_MAX_CHANGES
test_rdd_verifier_skip.bats     : skip: --max-changes 2 limits scan output to 2 changes
                                  skip: RDDF_VERIFIER_MAX_CHANGES env var honored as default
                                  skip: --max-changes CLI flag overrides env var
test_rdd_verifier_hook_provider.bats : hook-provider: exit 1 → rdd-verify rc 1 (failed)
                                       hook-provider: exit 2 → rdd-verify rc 3 (error)
```

**根因**：这些用例只写 `.rddf/state/iteration.json` fixture，**不建 `openspec/changes/<name>/` 目录**；
而 `fix-verifier-discovery-disk-derive`（2026-11-27 归档）已把发现改成 **disk 派生**
（`_lib/verifier/discovery.py::discover_eligible`）⇒ 没有 change 目录就**没有 eligible**。

实测复现（scratch 仓，只放 iteration.json + 4 个 change 条目）：

```
$ bash skills/rdd-verifier/scripts/scan_queue.sh
（空输出，rc=0）        # 用例期望 "a c"
```

## 范围

**In Scope**：

- 上述 8 条用例补建 change 目录（`openspec/changes/<fixture-name>/`，含 `proposal.md` + `tasks.md`），
  使其在 disk 派生下仍有 eligible；
- 若 design 认为「无 change 目录也应在队列里」是期望行为，则改 `discover_eligible`
  **并**同步 `_lib/verifier/discovery.py` 的 docstring / 该 change 的 spec Requirement（不可各改一半）。

**Out of Scope**：

- 不动 `rddf rdd-verify` 的 CLI 契约（退出码 / flag）；
- 不刷新 `tests/KNOWN_FAILURES.txt` 来「吸收」这 8 条（那正是该文件头部警告的反模式）。

## 关键场景

1. fixture 只有 iteration.json ⇒ 现状返回空（用例红）；修复后用例应显式建目录并断言非空，或断言「无目录 ⇒ 空」。
2. 真实仓（有 change 目录）⇒ 队列非空（既有行为）。

## 技术约束

- 判据必须与 `discover_eligible` 的现行 docstring 一致；
- 用例不得依赖本仓真实 `.rddf/state/iteration.json`（隔离门要求）；
- 变异：把 disk 派生关掉 ⇒ 新用例必红。

## 验收标准

- [ ] AC1 上述 8 条全绿（`bats tests/integration/test_rdd_verifier_{helpers,skip,hook_provider}.bats`）；
- [ ] AC2 `bash tests/scripts/report_regression.sh` 不再把这 8 条列为「新增失败」；
- [ ] AC3 变异：恢复「只写 iteration.json 不建目录」的 fixture ⇒ 用例必须红（证明判据真的盯 disk 派生）；
- [ ] AC4 门：`./test.sh --full --regression` 全绿；`openspec validate <change> --strict` valid。

## Capabilities

- MUST: 用例与 `discover_eligible` 的现行判据一致。
- MUST NOT: 用 baseline 刷新掩盖过期判据。

## Impact

| 面 | 影响 |
|---|---|
| `tests/integration/test_rdd_verifier_helpers.bats` | 2 条 |
| `tests/integration/test_rdd_verifier_skip.bats` | 3 条 |
| `tests/integration/test_rdd_verifier_hook_provider.bats` | 2 条 |
| 所有 change 的 archive 回归门 | 解除 8 条「新增失败」噪音 |
