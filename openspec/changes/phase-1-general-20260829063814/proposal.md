# phase-1-general-20260829063814

## Why

`ADR-0030` (Hub-Spoke federation) + `ADR-0032` (hub deepening) 已建立 contract sync通道,但 propose阶段 (`skills/propose/`) 仍需手工调用 `cross-repo-protocol` 工具。**Why now**: feat-fix-archive-gaps-v2 涉及跨仓审计,需 propose 阶段自动识别 Hub 边界。

## What Changes

**In Scope**:

- **Out Scope**: 全自动 Hub RFC 提交(留待 #7);Spoke 端合约编辑

### 关键场景

- GIVEN 用户在 propose阶段创建 change涉及 `openspec/specs/api-*/spec.md`
  WHEN guide-plan 调用 propose_phase
  THEN contract-check 自动 run,RFC 草稿含 Hub issue 占位符

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: 仅 MCP 工具调用,fallback REST (per cross-repo-protocol v1.2+)
- SHOULD: trace 日志写入 `.rddf/state/.cross-repo-deps-cache.json`

## Impact

- MUST NOT: 在 propose阶段直接 file Hub issue (等审批后由 #7 负责)

## Acceptance

- 3 个测试用例:纯本地提案无 RFC 占位 / 跨仓提案含占位 / 跨仓提案缓存命中跳过重新生成
- 端到端: propose → design → plan 全程0 手工 cross-repo 调用

