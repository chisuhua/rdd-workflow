# add-openspec-gate

**优先级**: P0
**阶段**: v2.1
**分类**: quality

## Why

复盘事件 2026-07-26/27 显示：UsrLinuxEmu 的 `stage4-1-bar-ioremap` 提案被批准后，开发者直接 commit 3 个 TDD 实现（571f9af / 556b647 / 116ca8c），proposal 滞留 `proposal-approved.md` 直到 `guide-plan` 触发才发现 → backfill 模式补追溯。

根本原因：pre-commit 不检查"代码变更 ↔ openspec/changes/ 关联"，即工作流外提交无法自动检测。

## What Changes

在 3 层增加 openspec 联动检测：
1. **仓库层（预防）**: pre-commit 串联 openspec-gate（~50ms），检测 staged 文件路径是否匹配 openspec change
2. **skill 层（检测）**: 新建 `skills/openspec-gate/`，默认 glob: `include/ src/ *.cpp *.h`
3. **workflow 层（联动）**: `plan_intake.sh` 检测 `proposal-approved.md` staleness

## Architecture

- 与 add-full-regression-gate 共享 pre-commit 文件（openspec-gate 先，cheap ~50ms；regression-gate 后，expensive ~30s）
- 默认软警告模式，`OPENSPEC_GATE_MODE=block` 可升级为硬拦截
- `config.yaml` 新增 `openspec_gate:` 配置节
