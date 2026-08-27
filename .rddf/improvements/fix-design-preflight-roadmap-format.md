# fix-design-preflight-roadmap-format

**优先级**: P1 | **来源**: 2026-08-27 ship audit (3 P1 docs-consistency changes ship) + 2026-08-27 feat-fix-audit-findings Hybrid 路径
**阶段**: default | **分类**: governance
**类型**: bugfix

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

`skills/guide-design/scripts/design_preflight.py:19` 的 `_PHASE_HEADER_RE = re.compile(r"^### Phase \d+:[^\n]*?\(phase-[a-z0-9-]+\)")` 期望 `.rddf/roadmap.md` 用 `### Phase N: <name> (phase-X)` 标题 + 5 列分类表格式。

但实际 `.rddf/roadmap.md` 是简化表格格式 (`## Phase Skeleton` + 5 列 Phase/Theme/Status/Started/Done)。

后果:

- `compute_theme_coverage()` 永远返回 0 themes,即使主表含 10 个 theme 行。
- `list_uncovered_themes` 无法返回未覆盖 themes,user 在 guide-design 看不到哪个 roadmap theme 还没对应 proposal。
- `check_theme_coverage_gate` 在 STRICT 模式下不会 block(因为 0 themes 视为通过)。

期望行为: `design_preflight.py` 应该支持当前 `.rddf/roadmap.md` 的简化格式(也兼容历史 `### Phase N:` 格式)。

## 范围

**In Scope**:

- `_read_roadmap_themes` 重构,同时支持两种格式:
  - 新格式: `## Phase Skeleton` + `| Phase | Theme | ... |` 表格
  - 老格式: `### Phase N: ... (phase-X)` + 分类表
- `_PHASE_HEADER_RE` 改为可选(仅在老格式中需要)
- 新增 unit test 覆盖两种格式

**Out of Scope**:

- 强制迁移 `.rddf/roadmap.md` 格式(向后兼容)
- 修复历史 178 个 unmapped legacy proposals(单独的 sync 提案)

## 关键场景

- GIVEN `.rddf/roadmap.md` 是新格式 (Phase Skeleton + 5列表格)
  WHEN `compute_theme_coverage` 调用
  THEN 返回正确的主题列表(10 themes),而不是 0

- GIVEN `.rddf/roadmap.md` 是老格式 (### Phase N: ...)
  WHEN `compute_theme_coverage` 调用
  THEN 仍能正确解析(向后兼容)

## 技术约束

- MUST: 两种格式都能解析(向后兼容,不要 break 老文档)
- MUST: Phase ID 必须能被识别为 `phase-X` 格式
- MUST NOT: 强制用户迁移格式
- SHOULD: 提供格式化帮助信息告诉用户哪种格式被检测

## 验收标准

- [ ] `_read_roadmap_themes` 支持 `## Phase Skeleton` 表格格式
- [ ] `_read_roadmap_themes` 保留对 `### Phase N:` 段落格式的支持
- [ ] 新增 unit test `test_parse_phase_skeleton_table` 和 `test_parse_phase_n_section`
- [ ] 在当前 master 上 `compute_theme_coverage` 返回 10 themes 而不是 0
- [ ] 不修改 `.rddf/roadmap.md` 主文档(向后兼容)
- [ ] `guide-design/SKILL.md` Phase 1 preflight 段说明新格式支持
