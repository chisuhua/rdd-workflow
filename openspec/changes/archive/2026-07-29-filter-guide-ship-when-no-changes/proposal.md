# Filter guide-ship when no active changes

**优先级**: P2  
**阶段**: v2.1  
**分类**: planning

## 概要

当 `openspec/changes/` 下没有活跃 change（仅 `archive/` 目录）时，`guide` 菜单不应提供 `guide-ship` 选项，或将其标记为不可用，避免用户选择后进入空转流程。

## 背景

- Session 复盘 2026-07-26 发现：用户从 guide 菜单选择 `guide-ship`，立即发现 `openspec/changes/` 无活跃 change（仅 `archive/`），被迫返回。
- 根本原因：`workflow_synthesizer.py` / `scan-state.sh` 的 `all_options` 无条件包含 `guide-ship`（`group: "stages"`），不验证入口条件。
- `guide-ship` 的实际入口条件是：至少有一个已提交的非归档 change。
- 当 `FS_ACTIVE_COUNT == 0` 时提供 guide-ship 选项，导致无意义的用户旅程。

## 范围

### In Scope

- `workflow_synthesizer.py` 的 `all_options` 生成逻辑新增条件过滤：当 `FS_ACTIVE_COUNT == 0` 时排除 `guide-ship`
- 或在 description 中标注 `"(当前无活跃 change)"`，`group` 降级为 `disabled`
- `scan_state()` 的 13-path 决策树中，path 7+ 的推荐不再包含 `guide-ship`

### Out Scope

- 不修改 `guide-ship` 自身的入口检测逻辑（那是防御性编程，保留）
- 不影响 `guide-arch` / `guide-plan` 的过滤

## 验收标准

- 无活跃 change 时 `guide_entry` 的 `all_options` 不包含 `guide-ship`
- 有活跃 change 时 `guide-ship` 正常出现
- 已有 bats 测试通过