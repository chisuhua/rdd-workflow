# auto-sync-adr-index

**优先级**: P2 | **来源**: 改进分析报告 #7
**阶段**: default | **分类**: maintenance
**类型**: test-only

## 架构依据
（无）

## 范围
- In Scope:
  - scripts/sync_adr_index.py 自动生成 README.md 表格
  - CI hook 或 pre-commit hook 自动调用
- Out Scope:
  - 不修改 ADR 模板或格式

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 新增 ADR 后 README.md 自动更新
