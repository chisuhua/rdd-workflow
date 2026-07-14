---
SCOPE: shared
STATUS: PROPOSED
---

## Why

ADR-0017 (rddf-session) 已实施并归档（见 `archive/2026-07-09-add-rddf-session/`），提供了 5 个 subcommand（list/show/resume/abandon/archive-history）和 24 单元测试 + 5 集成测试。但**发现层仍不完整**：

1. **没有"我当前绑定在哪个 rddf-session"的查询入口**——用户必须手动 `list` 并用肉眼 grep `owner_opencode_session_id` 列。
2. **没有"我应该 resume 哪个 orphaned session"的推荐**——用户必须手动扫描所有 session、判断哪个处于 orphaned 状态、按 `started_at` 倒序排序选最新。
3. **`guide` 推荐器（无状态扫描器）忽略 sessions.json**——它扫描 `.arch-handoff.json` / `.plan-handoff.json` / worktrees / proposal-suggestions.md，但不读 `.rddf/state/sessions.json`，所以用户即使有活跃绑定也看不到。
4. **mandatory binding 契约只在 guide-arch/plan/ship 入口 hooks 隐式执行**（ADR-0017 Migration Plan P2 已完成），没有文档化的全局政策。

本次 work 直接在 master 实施（轻量模式，无 worktree），新增 2 个 RddfSessionCoordinator 方法 + 1 个 bash 子命令 + 1 个 scan-state.sh 函数 + 1 个 guide.md 集成。**schema 无变更**（`sessions_schema.json` v1 unchanged），**公开 API 无破坏**（仅 additive）。

## What Changes

- **新增 `RddfSessionCoordinator.find_current_binding(owner)`** — 返回该 OpenCode session 拥有的 active rddf-session（按 `started_at` desc 取最新）；无活跃返回 None。
- **新增 `RddfSessionCoordinator.find_next_recommendation(owner=None)`** — 返回最近 started 的 orphaned rddf-session；无 orphan 返回 None。`owner` 参数保留供未来按 owner 过滤。
- **新增 `rddf-session current` 子命令** — 输出当前 binding 或推荐下一个 resume 目标。OPENCODE_SESSION_ID fallback 到 `hostname -s_$$`（沿用 ADR-0017 模式）。
- **新增 `skills/_lib/scan-state.sh` 中 `scan_session_binding()` 函数 + `BINDING_LINES` 全局数组** — 只读扫描 `.rddf/state/sessions.json`，写入 1-2 行 alert。文件缺失/损坏时静默返回（`BINDING_LINES=()` 空数组）。
- **修改 `skills/guide.md`** — 在 `scan_state` 调用之后追加 `scan_session_binding` 调用 + `BINDING_LINES` 打印循环。`RECOMMEND`/`REASON` 不变。
- **修改 `AGENTS.md`** — 新增 `### Session Binding Policy` subsection（关键约定章节内）。
- **修改 `docs/adr/ADR-0017-rddf-session.md`** — 新增 `## Cross-Reference` 段指向本次 spec。

## Capabilities

### New: `rddf-session-binding`

定义 spec 见 `specs/rddf-session-binding/spec.md`：
- `RddfSessionCoordinator.find_current_binding()` / `find_next_recommendation()` 公开方法
- `rddf-session current` 子命令 CLI 表面
- `BINDING_LINES` 在 `scan_state` 之后被 `guide` 推荐器消费
- mandatory binding 契约在 `guide-arch`/`guide-plan`/`guide-ship` 入口强制执行

## Impact

- **依赖**: 仅 `RddfSessionCoordinator`（已有）+ `scan-state.sh` bash 函数（已有）+ `rddf-session.md` skill（已有）
- **向后兼容**: 完全。`sessions_schema.json` v1 不变；`RddfSessionCoordinator` 现有 11 个公开方法签名不变；`scan_state` 11 条优先级不变；5 个现有 rddf-session subcommand 不变。
- **风险**: 低（pure additive，0 schema bump，0 API break）
- **测试**: 10 unit + 18 bats integration（共 28 新增），全部 545 unit + 22 bats regression 全绿

## Spec & Plan Reference

- 设计稿：`docs/superpowers/specs/2026-07-14-rddf-session-binding-design.md`（480 LOC）
- 实施计划：`docs/superpowers/plans/2026-07-14-rddf-session-binding.md`（1121 LOC）
- 跨引用：`docs/adr/ADR-0017-rddf-session.md` § Cross-Reference