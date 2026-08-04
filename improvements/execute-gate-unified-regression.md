# execute-gate-unified-regression

**优先级**: P2 | **来源**: Session 复盘 2026-08-04 — Execute gate 回归覆盖不均
**阶段**: v2.1 | **分类**: quality
**类型**: feature

## 架构依据
- 实测：execute 阶段 3 个 worktree 的回归验证入口不统一——worktree 1 有 `tests/scripts/report_regression.sh`（完整递归 bats + 基线对比），worktree 2/3 只能跑聚焦 bats + smoke，未执行完整 `bats tests/ --recursive`
- Execute gate 的"全量回归"检查依赖各 change 自身是否恰好引入报告脚本，存在覆盖缺口
- 仓库已建立 KNOWN_FAILURES 基线（add-known-failures-baseline），可复用于所有 change 的 execute 回归

## 范围
- **In Scope**:
  - execute 技能（或 guide-ship Execute gate）增加统一全量回归步骤：默认运行 `bats tests/ --recursive`，若存在 `tests/KNOWN_FAILURES.txt` 则用 report_regression.sh 对比基线
  - `SKIP_REGRESSION=1` 逃生舱保留
  - 1 个 bats 测试：验证 gate 在有/无基线文件时的两种路径
- **Out Scope**:
  - 不重复实现 report_regression.sh（复用 add-known-failures-baseline 的脚本）
  - 不改变 ctest/cmake 构建验证逻辑

## 关键场景
- **GIVEN** 任意 change 进入 Execute 收尾
  **WHEN** 运行全量回归门
  **THEN** 无论该 change 是否自带报告脚本，都执行完整 bats 递归并输出与基线对比的增量失败报告

## 技术约束
- report_regression.sh 若不存在（未归档 add-known-failures-baseline 的仓库），降级为普通 `bats tests/ --recursive`，不报错

## 验收标准
- execute gate 对所有 worktree 统一执行完整递归 bats
- 基线存在时输出增量失败对比；基线缺失时正常降级
- 1 个 bats 测试覆盖两条路径
