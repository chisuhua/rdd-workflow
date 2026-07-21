# skill-name-auto-resolve

**Priority**: P2
**Phase**: v2.1
**Status**: proposed

## Why

## 架构依据
- 复盘发现：第一轮 8 个 task() 全部因 `load_skills=["spec-workflow/writing-plans"]` 失败
- 根因：skill 名缺少 `rdd-workflow/skills/` 前缀，无自动补全机制

## 范围
- **In Scope**:
  - 在 task() 调用前增加 skill 名校验步骤：从 available list 中搜索匹配
  - 短名匹配逻辑：`spec-workflow/writing-plans` → 自动补全为 `rdd-workflow/skills/spec-workflow/writing-plans`
  - 歧义时报错（多个匹配），无匹配时提示候选项
  - 1 个 bats 测试：短名 → 全名映射、歧义场景、无匹配场景
- **Out Scope**:
  - 不修改 task() 平台实现（适配层）

## 验收标准
- `resolve-skill-name spec-workflow/writing-plans` 输出全名
- 1 个 bats 测试通过
