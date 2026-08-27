# fix-design-preflight-roadmap-format — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `_read_roadmap_themes` 支持 `## Phase Skeleton` 表格格式
- [x] Task 2: `_read_roadmap_themes` 保留对 `### Phase N:` 段落格式的支持
- [x] Task 3: 新增 unit test `test_design_preflight_roadmap.py` (7 tests, all pass) + `test_parse_phase_skeleton_table` + `test_parse_phase_n_section`
- [x] Task 4: 在当前 master 上 `compute_theme_coverage` 返回 10 themes 而不是 0 (verified by test_compute_theme_coverage_returns_ten_themes_on_current_roadmap)
- [x] Task 5: 不修改 `.rddf/roadmap.md` 主文档 (backward-compat parse, both formats supported)
- [x] Task 6: `guide-design/SKILL.md` Phase 1 preflight 段说明新格式支持 (added "Roadmap 格式支持" section)
