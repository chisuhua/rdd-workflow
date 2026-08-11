# update-adr-index

**优先级**: P2 | **来源**: 复盘遗留 — ADR 索引表与 README 不同步
**阶段**: v2.1 | **分类**: docs
**类型**: test-only

## 架构依据
- 执行中发现 docs/adr/README.md 索引表只更新到 ADR-0020，但代码库已有 ADR-0021、ADR-0022。
- test_adr_index.bats 因此一直失败（pre-existing failure #1）。

## 范围
- **In Scope**:
  - 更新 docs/adr/README.md 索引表追加 ADR-0021、ADR-0022 行
  - 保持表格格式一致
- **Out Scope**:
  - 不修改 bats 测试（预存在失败会自然解决）
  - 不修改 ADR 文件本身

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- README.md 的 ADR 索引表包含 ADR-0021 和 ADR-0022
- README.md 的进度表（v2.0 ADR 实施状态）包含 ADR-0022
- test_adr_index.bats 中 ADR 文件检查通过
