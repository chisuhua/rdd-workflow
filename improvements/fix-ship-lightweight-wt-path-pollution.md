# fix-ship-lightweight-wt-path-pollution

**优先级**: P2 | **来源**: 2026-07-27 会话复盘
**阶段**: default | **分类**: core-impl
**类型**: bug

## 架构依据

- `setup_execution_workspace()` 在 `skills/guide-ship/scripts/ship_plan.sh` 中定义，函数契约（line 177 注释）："Echoes the working directory (WT_PATH) to stdout for the caller"
- worktree 模式（line 221）：仅 `echo "$wt_path"` 到 stdout，状态信息写 stderr，符合契约
- 轻量模式（line 224-229）：`git checkout` 的 "Switched to branch" + dirty 文件状态写入 stdout，`echo "⚡ 轻量模式..."` 也写入 stdout，导致调用方捕获到多条输出

## 范围

- **In Scope**:
  - Line 224：`git checkout` 追加 `>/dev/null` 吞掉 stdout
  - Line 228：`echo "⚡ 轻量模式..."` 改为 `>&2`（状态消息走 stderr）
  - 共 2 行变更

- **Out Scope**:
  - 不修改 worktree 模式（line 221 已正确）
  - 不修改调用方 `WT_PATH=$(setup_execution_workspace ...)` 的捕获方式
  - 不改变函数签名或返回值语义

## 关键场景

- GIVEN 工作区有 31 个 dirty 文件（未跟踪/修改），选择轻量模式执行
  WHEN `git checkout openspec/X` 被调用
  THEN git 不再将 dirty 文件列表输出到 stdout，`WT_PATH` 为干净的单行路径

- GIVEN 轻量模式成功切换分支
  WHEN 调用方读取 `WT_PATH` 变量
  THEN `WT_PATH = "/workspace/project/rdd-workflow"`（仅路径，无 git 输出、无状态消息）

- GIVEN 工作区干净，轻量模式执行
  WHEN `git checkout` 无 dirty 文件输出
  THEN `WT_PATH` 仍为干净单行路径（无多余换行）

## 技术约束

- **MUST**：stdout 仅输出工作目录路径（与 worktree 模式 line 221 一致）
- **MUST**：状态消息保留（改走 stderr，用户仍可看到 "⚡ 轻量模式"）
- **MUST NOT**：不改变 git checkout 错误时的 `return 1` 行为

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | 轻量模式有 dirty 文件时 WT_PATH 为单行路径 | bats：预置 dirty 文件，`WT_PATH=$(setup_execution_workspace ...)`，断言 `$WT_PATH` 不含 "M\t" 或 "⚡" |
| 2 | 状态消息 "⚡ 轻量模式" 仍在 stderr 可见 | bats：断言 stderr 含 "轻量模式" |
| 3 | worktree 模式不受影响 | 现有 bats 测试通过 |
| 4 | git checkout 失败仍正确报错 | bats：模拟 checkout 失败，断言 return 1 |
