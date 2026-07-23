## Context

`docs/adr/README.md` 包含两个 ADR 索引表：顶部的"v2.0 ADR 实施状态"表和详细的"ADR 列表"表。`test_adr_index.bats` 验证索引表列出的 ADR 文件是否实际存在于 `docs/adr/` 目录。当前 ADR-0021（Phase 2 per-skill helper migration）、ADR-0022（manual_deps 字段）和 ADR-0023（v3.0.0 包名重命名）已存在，但索引表未同步更新，导致 bats 测试失败。

## Goals / Non-Goals

**Goals:**
- 同步"ADR 列表"索引表，追加 ADR-0021、ADR-0022、ADR-0023 行
- 恢复 `test_adr_index.bats` 的通过状态

**Non-Goals:**
- 不修改任何 ADR `.md` 文件内容
- 不修改 `test_adr_index.bats` 测试逻辑
- 不改动"v2.0 ADR 实施状态"表（该表为人工维护的状态快照，非必填字段）

## Decisions

- **手动补全表格行**：`README.md` 的索引表为纯手工维护的 Markdown，采用与现有行一致的格式追加 3 行
- **仅补"ADR 列表"表**：该表是 bats 测试的验证目标（测试检查 `docs/adr/` 文件与索引表条目的一致性），顶部的"实施状态"表不在测试范围内
- **不自动生成**：索引表不含自动化生成工具，手工维护的成本在此次修改中可接受

## Risks / Trade-offs

- **低风险**：纯文档更新，不涉及代码逻辑变更
- **手工维护的持续成本**：索引表依赖人工同步，后续新增 ADR 时可能再次落后。可考虑未来引入自动化脚本，但不在本次范围