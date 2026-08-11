# fix-rddf-session-lifecycle-binding

**优先级**: P1 | **来源**: 会话复盘 2026-07-31 — 4 阶段工作流执行中缺少 session 生命周期管理
**阶段**: default | **分类**: core-impl
**类型**: fix

## 架构依据

- ADR-0017: rddf-session 数据模型，要求每个 workflow stage 创建/绑定/关闭 rddf-session
- 会话复盘 2026-07-31: guide → design → plan → ship 全流程执行中，`rddf_session_hook_entry` / `rddf_session_hook_close` 从未被触发
- 根因：`rddf_session_hooks.sh` 依赖 `resolve_rdd_skill_dir` 函数（来自 `skill_root.sh`），但在当前会话环境中 `skill_root.sh` 未被 source 或不可用
- 后果：3 个 orphaned session 残留（`rds_0569`, `rds_1221`, `rds_a1b5`），本次工作流没有被追踪，跨 session 恢复不可用

## 范围

- **In Scope**:
  - `skills/guide-design/SKILL.md` Phase 1: 确保 `rddf_session_hook_entry` 调用前 source `skill_root.sh`
  - `skills/guide-plan/SKILL.md` Phase 1: 同上
  - `skills/guide-ship/SKILL.md` Phase 1: 同上
  - `skills/guide-design/SKILL.md` Phase 5: 确保 `rddf_session_hook_close` 调用前 source `skill_root.sh`
  - `skills/guide-plan/SKILL.md` Phase 4: 同上
  - `skills/guide-ship/SKILL.md` Phase 5: 同上
  - 若 `skill_root.sh` 不存在则优雅降级（打印 warning 而非 crash）
- **Out Scope**:
  - 不修改 `rddf_session_hooks.sh` 本身
  - 不修改 `skill_root.sh` 本身
  - 不修改 `guide` 推荐器（无状态只读）

## 关键场景

- GIVEN 用户调用 `skill_use("guide-design")`, WHEN Phase 1 执行, THEN `rddf_session_hook_entry stage_design` 被调用, 创建 stage_design session
- GIVEN design-done 门控通过, WHEN Phase 5 执行, THEN `rddf_session_hook_close stage_design` 被调用, 标记 session completed
- GIVEN `skill_root.sh` 不存在或 `resolve_rdd_skill_dir` 失败, WHEN session hook 执行, THEN 打印 warning 并继续, 不阻塞工作流

## 技术约束

- MUST 在 3 个 guide skill 的入口和出口各添加 `source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"` 调用
- MUST 在 source 前添加 `skill_root.sh` 的 fallback 查找逻辑（`~/.agents/skills/_lib/skill_root.sh` → `.opencode/skills/_lib/skill_root.sh`）
- MUST NOT 在 session hook 失败时阻塞工作流（graceful degradation）
- SHOULD 在 session hook 成功时输出 session ID 供用户确认

## 验收标准

- `skill_use("guide-design")` 执行后 `.rddf/state/sessions.json` 中出现 `kind=stage_design` 的 session
- `skill_use("guide-plan")` 执行后 `sessions.json` 中出现 `kind=stage_plan` 且 parent 指向 stage_design
- session hook 失败时 guide skill 正常继续执行，不崩溃
- 现有 `pytest tests/unit/` 测试全部通过