# fix-scan-state-integer-comparison

**优先级**: P2 | **来源**: Session 复盘 2026-07-26 — guide-entry 实操
**阶段**: v2.1 | **分类**: infra-fix
**类型**: fix

## 架构依据
- `skills/guide/scripts/scan-state.sh` L95-96 在 PTX-EMU 项目上执行时输出：
  ```
  line 96: [: 0\n0: integer expression expected
  ```
- 根因：`FS_ACTIVE_COUNT=$(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v 'archive/' | wc -l || echo 0)` 在某些 shell 环境下输出含换行符（如 `"0\n"`），`[-eq` 无法处理非纯数字字符串。
- 该错误虽不影响最终推荐结果（`$FS_ACTIVE_COUNT` 非空即进入 else 分支），但产生 stderr 输出污染扫描结果，且降低用户信任度。

## 范围
- **In Scope**:
  - 修复 `scan-state.sh` L95-96 的整数比较错误
  - 对其他 `$() | wc -l` 赋值做防御性清理（`tr -d '[:space:]'` 或 `${var//[[:space:]]/}`）
  - 排查 `scan-state.sh` 中所有 `[-eq` 用法是否一致
- **Out Scope**:
  - 不修改 scan_state 的推荐逻辑
  - 不新增 bats 测试（已有 coverage）

## 关键场景
- GIVEN project root 下 `openspec/changes/` 只有 `archive/` 子目录, WHEN `scan_state` 执行 L95-96, THEN 无 shell 错误，`FS_ACTIVE_COUNT=0` 且正确进入 `guide-arch` 推荐路径
- GIVEN `openspec/changes/` 有 3 个活跃 change, WHEN L95-96 执行, THEN `FS_ACTIVE_COUNT=3`

## 技术约束
- MUST 与现有 `set -euo pipefail` 兼容
- MUST NOT 改变 `scan_state()` 的返回值或 side effects

## 验收标准
- `scan_state` 执行时无 `integer expression expected` 错误
- `FS_ACTIVE_COUNT` 在所有场景下均为纯数字（0 / N）
- 3 个 `[-eq` 比较点全部增加防御性清理