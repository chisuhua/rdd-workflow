# Fix scan-state integer comparison — wc -l newline pollution

**优先级**: P2
**阶段**: v2.1
**分类**: infra-fix

## 概要

修复 `scan-state.sh` 中 `wc -l` 输出可能含换行符导致 `integer expression expected` 错误的问题。

## 背景

- `skills/guide/scripts/scan-state.sh` L95-96 在 PTX-EMU 项目上执行时输出：
  ```
  line 96: [: 0\n0: integer expression expected
  ```
- 根因：`FS_ACTIVE_COUNT=$(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v 'archive/' | wc -l || echo 0)` 在某些 shell 环境下输出含换行符（如 `"0\n"`），`[ "$FS_ACTIVE_COUNT" -eq 0 ]` 无法处理非纯数字字符串。
- 该错误虽不影响最终推荐结果（`$FS_ACTIVE_COUNT` 非空即进入 else 分支），但产生 stderr 输出污染扫描结果，且降低用户信任度。
- 同类问题存在于 `scan-state.sh` L127、`arch_env_check.sh` L91/93/94、`plan_done_gate.sh` L91 等 10+ 处 `$() | wc -l` 赋值。

## 范围

### In Scope

- 修复 `scan-state.sh` L95 和 L127 的 `wc -l` 输出 sanitize
- 排查 `scan-state.sh` 中所有 `[-eq` / `-gt` / `-lt` 比较的变量来源
- 排查 `skills/_lib/` 中同类 `wc -l` 赋值模式
- 排查 `guide-arch/scripts/`、`guide-plan/scripts/`、`guide-ship/scripts/` 中同类模式
- 统一使用 `tr -d '[:space:]'` 或 `|| echo 0` 已有 fallback 的补强

### Out Scope

- 不修改 `scan_state()` 的推荐逻辑
- 不修改 Python 代码（`wc -l` 问题仅存在于 bash）

## 关键场景

- GIVEN `openspec/changes/` 只有 `archive/` 子目录, WHEN `scan_state` 执行 L95-96, THEN 无 shell 错误，`FS_ACTIVE_COUNT=0` 且正确进入 `guide-arch` 推荐路径
- GIVEN `openspec/changes/` 有 3 个活跃 change, WHEN L95-96 执行, THEN `FS_ACTIVE_COUNT=3`
- GIVEN 无 worktree, WHEN L127 执行, THEN `DETACHED=0` 且无 integer expression expected 错误

## 验收标准

- `scan_state` 执行时无 `integer expression expected` 错误
- `FS_ACTIVE_COUNT` 在所有场景下均为纯数字（0 / N）
- 所有 `$() | wc -l` 赋值增加防御性清理
- 现有 bats 测试全部通过