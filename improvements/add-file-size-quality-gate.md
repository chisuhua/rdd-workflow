# add-file-size-quality-gate

**优先级**: P2 | **来源**: 改进分析报告 #8
**阶段**: default | **分类**: code-quality
**类型**: feature

## 架构依据
（无）

## 范围
- In Scope:
  - 添加代码质量门控：单文件超过 300 行触发 warning
  - 或在 arch-quality-gate 中添加检查
- Out Scope:
  - 不修改现有代码

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 超过 300 行的文件在 CI 中触发警告
