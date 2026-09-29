---
优先级: P3
来源: 2026-09-29 fix-roadmap-phase-objective-parser 修复后续 (update_objectives_sentinel 已就位但需手动触发)
阶段: phase-2
分类: governance
类型: improvement
主题: Roadmap 自动刷新 hook（git post-commit 触发 sentinel 更新）
---
**优先级**: P3 | **来源**: 2026-09-29 fix-roadmap-phase-objective-parser 修复后续
**阶段**: phase-2 | **分类**: governance | **类型**: improvement

**主题**: Roadmap 自动刷新 hook（git post-commit 触发 sentinel 更新）

## 架构依据

`commit 67a3e85` 引入 `_lib/roadmap_state.py::update_objectives_sentinel()` 后，AGENTS.md 的 `<!-- AUTO: objectives start -->` 哨兵段刷新路径完整可用。**当前唯一调用方是 `planner_stage_exit.sh`** — 即用户在 rdd-planner P3 阶段退出时才会触发。

后果:
- 开发者直接编辑 `.rddf/roadmap/objectives/objective-xxx.md` 后，AGENTS.md 不会自动更新（除非跑 `planner_stage_exit.sh`）
- `update_agent_md`（feature fragments 哨兵）同理 — 当前需手动 `rddf roadmap --update-agent-md`
- rdd-doctor 检测 AGENTS.md drift 是只读警告，不自动修复

期望行为: git post-commit hook 在 `.rddf/roadmap/{objectives,features}/*.md` 变更时自动触发对应 sentinel 刷新。

## 范围

### In Scope
- `.git/hooks/post-commit` 或 hooks installer（推荐后者，便于分发到外部项目）
- 触发条件: `git diff --name-only HEAD~1 HEAD | grep -E '\.rddf/roadmap/(objectives|features)/.*\.md$'`
- 调用: `python3 -c "from _lib.roadmap_state import update_objectives_sentinel, update_agent_md; update_objectives_sentinel('.'); update_agent_md('.')"`
- 幂等 + 快速 (< 100ms)
- 可选: `--check-only` 模式（不写文件，只报告 drift）

### Out of Scope
- pre-commit hook（修改 staging 文件语义复杂，留 v5+）
- `.rddf/roadmap/phases/*.md` 的自动刷新（phases 由 `populate` 流程管理，不是手工编辑）
- 强制 hook（用户应能 opt-out via `--no-verify`）

### Deferral 理由

v4.x 当前优先级低的原因:
1. sentinel 刷新已经可以通过 `planner_stage_exit.sh` + `rddf roadmap --update-agent-md` 手动触发
2. rdd-doctor 已经检测 drift（`rdd-doctor --category roadmap-feature`）
3. hook 安装 + 分发（跨 external project）需要 hooks installer 重构

v5 重新评估触发条件:
- 用户报告 ≥ 3 次 "AGENTS.md stale" 问题
- 或 rdd-doctor 检测到 drift 自动修复（不再只读）

## Acceptance

- [ ] hook installer (`bash skills/INSTALL.md` 集成) 支持 `--with-git-hooks` flag
- [ ] post-commit hook 存在且可执行 (mode 0755)
- [ ] hook 检测到 `.rddf/roadmap/{objectives,features}/*.md` 变更时自动调用 sentinel 刷新
- [ ] 无变更时 (diff 为空) hook exit 0 且 < 100ms
- [ ] `rdd roadmap --update-agent-md` + `update_objectives_sentinel` 单文件路径时同步刷新
- [ ] 集成测试: `tests/integration/test_git_hooks.bats` 覆盖正常/空 diff/opt-out 三场景

## 参考

- `commit 67a3e85` — `update_objectives_sentinel` 引入
- `_lib/roadmap_state.py:1077-1174` — `update_agent_md` 已就位
- `_lib/roadmap_state.py:1180-1260` — `update_objectives_sentinel` 已就位
- `tests/integration/test_planner_stage_graceful_degradation.bats` — graceful degradation 契约已锁

## 关联 follow-up

- `phase-4.md` near-duplicate themes (commit 67a3e85 msg 标记) — 人工 review 后手动合并
- L7 `arch_roadmap_menu.sh` 重命名/合并到 `_case_handler.sh`（如果未来菜单统一重构）
