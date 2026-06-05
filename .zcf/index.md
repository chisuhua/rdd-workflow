# .zcf/ State Files Index

本目录包含 spec-workflow 状态机使用的状态文件。本索引说明每个文件的角色、写入者和读取者。

## 状态文件清单

### `.roadmap-state.json`
- **角色**: 存储项目 roadmap 的当前阶段、阶段门控状态、各阶段包含的 changes
- **写入者**: `roadmap.md` (init/edit/advance/validate), `execute.md` (Roadmap 进度自动更新)
- **读取者**: `guide-spec.md` Phase 1.5 (展示当前阶段), `propose.md` Phase -1 (读取 ROADMAP_MODE)
- **格式**: JSON, 由 roadmap.md 维护
- **Git 跟踪**: 否 (.gitignore 忽略)

### `.deps-candidates.json`
- **角色**: 存储需要做依赖分析的 change 候选列表
- **写入者**: `guide-spec.md` Phase 2.5 Step 1
- **读取者**: `deps.md` Step 0
- **格式**: JSON, `{"candidates": [...]}`
- **Git 跟踪**: 否

### `.deps-output.md`
- **角色**: deps 依赖分析的输出报告,包含依赖图、状态表、推荐顺序、冲突警告、AI 建议
- **写入者**: `deps.md` Step 5
- **读取者**: `guide-spec.md` Phase 2.5 Step 3 (cat 显示给用户)
- **格式**: Markdown, 5 章节 (依赖图 / 状态表 / 推荐顺序 / 冲突警告 / AI 建议)
- **Git 跟踪**: 否

### `.phase-gate-report.md`
- **角色**: 阶段门控报告,说明当前 phase 是否满足进入下一 phase 的条件
- **写入者**: `roadmap.md` (gate-report 命令)
- **读取者**: 用户 (手动 review), `roadmap.md` (advance 命令)
- **格式**: Markdown
- **Git 跟踪**: 否

### `.handoff.json`
- **角色**: 记录 spec 端到 ship 端的交接状态（spec→ship handoff）
- **写入者**: `guide-spec.md` Phase 3 (spec-done exit, 写入 spec_complete_at + current_change)
- **读取者**: `guide-ship.md` Phase 1 (entry, 回填 ship_started_at)
- **格式**: JSON, `{spec_complete_at, ship_started_at, current_change}`
- **Git 跟踪**: 否 (.zcf/* 已被 .gitignore 排除)

## 生命周期

- `.zcf/` 在项目第一次执行 roadmap init 时创建
- 各状态文件在对应阶段首次进入时创建
- 文件由各自维护者持续更新,无版本控制
- 项目归档时,这些文件可保留作历史记录

## 一致性保证

- 各文件独立维护,无强一致性约束
- 状态迁移出错时,以 `.zcf/.phase-gate-report.md` 为权威报告
- 删除 `.zcf/` 不会破坏工作流(会自动重新生成)
