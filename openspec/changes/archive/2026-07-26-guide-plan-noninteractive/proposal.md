## Why

`guide-plan` 是当前 OpenSpec 工作流中唯一完全人际交互的状态机 — 它依赖 `Question` 工具弹出菜单、读取用户选择、等待确认。这导致 AI 编排器（如 OpenCode 的自动化工作流）无法调用 guide-plan：每次走到菜单就卡住，需要人工介入。

复盘改进 #1 发现：`propose_change.py` 虽可绕过菜单直接调用，但跳过了完整的 plan 流程（scan → propose → deps → plan-done），无法保证质量门控。

此 change 为 guide-plan 添加 `--non-interactive` 模式及 `--batch-create` 批量 propose 能力，让 AI 编排器可以自动执行完整 plan 流程，同时 100% 向后兼容现有交互体验。

## What Changes

- **Add** `--non-interactive` CLI flag and `SKIP_GUIDE_PLAN_MENU=yes` env var detection to `guide-plan.md` entry point
- **Add** non-interactive mode: skip Phase 3 menu, execute default flow (scan → propose → deps → plan-done) automatically
- **Add** `--batch-create` CLI flag to `propose.md` Phase 4: batch-create skeleton changes for all pending suggestions in `proposal-suggestions.md`
- **Add** bats integration tests: 4 cases covering `SKIP_GUIDE_PLAN_MENU`, `--non-interactive`, `--batch-create`, and backward compatibility
- **Add** unit tests: 2 cases covering `--batch-create` logic in propose_change.py

## Capabilities

### New Capabilities
- `guide-plan-noninteractive`: `SKIP_GUIDE_PLAN_MENU=yes skill_use("guide-plan")` — auto-executes full plan flow without interactive menu
- `batch-create`: `skill_use("propose", "--batch-create")` — creates skeleton changes for all pending suggestions

### Modified Capabilities
- `guide-plan`: Entry point now detects `--non-interactive` / `SKIP_GUIDE_PLAN_MENU`; when set, Phase 3 menu is skipped and default flow runs
- `propose`: Phase 4 now accepts `--batch-create` to iterate over all pending suggestions automatically

## Impact

- **New code**: ~60 lines (guide-plan.md entry detection) + ~40 lines (propose.md batch-create) + ~80 lines (tests) = ~180 lines
- **Dependencies**: None — uses existing `propose_change.sh` skeleton creation path
- **Compatibility**: 100% backward compatible — omitting `--non-interactive` preserves existing interactive behavior
- **Risk**: Low — additive; all paths are optional and gated behind flags/env vars
- **Source**: 复盘改进 #1, improvement `guide-plan-noninteractive`