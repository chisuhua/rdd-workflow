## 1. Schema 与状态基础设施

- [ ] 1.1 修改 `skills/_lib/schemas/iteration_schema.json`：status enum 添加 `"planned"`，bump version 到 3
- [ ] 1.2 修改 `skills/_lib/iteration.py`：`create_empty()` 和 `add_or_update_change()` 支持 `planned` status；新增 `get_unblocked_planned(project_root)` 函数（返回 blocker 已全部 archived 的 planned change 列表）
- [ ] 1.3 修改 `skills/_lib/schemas/deps_analysis_schema.json`：change 对象新增 `skeleton: boolean` 字段（默认 false）
- [ ] 1.4 更新 `tests/unit/test_iteration.py`：新增 planned status 的单元测试（schema 验证 + 状态转换 + get_unblocked_planned）
- [ ] 1.5 更新 `tests/unit/test_deps_output.py` 和 `tests/unit/test_roadmap_sprint.py`（若有对 status enum 的引用）

## 2. Propose 骨架模式

- [ ] 2.1 修改 `skills/propose.md` Phase 4：新增 `--skeleton` 分支——仅执行 `openspec new change` + 写入 `roadmap-meta.yaml` + 写入最小 `proposal.md`（Why + What Changes 章节），跳过 design.md/tasks.md
- [ ] 2.2 修改 `skills/propose.md` Phase 5 提交逻辑：骨架 change 仅提交 `.openspec.yaml` + `roadmap-meta.yaml` + `proposal.md`
- [ ] 2.3 修改 `skills/propose.md` Phase 0 清理逻辑：`skeleton` 状态的条目保留在 proposal-suggestions.md 中（不删除），仅删除 `已完成` 条目
- [ ] 2.4 更新 `tests/integration/` 新增骨架创建测试（bats: test_propose_skeleton.bats）

## 3. Guide-Plan Fill 阶段

- [ ] 3.1 修改 `skills/guide-plan.md` Phase 2 菜单：新增选项「3. 填充骨架 change (fill)」
- [ ] 3.2 新增 `skills/guide-plan.md` Phase 2.5 fill 阶段内容：
  - 展示 `planned` 状态 change 列表，按 deps 推荐顺序排序（blocker 已清除的优先）
  - 用户选择后，读取 `proposal-suggestions.md` 获取原始 `description`
  - 串行调用 `openspec instructions design/tasks` 填充 artifacts
  - 成功后更新 `iteration.json` status 为 `proposed`，`proposal-suggestions.md` status 为 `已完成`
- [ ] 3.3 修改 `skills/guide-plan.md` Phase 4 plan-done 门控：
  - 新增混合状态路径：`planned=N, proposed=M` 且 `M ≥ 1` → 通过
  - 仅 `planned` 无 `proposed` → 失败
- [ ] 3.4 更新 `tests/integration/test_guide_plan_fill.bats`（fill 阶段集成测试）

## 4. Deps 骨架容错

- [ ] 4.1 修改 `skills/deps.md` Step 1：读取 change artifacts 时容错——design.md/tasks.md 不存在时跳过对应提取，不报错
- [ ] 4.2 修改 `skills/deps.md` Step 2 轴 3（接口依赖）：对无 design.md 的 change 跳过接口检测，输出标注 `skeleton: true`
- [ ] 4.3 修改 `skills/deps.md` Step 5 输出：骨架 change 在 Mermaid 图中用虚线边框标记；Change 状态表新增 `Skeleton` 列
- [ ] 4.4 修改 `skills/deps.md` Step 6（同步 iteration.json）：骨架 change 的 deps 信息正确写入（blocker/parallel_group/conflicts + `skeleton: true`）
- [ ] 4.5 更新 `tests/integration/test_deps_skeleton.bats`（骨架 deps 容错测试）

## 5. Guide-Ship Archive 后触发

- [ ] 5.1 修改 `skills/guide-ship.md` Phase 3 archive 完成后：调用 `iteration.get_unblocked_planned()` 扫描因本次归档而解除阻塞的 planned change
- [ ] 5.2 若有候选：输出建议信息（change 列表 + 提示运行 guide-plan fill）
- [ ] 5.3 若无候选：不输出额外信息（保持现有行为）
- [ ] 5.4 更新 `tests/integration/test_guide_ship_archive_hook.bats`（archive 后 fill 建议测试）

## 6. Status 模式适配

- [ ] 6.1 修改 `skills/status.md` Mode A（全局概览）：表格新增 `planned` 状态列
- [ ] 6.2 修改 `skills/status.md` Mode E（当前迭代）：显示 `planned` 变化为独立分组（图标 📋），展示 blocker/progress
- [ ] 6.3 更新 `tests/integration/test_status_planned.bats`

## 7. ADR 与文档

- [ ] 7.1 创建 `docs/adr/ADR-0013-incremental-skeleton-planning.md`：记录骨架规划的设计决策（Decision 1-6）
- [ ] 7.2 更新 `skills/guide.md`（推荐器）：识别 `planned` 状态变化，推荐 fill 操作
- [ ] 7.3 更新 `AGENTS.md` 或相关文档提及新工作流模式