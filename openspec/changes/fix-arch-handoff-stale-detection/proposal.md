## Why

`write_arch_handoff.py` 的 ADR 发现逻辑基于有限 `candidates_tried` 列表，在非标准上下文中执行时未命中 `docs/adr/`。一旦写入错误 handoff，后续所有 `guide` 入口的 `scan_state()` 都无条件信任该值，不做文件系统交叉验证，导致错误推荐 `guide-arch`。

## What Changes

- `scan_state()` 新增轻量文件系统交叉验证：当 `arch-handoff.adr_count == 0` 时，检查 `"$PROJECT_ROOT/docs/adr/ADR-*.md"` 是否存在
- 发现不一致时：自动标记 handoff 为 `stale`，降低 guide-arch 推荐置信度（`high` → `low`）
- 新增 `guide` 入口提示："⚠️ arch-handoff 记录 0 ADRs 但文件系统发现 N 个 — handoff 可能过期，建议重新运行 guide-arch"

## Capabilities

### New Capabilities
- `arch-handoff-stale-detection`: 检测 arch-handoff 是否过期

### Modified Capabilities
- `guide-scan`: 在 scan-state.sh 中增加文件系统交叉验证

## Impact

- 修改文件：skills/guide/scripts/scan-state.sh
- 影响流程：guide 推荐器入口
- 只读操作：不修改 handoff 文件
