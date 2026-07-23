## Context

- fix-attach-detach-symmetry 补齐了 rddf_session_hook_attach
- 初始设计时 attach/detach 不对称

## Goals / Non-Goals

**Goals:**

- - 
  - 在 ADR 或设计文档中明确 hook 对称性要求
  - 添加测试自动验证 hook 成对存在
- Out Scope:
  - 不修改现有 hook 实现

## 验收标准
- 新增 hook 必须成对（attach/detach）

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 30min
