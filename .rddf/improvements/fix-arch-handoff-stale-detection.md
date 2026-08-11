# fix-arch-handoff-stale-detection

**优先级**: P1 | **来源**: Session 复盘 2026-07-26 — PTX-EMU ADR 检测失效
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据
- Session 复盘发现：PTX-EMU 项目有 5 个 `docs/adr/ADR-*.md` 文件和一个 `roadmap.md`，但 `arch-handoff.json` 记录 `adr_count=0, discovered.adr_dir.found=false`
- 根因：`write_arch_handoff.py` 的 ADR 发现逻辑基于有限 `candidates_tried` 列表，在非标准上下文中执行时未命中 `docs/adr/`。一旦写入错误 handoff，后续所有 `guide` 入口的 `scan_state()` 都无条件信任该值，不做文件系统交叉验证
- 影响：错误推荐 `guide-arch`（高置信度），用户被引导进入空转流程

## 范围
- **In Scope**:
  - `scan_state()` 新增轻量文件系统交叉验证：当 `arch-handoff.adr_count == 0` 时，检查 `"$PROJECT_ROOT/docs/adr/ADR-*.md"` 是否存在
  - 发现不一致时：自动标记 handoff 为 `stale`，降低 guide-arch 推荐置信度（`high` → `low`），在 reason 中注明 "arch-handoff 可能过期"
  - 新增 `guide` 入口提示："⚠️ arch-handoff 记录 0 ADRs 但文件系统发现 N 个 — handoff 可能过期，建议重新运行 guide-arch"
- **Out Scope**:
  - 不自动重写 arch-handoff（修改状态文件的风险）
  - 不修改 `write_arch_handoff.py` 的发现逻辑（那是另一改进项）

## 关键场景
- GIVEN `arch-handoff.adr_count=0` 但 `docs/adr/ADR-*.md` 存在, WHEN `scan_state()` 执行, THEN 输出警告且推荐置信度降级
- GIVEN `arch-handoff.adr_count=5` 且文件系统一致, WHEN `scan_state()` 执行, THEN 行为不变
- GIVEN `arch-handoff` 不存在, WHEN `scan_state()` 执行, THEN 行为不变（走原有推荐路径）

## 技术约束
- MUST 保持读写分离——`scan_state()` 是只读扫描，不修改 handoff 文件
- MUST NOT 引入新的 Python 依赖（用 `ls` + `wc -l` bash 实现交叉验证）

## 验收标准
- `scan_state` 在 handoff 过期时输出 `⚠️` 警告且置信度降级
- 新 bats 测试覆盖 "arch-handoff stale" 场景
- 不改变 handoff 正确时的原有推荐行为