# fix-ship-archive-resolve-lib-path

**优先级**: P1 | **来源**: 隔离 playground 全流程验证 — lightweight archive global install failure
**阶段**: v2.1 | **分类**: ship
**类型**: fix

## 架构依据

`guide-ship/scripts/ship_archive.sh` 的 lightweight archive pre-flight 直接读取 `$project_root/_lib/validate_delta_targets.py`。第三方项目通常没有项目本地 `_lib/`；全局安装的实现应通过现有 `resolve_rdd_lib_dir` 解析，因此当前代码会在 archive 前错误失败。

## 范围

- **In Scope**:
  - 在 lightweight archive validation 中使用 `resolve_rdd_lib_dir` 找到 `validate_delta_targets.py`。
  - 无法解析共享库时输出明确错误并保持 fail-closed。
  - 增加外部项目无本地 `_lib`、仅使用 global install 的 archive 回归测试。
- **Out of Scope**:
  - 不改变 delta target validation 规则。
  - 不改变 lightweight/worktree archive 的其他流程。
  - 不创建项目本地 `_lib` symlink 作为运行时依赖。

## 关键场景

### 场景 1：外部项目使用全局库归档

- GIVEN active change 已提交且项目没有 `_lib/`
- AND `~/.agents/skills/_lib/validate_delta_targets.py` 存在
- WHEN lightweight archive 执行 pre-flight
- THEN 通过 `resolve_rdd_lib_dir` 找到并运行 validator
- AND archive 可以继续执行

### 场景 2：共享库不可用

- GIVEN archive helper 无法解析共享 `_lib`
- WHEN validation pre-flight 执行
- THEN 输出明确的解析失败信息
- AND archive 返回非零，不绕过验证

## 技术约束

- 沿用现有 bootstrap 和 `resolve_rdd_lib_dir`，不新增依赖。
- validator 的 stdout/stderr 和返回码语义保持不变。

## 验收标准

- `ship_archive.sh` 不再使用 `$project_root/_lib/validate_delta_targets.py`。
- 外部项目无本地 `_lib` 时 lightweight archive 验证通过。
- 缺失共享库时 archive 明确失败。
- 相关 focused tests 和全量 regression gate 通过。
