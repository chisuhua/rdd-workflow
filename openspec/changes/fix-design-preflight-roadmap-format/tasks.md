# fix-design-preflight-roadmap-format — Implementation Tasks

## Implementation Tasks

- [ ] Task 1: `_read_roadmap_themes` 支持 `## Phase Skeleton` 表格格式
- [ ] Task 2: `_read_roadmap_themes` 保留对 `### Phase N:` 段落格式的支持
- [ ] Task 3: 新增 unit test `test_parse_phase_skeleton_table` 和 `test_parse_phase_n_section`
- [ ] Task 4: 在当前 master 上 `compute_theme_coverage` 返回 10 themes 而不是 0
- [ ] Task 5: 不修改 `.rddf/roadmap.md` 主文档(向后兼容)
- [ ] Task 6: `guide-design/SKILL.md` Phase 1 preflight 段说明新格式支持
- [ ] Task 7: Run `bash tests/scripts/report_regression.sh` to confirm no new failures