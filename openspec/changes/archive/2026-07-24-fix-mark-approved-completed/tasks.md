# Tasks: fix-mark-approved-completed

## Implementation Steps

- [ ] 修复 `skills/_lib/state.sh` 中 `mark_approved_completed` 的 `content.replace` 逻辑
  - 使用 `re` 模块定位 `## 已实施` 表头行
  - 在表头 + 分隔行之后插入新行，而非替换整个表头块
- [ ] 增加幂等性检查
  - 插入前搜索 `## 已实施` 表格中是否已包含该提案名
  - 若已存在则直接返回 0（成功），不修改文件
- [ ] 保持调用约定一致
  - 返回值语义：0=成功，1=失败
  - 与 `append_approved` / `list_approved` 的调用约定一致
- [ ] 编写单元测试覆盖 3 个场景
  - 正常路径：条目从 `## 待实施` 移动到 `## 已实施`，无重复表头
  - 重复调用幂等：条目已在 `## 已实施`，再次调用返回成功且不修改文件
  - 已实施条目跳过：检测到条目已存在时跳过插入

## Verification (验收标准)

- [ ] `mark_approved_completed` 不产生重复表头
- [ ] 幂等调用返回 success 且不修改文件
- [ ] 3 个单元测试通过

## Key Scenarios (关键场景)

- [ ] GIVEN approved.md 有 `## 已实施` 表头, WHEN mark_approved_completed 执行, THEN 新行插入在表头下方而非重复表头
- [ ] GIVEN 条目已在 `## 已实施` 表格, WHEN 再次调用 mark_approved_completed, THEN 幂等返回 success
