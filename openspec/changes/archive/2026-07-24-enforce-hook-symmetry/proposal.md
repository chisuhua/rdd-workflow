## Why

- fix-attach-detach-symmetry 补齐了 rddf_session_hook_attach
- 初始设计时 attach/detach 不对称

## What Changes

- In Scope:
  - 在 ADR 或设计文档中明确 hook 对称性要求
  - 添加测试自动验证 hook 成对存在
- Out Scope:
  - 不修改现有 hook 实现

## Capabilities

### New Capabilities
- `enforce-hook-symmetry`: ## 问题
- fix-attach-detach-symmetry 补齐了 rddf_session_hook_attach
- 初始设计时 attach/detach 不对称

## 范围
- I

## Impact

- **Priority**: P2
- **Effort**: 30min
- **Source**: 改进分析报告 #9
