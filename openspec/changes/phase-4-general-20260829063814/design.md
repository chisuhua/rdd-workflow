## Context

本提案实现 roadmap 主题「」。详见 `proposal.md` 的 ## Why 与 ## What Changes 段。

## Goals / Non-Goals

**Goals:**
- 实现 capabilities 段所有 MUST 约束
- 提供对应验收标准的自动化测试覆盖

**Non-Goals:**
- 不修改现有非相关模块 (per Impact MUST NOT 约束)
- 不引入 capabilities/impact 范围外的扩展

## Decisions

### 1. 单职责 helper 提取 vs 内联

**选择**: 单职责 helper 提取到 `skills/_lib/` 或对应 skill 的 `scripts/` 目录。

**理由**: 与 Round A/B 一致 (per ADR-0021);helper < 250 行,测试 1:1 锁定。

**Alternatives considered:**
- 内联实现: 拒绝,因为与 codebase 现有约定不符,且增加 skill 体积

## Risks / Trade-offs

- **Risk**: 9 个 proposal 并行 ship 可能时 出现 file conflict (尤其在 `_lib/` 目录)
- **Mitigation**: deps 阶段会计算 wave,串行化高冲突 proposal

## Capabilities 摘要

- MUST: 回归基线版本控制 (KNOWN_FAILURES.txt 跟随 git)
- SHOULD: 提供 `rddf regression diff` CLI 对比 baseline vs 当前

## Impact 摘要

- MUST NOT: 删除 KNOWN_FAILURES 条目来 "通过" 测试
