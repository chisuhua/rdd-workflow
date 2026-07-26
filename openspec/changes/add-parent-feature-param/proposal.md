## Why

`iteration_schema.json` 中 `parent_feature` 字段已定义 (L99-102) 但从未被任何代码写入 — 是 dead field。当前所有 7 个 changes 全在 `__ungrouped__` 组，因为没有 `feature-` 前缀也没有 `parent_feature` 设置。

Oracle 架构分析 2026-07-21 结论：激活 `parent_feature` 字段即可让 change 归入 feature 组，无需新增 feature 状态机。与 ADR-0016 "extend not replace" 原则一致 — 扩展已有字段而非新建结构。Schema 零变更，只需修复写入端。

## What Changes

- **Add** `--parent-feature` CLI argument to `propose_change.sh` bash wrapper (currently only reads `PARENT_FEATURE` env var)
- **Add** `--parent-feature` argument to `propose_create_change` and `propose_finalize_change` bash functions
- **Add** Phase 3 interactive menu: optional "归属 feature" input when user selects a propose
- **Add** rejection of `parent_feature=__ungrouped__` (reserved synthetic key)
- **Add** unit tests: 4 cases covering `--parent-feature` flow, rejection, env-var fallback, backward compatibility
- **Add** bats integration tests: 2 cases covering CLI parsing and iteration.json output

## Capabilities

### New Capabilities
- `parent-feature-param`: CLI `--parent-feature <name>` parameter on `propose_create_change` and `propose_finalize_change`, enabling explicit feature grouping without requiring `feature-` name prefix convention

### Modified Capabilities
- `propose`: The Phase 3 interactive menu now offers optional "归属 feature" input; the bash wrapper now accepts `--parent-feature` argument

## Impact

- **New code**: ~40 lines (bash arg parsing in propose_change.sh) + ~20 lines (propose.md Phase 3 menu) + ~80 lines (tests) = ~140 lines
- **Dependencies**: None (uses existing Python backend that already supports `parent_feature`)
- **Compatibility**: 100% backward compatible — omitting `--parent-feature` preserves existing behavior
- **Risk**: Low — additive change; Python backend already handles `parent_feature` parameter
- **Source**: Oracle 架构分析 2026-07-21, improvement `add-parent-feature-param`