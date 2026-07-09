## 1. Schema 准备

- [ ] 1.1 修改 `state_vector.py` 的 `_SCHEMA`，移除根层 `additionalProperties: false` 限制，允许 session_management 字段
- [ ] 1.2 创建 `skills/_lib/schemas/sessions_schema.json`（rddf-session JSON Schema）
- [ ] 1.3 验证现有 unit tests 全部通过（schema 修改向后兼容）

## 2. rddf-session 核心实现

- [ ] 2.1 创建 `skills/_lib/rddf_session.py`（RddfSessionCoordinator + 原子写 + 心跳 + 冲突检测）
- [ ] 2.2 实现 `create_session()` / `find_session()` / `update_session_status()` / `list_sessions()`
- [ ] 2.3 实现 `attach_change()` / `detach_change()` 用于 attached_changes 生命周期
- [ ] 2.4 实现 `_atomic_write()` 复用 state_vector 模式
- [ ] 2.5 实现心跳刷新 + 超时检测 `_check_heartbeat()`

## 3. 单元测试

- [ ] 3.1 创建 `tests/unit/test_rddf_session.py`
- [ ] 3.2 测试用例：创建 + 重检测 + 父子关系 + 心跳刷新 + 心跳超时 → orphaned
- [ ] 3.3 测试用例：4 种冲突场景（同 owner / 不同 owner active / 不同 owner orphaned / 无 active）
- [ ] 3.3 测试用例：4 种软提示选项（放弃/转移/强制/查看）
- [ ] 3.4 测试用例：attached_changes 添加/归档清理
- [ ] 3.5 测试用例：arch-done → completed, plan-done → completed, archive all → completed
- [ ] 3.6 测试用例：sessions.json schema 校验 + 原子写并发安全
- [ ] 3.7 测试用例：同 opencode session 重复调用幂等性

## 4. Skill 集成

- [ ] 4.1 修改 `skills/guide-arch.md` 入口添加 rddf-session 创建逻辑（kind=stage_arch）
- [ ] 4.2 修改 `skills/guide-plan.md` 入口添加 rddf-session 创建逻辑（kind=stage_plan, parent=arch）
- [ ] 4.3 修改 `skills/guide-ship.md` 入口添加 rddf-session 创建逻辑（kind=stage_ship, parent=plan）
- [ ] 4.4 修改 `guide-arch.md` 在 arch-done 通过时关闭 session
- [ ] 4.5 修改 `guide-plan.md` 在 plan-done 通过时关闭 session
- [ ] 4.6 修改 `guide-ship.md` 在 archive_change 完成后关闭 session
- [ ] 4.7 创建 `skills/rddf-session.md`（list/show/resume/abandon/archive-history 子命令）

## 5. 集成测试

- [ ] 5.1 创建 `tests/integration/test_rddf_session_lifecycle.py`
- [ ] 5.2 测试完整 lifecycle：创建 → 心跳刷新 → 完成 → 跨 opencode session 读取
- [ ] 5.3 测试 worktree 完全解耦（rddf-session 不持有 worktree_path）
- [ ] 5.4 测试 session 间冲突恢复（创建 A → 模拟 B → 软提示 → 转移 → 继续）

## 6. 文档与 ADR

- [ ] 6.1 创建 `docs/adr/ADR-0017-rddf-session.md`
- [ ] 6.2 更新 `docs/adr/ADR-0010-multi-session-management.md` 状态为"已实施"
- [ ] 6.3 更新 `docs/adr/README.md` 索引表加 ADR-0017
- [ ] 6.4 更新 `docs/v2-workflow-overview.md` 增加 rddf-session 章节（含 4.5 + 闭环 11）
- [ ] 6.5 更新 `docs/v2-multi-session-guide.md` 增加 rddf-session 用户指南
- [ ] 6.6 更新 `AGENTS.md` 关键约定状态文件表加 sessions.json 行

## 7. 最终验证

- [ ] 7.1 运行所有 unit tests（≥150 通过）
- [ ] 7.2 运行所有 integration tests（全部通过）
- [ ] 7.3 运行 bats tests（无回归）
- [ ] 7.4 运行 `openspec validate add-rddf-session` 验证
- [ ] 7.5 检查 git log（5+ 聚焦 commits）
- [ ] 7.6 更新 `package.json` 描述（如有变更）