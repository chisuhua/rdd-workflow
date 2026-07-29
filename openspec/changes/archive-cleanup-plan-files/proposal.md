# Archive cleanup plan files — remove orphaned .rddf/plans/<name>.md

**优先级**: P2
**阶段**: v2.2
**分类**: core
**类型**: bugfix

## 概要

归档流程（archive）没有清理 `.rddf/plans/<name>.md` 计划文件，导致孤立计划文件累积。应在 archive 完成后自动删除对应的计划文件，并在 scan-state.sh 中添加孤立文件检测。

## 背景

- PTX-EMU add-cudart-unit-tests 归档后复盘发现 `.rddf/plans/add-cudart-unit-tests.md` 变为孤立文件
- 还发现 2 个类似孤立计划文件（`fix-commented-ptx-tests.md`、`fix-named-barrier-slots.md`），其对应 change 早已归档
- archive 流程（`ship_archive.sh` / `archive.sh`）没有清理 `.rddf/plans/<name>.md` 的步骤
- 孤立计划文件会给 scan-state.sh 扫描带来噪音，且占用 `.rddf/` 空间
- v2.0 自包含的 `rdd-workflow-writing-plans` 生成 `.rddf/plans/<name>.md`，但 archive 时未处理删除

## 范围

### In Scope

- `ship_archive.sh::archive_change_for_mode()` 中归档完成后添加计划文件清理步骤：检测 `.rddf/plans/<change_name>.md` 存在则删除
- `scan-state.sh` 中增加孤立计划文件检测：扫描 `.rddf/plans/` 中所有文件，检查其对应的 change 是否已归档
- 孤立文件检测输出为 warning 级别（不阻塞流程）
- guide 入口扫描时展示孤立计划文件数量

### Out Scope

- 不清理 `.rddf/plans/` 之外的文件
- 不修改 `.rddf/plans/` 目录结构或文件命名规则
- 不涉及 `.rddf/state/` 下的文件
- 不修改 `archive.sh::archive_change()`（worktree 模式已通过 `ship_archive.sh` 统一 funnel）

## 关键场景

- GIVEN change 归档完成, WHEN `archive_change_for_mode` 执行, THEN 自动删除 `.rddf/plans/<name>.md`
- GIVEN `.rddf/plans/` 中存在孤立文件, WHEN scan-state 运行, THEN warning 输出包含文件名和计数
- GIVEN `.rddf/plans/<name>.md` 不存在, WHEN archive 完成, THEN 跳过删除（幂等）
- GIVEN guide 入口扫描, WHEN 发现孤立计划文件, THEN 在菜单中展示清理建议

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | archive 完成后 `.rddf/plans/<name>.md` 自动删除 | bats：创建 plan 文件 → 执行 archive → 断言文件不存在 |
| 2 | scan-state.sh 检测到孤立计划文件时输出 warning | bats：创建孤立 plan 文件 → 运行 scan → 捕获 warning 输出 |
| 3 | 无孤立文件时 scan-state.sh 不输出 warning | bats：清理所有 plan 文件 → 运行 scan → 无 warning |
| 4 | 删除操作幂等（文件不存在时跳过） | bats：删除不存在的 plan 文件 → 无错误 |