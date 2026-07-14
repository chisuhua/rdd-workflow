# .rddf/state/ — State Files Index

本目录包含 spec-workflow 状态机使用的状态文件。本索引说明每个文件的角色、写入者和读取者。

## 状态文件清单

### `roadmap-state.json`
- **角色**: 存储项目 roadmap 的当前阶段、阶段门控状态、各阶段包含的 changes
- **写入者**: `roadmap.md` (init/edit/advance/validate), `execute.md` (Roadmap 进度自动更新)
- **读取者**: `guide-arch.md` Phase 1.5 (展示当前阶段), `propose.md` Phase -1 (读取 ROADMAP_MODE)
- **格式**: JSON, 由 roadmap.md 维护
- **Git 跟踪**: 否 (.gitignore 忽略)

### `deps-candidates.json`
- **角色**: 存储需要做依赖分析的 change 候选列表
- **写入者**: `guide-plan.md` deps 阶段 Step 1
- **读取者**: `deps.md` Step 0
- **格式**: JSON, `{"candidates": [...]}`
- **Git 跟踪**: 否

### `deps-output.md`
- **角色**: deps 依赖分析的输出报告,包含依赖图、状态表、推荐顺序、冲突警告、AI 建议
- **写入者**: `deps.md` Step 5
- **读取者**: `guide-plan.md` deps 阶段 Step 3 (cat 显示给用户)
- **格式**: Markdown, 5 章节 (依赖图 / 状态表 / 推荐顺序 / 冲突警告 / AI 建议)
- **Git 跟踪**: 否

### `deps-ai-result.json`
- **角色**: subagent 语义分析的输出 (Step 3 成功路径), 包含 AI 识别的隐式依赖 + 重组建议
- **写入者**: `deps.md` Step 3 (3e/3e+) — 由 subagent 调用写入
- **读取者**: `deps.md` Step 5 (5a/5e) — 解析后渲染到 `deps-output.md` 的 AI 章节
- **格式**: JSON, `{ai_deps: [...], suggestions: [...], fallback: bool}`
- **Git 跟踪**: 否
- **关系**: 缺失或 `fallback: true` 时, Step 5 写入 `AI 语义分析未启用 (fallback)` 标记

### `phase-gate-report.md` (REMOVED in v2.0.3)
- **状态**: 已移除 (fix-debt-audit-2026-07-14)
- **移除原因**: writer (roadmap.md) 写 `phase-gate-report.md` (无点),reader (scan-state.sh) 读 `.phase-gate-report.md` (有点) — 文件名 dot mismatch 导致机制从未工作,判定为死代码
- **历史**: 由 T12 (P1-3) 连接到 `guide.md` 推荐逻辑, T33 加 regression test;v2.0.3 整体删除
- **Git 跟踪**: 否

### `handoff.json`
- **角色**: 记录 plan 端到 ship 端的交接状态（plan→ship handoff）
- **写入者**: `guide-plan.md` plan-done exit (写入 plan_complete_at + current_change)
- **读取者**: `guide-ship.md` Phase 1 (entry, 回填 ship_started_at)
- **格式**: JSON, `{plan_complete_at, ship_started_at, current_change}`
- **Git 跟踪**: 否

## 生命周期

- `.rddf/state/` 目录在项目执行 state 相关命令时自动创建
- 各状态文件在对应阶段首次进入时创建
- 文件由各自维护者持续更新,无版本控制
- 项目归档时,这些文件可保留作历史记录

## 一致性保证

- 各文件独立维护,无强一致性约束
- 删除 `.rddf/state/` 不会破坏工作流(会自动重新生成)

## 相关目录

| 目录 | 用途 | Git 跟踪 |
|------|------|---------|
| `.rddf/state/` | 运行时状态文件 | 否 (gitignored) |
| `.rddf/wt/` | git worktree 工作目录 | 否 (gitignored) |
| `.rddf/plans/` | 执行计划文件 | 是 |