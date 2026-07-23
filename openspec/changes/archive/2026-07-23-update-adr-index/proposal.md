## Why

ADR 索引表 (`docs/adr/README.md`) 目前只列出到 ADR-0020，但代码库实际已有 ADR-0021 (ADR-0022 manual_deps 字段) 和 ADR-0022 (未编号)。这导致：
- 索引表与仓库实际 ADR 文件不一致，新成员无法通过索引了解全部 ADR
- `test_adr_index.bats` 因此一直失败（pre-existing failure #1）

## What Changes

- 更新 `docs/adr/README.md` 索引表，追加 ADR-0021、ADR-0022 行
- 保持表格格式与现有行一致
- 仅修改 README.md，不修改 ADR 文件本身

## Capabilities

### New Capabilities

无 — 纯文档更新，不引入新能力。

### Modified Capabilities

无 — 不修改任何 spec 要求。

## Impact

- **Affected files**: `docs/adr/README.md` 仅此一处
- **无** API 变更、无依赖变更、无代码修改
- 修复后 `test_adr_index.bats` 中 ADR 文件检查应通过