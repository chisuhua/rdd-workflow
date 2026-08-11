# fix-rddf-session-owner-cross-call

**优先级**: P1 | **来源**: Session 复盘 2026-07-26 — session close owner mismatch
**阶段**: v2.1 | **分类**: planning
**类型**: fix

## 架构依据
- Session 复盘：guide-plan 结束时 `rddf_session_hook_close` 输出：
  ```
  rddf-session close skipped: Active stage_plan session rds_b80d90fb1c35 owned by my-eci-group_99204; caller my-eci-group_100069
  ```
- 根因：rddf-session 的 owner 基于 `OPENCODE_SESSION_ID`（回退到 `$(hostname -s)_$$`）。每次 AI 通过 `bash -c` 调用 hook 脚本时，`$$` 取新 shell 的 PID，形成不同 owner。创建者和关闭者被判定为不同进程，关闭被拒。
- 影响：每个 guide 阶段结束时 session 保持 active，积累 orphaned sessions（当前已有 6 个）。用户无法显式关闭，流程不干净。
- 预期行为：在同一个 opencode session 内部，同一阶段创建的 session 应在退出时正常关闭。

## 范围
- **In Scope**:
  - 解决跨 `bash -c` 调用的 owner 不一致问题
  - 方案 A：hook 脚本通过环境变量传递持久的 `OPENCODE_SESSION_ID`（如 `RDSD_OWNER_ID`），覆盖 `$(hostname -s)_$$` 回退
  - 方案 B：close hook 增加 `--force` 模式（warning 级），允许同一流程的 close 操作
  - 方案 C：entry hook 的输出（session ID）被保存并显式传递给 close hook
  - 评估并选择最优方案实施
- **Out Scope**:
  - 不修改 rddf-session 的底层 owner 验证机制（跨 session 安全保护仍需要）
  - 不影响其他 rddf-session 功能（list/show/resume/abandon）

## 关键场景
- GIVEN `rddf_session_hook_entry` 在 `bash -c` 中创建 session, WHEN `rddf_session_hook_close` 在同一 opencode session 中调用（不同 `bash -c`）, THEN session 正常关闭
- GIVEN `rddf_session_hook_entry` 在 opencode session A 中创建, WHEN session B 尝试关闭, THEN 拒绝（跨 session 安全保护正常工作）

## 技术约束
- MUST 不引入安全漏洞（不能让人随意关闭别人的 session）
- MUST 兼容现有 `sessions.json` 格式
- MUST 不修改 `_with_file_lock` 的并发控制机制

## 验收标准
- guide-arch/plan/ship 的 entry + close hook 在同一个 opencode session 内正常配对
- 无新的 orphaned session 产生
- 跨 session 关闭仍然被拒绝
- 2+ bats 测试覆盖