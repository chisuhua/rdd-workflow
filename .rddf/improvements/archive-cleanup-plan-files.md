# archive-cleanup-plan-files

**优先级**: P2 | **来源**: PTX-EMU add-cudart-unit-tests archive 复盘 2026-07-24
**阶段**: v2.2 | **分类**: core
**类型**: bugfix

## 架构依据
- 复盘发现：`add-cudart-unit-tests` 归档后 `.rddf/plans/add-cudart-unit-tests.md` 变成孤立文件（无对应活跃 change）
- 同时还有 2 个类似孤立计划文件（`fix-commented-ptx-tests.md`、`fix-named-barrier-slots.md`），其对应 change 早已归档
- archive 流程没有清理 `.rddf/plans/<name>.md` 的步骤，导致孤立文件累积
- 孤立计划文件会给未来扫描（如 scan-state.sh）带来噪音，且占用 `.rddf/` 空间

## 范围
- **In Scope**:
  - ship_archive.sh::archive_change() 末尾增加计划文件清理步骤：检测 `.rddf/plans/<change_name>.md` 并删除
  - scan-state.sh 增加孤立计划文件检测：扫描 `.rddf/plans/` 中所有文件，检查其对应的 change 是否已归档
  - 孤立文件检测结果输出为 warning 级别（不阻止流程）
  - guide 入口扫描时展示孤立计划文件数量
- **Out Scope**:
  - 不清理 `.rddf/plans/` 之外的文件
  - 不修改 `.rddf/plans/` 目录结构或文件命名规则
  - 不涉及 `.rddf/state/` 下的文件

## 关键场景
- GIVEN change 归档, WHEN archive 完成, THEN 自动删除 `.rddf/plans/<name>.md`
- GIVEN `.rddf/plans/` 中存在孤立文件, WHEN scan-state 运行, THEN warning 输出并计数
- GIVEN `.rddf/plans/<name>.md` 不存在, WHEN archive 完成, THEN 跳过删除（幂等）
- GIVEN guide 入口扫描, WHEN 发现孤立计划文件, THEN 在菜单中展示清理建议

## 技术约束
- MUST archive 时通过 change 名称精确匹配计划文件，不 glob 遍历全目录（降低误删风险）
- MUST 删除前检查 change 是否已归档（通过 check `openspec/changes/archive/<date>-<name>/` 存在性）
- MUST scan-state.sh 的孤立文件检测为 warning 级别，不阻塞主流程
- SHOULD 提供 `--cleanup-plan-files` 参数让用户手动触发清理所有孤立计划文件

## 验收标准
- archive 完成后 `.rddf/plans/<name>.md` 自动删除
- scan-state.sh 检测到孤立计划文件时输出 warning
- 5 个孤立文件时输出计数正确
- 2 个 bats 测试：archive 自动清理 + scan 检测