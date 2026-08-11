# filter-guide-ship-when-no-changes

**优先级**: P2 | **来源**: Session 复盘 2026-07-26 — guide-ship 空转
**阶段**: v2.1 | **分类**: planning
**类型**: improvement

## 架构依据
- Session 复盘：用户从 guide 菜单选择 `guide-ship`，立即发现 `openspec/changes/` 无活跃 change（仅 `archive/`），被迫返回。
- 根因：`workflow_synthesizer.py` / `scan-state.sh` 的 `all_options` 无条件包含 `guide-ship`（`group: "stages"`），不验证入口条件。
- `guide-ship` 的实际入口条件是：至少有一个已提交的非归档 change。
- 当 `FS_ACTIVE_COUNT == 0` 时提供 guide-ship 选项，导致无意义的用户旅程。

## 范围
- **In Scope**:
  - `workflow_synthesizer.py` 的 `all_options` 生成逻辑新增条件过滤：当 `FS_ACTIVE_COUNT == 0` 时排除 `guide-ship`
  - 或在 description 中标注 `"(当前无活跃 change)"`，`group` 降级为 `disabled`
  - `scan_state()` 的 13-path 决策树中，path 4 的推荐改为 `guide-arch`（当前已是）而不是 `guide-ship`
- **Out Scope**:
  - 不修改 `guide-ship` 自身的入口检测逻辑（那是防御性编程，保留）
  - 不影响 `guide-arch` / `guide-plan` 的过滤

## 关键场景
- GIVEN `openspec/changes/` 只有 `archive/`，WHEN `guide_entry` 执行并生成 `all_options`，THEN `guide-ship` 不在选项中
- GIVEN `openspec/changes/` 有 1 个非归档 change，WHEN `guide_entry` 执行，THEN `guide-ship` 正常出现（`group: "stages"`，可选的）

## 技术约束
- MUST 保持阶段命令按实际可用性动态过滤
- MUST 与其他 `all_options` 过滤逻辑一致（如果后续有其他类似条件过滤的需求）

## 验收标准
- 无活跃 change 时 `guide_entry` 的 `all_options` 不包含 `guide-ship`
- 有活跃 change 时 `guide-ship` 正常出现
- 已有 bats 测试通过