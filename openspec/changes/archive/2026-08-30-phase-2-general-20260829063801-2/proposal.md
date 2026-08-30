# phase-2-general-20260829063801-2

## Why

`ADR-0011` (phase step pipeline model) + `ADR-0021` (phase2 per-skill helper migration) 已确立 helper 提取规范。Round A (10 个 helper) + Round B (14 个 helper) 共减少 skills/*.md ~1509 行,但 guide-arch / guide-design / guide-plan 仍有内联 bash 块可提取。**Why now**: 持续维护,每内联块都增加 skill 大小和出错风险。

## What Changes

**In Scope**:

- **Out Scope**: 完整 DSL;helper 自动生成

### 关键场景

- GIVEN guide-design Phase 4 design-done 门控脚本 50 行内联
  WHEN提取为 `skills/guide-design/scripts/design_done_gate.sh`
  THEN 9 个边界测试用例锁定 (含正常路径 + 4异常路径 + 4 集成路径)

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: env-var 传递模式 (Oracle C1) — 不内联 `$VAR` 字符串
- SHOULD: helper 模块< 250 行

## Impact

- MUST NOT: helper 之间相互依赖 > 3 层

## Acceptance

- ≥6 个新 helper 提取,行数减少 ≥200 行
- helper 测试覆盖率 ≥90%
- ARCHITECTURE_GATE 通过 (no regression)

