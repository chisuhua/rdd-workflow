## Context

ADR-0017 定义 rddf-session 数据模型，要求每个 workflow stage 创建/绑定/关闭 rddf-session。会话复盘 2026-07-31 发现 `guide-design` / `guide-plan` / `guide-ship` 全流程执行中 session hook 从未触发——因为 `rddf_session_hooks.sh` 依赖的 `resolve_rdd_skill_dir`（来自 `skill_root.sh`）在当前环境中未被 source。残留 3 个 orphaned session（`rds_0569`, `rds_1221`, `rds_a1b5`）。

## Goals / Non-Goals

**Goals:**
- 3 个 guide skill（design/plan/ship）的入口（Phase 1）与出口（Phase 5/4）可靠触发 `rddf_session_hook_entry` / `rddf_session_hook_close`
- hook 调用前置 source `skill_root.sh`，带 fallback 查找路径（`~/.agents/skills/_lib/skill_root.sh` → `.opencode/skills/_lib/skill_root.sh`）
- `skill_root.sh` 缺失或 `resolve_rdd_skill_dir` 失败时优雅降级：打印 warning，不阻塞工作流

**Non-Goals:**
- 不修改 `rddf_session_hooks.sh` / `skill_root.sh` 本身
- 不修改 `guide` 推荐器
- 不涉及 sessions.json schema 变更

## Decisions

1. **前置 source 模式**：在每个 guide skill 的入口/出口 hook 调用前，添加 skill_root.sh 的 fallback source 逻辑。与现有模式一致（`source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"`）。
2. **优雅降级**：`resolve_rdd_skill_dir` 失败时打印 warning 并跳过 hook（`|| echo "⚠️ ..."`），不 `exit 1`，保证工作流继续。
3. **成功可见性**：hook 成功时输出 session ID 供用户确认（hook 自身已输出，无需额外包装）。

## Risks / Trade-offs

- **重复 source**：每次 guide skill 调用都 source skill_root.sh，幂等无副作用（纯函数定义）。
- **降级风险**：skill_root.sh 不可用时 session 生命周期不被追踪，但工作流不中断——与 ADR-0017 的"不阻塞"原则一致。
- **低风险**：改动限于 3 个 SKILL.md 的入口/出口代码块，不改变阶段状态机逻辑。
