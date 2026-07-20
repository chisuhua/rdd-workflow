# Tasks

## [1/2] Expand roadmap.md with v2.1/v3.0 change mapping
- [x] Verify v2.1 Phase 1 has 5 base change entries (v2-multi-session, add-review-phase-debt-reflow, add-openspec-validate-critic, add-arch-artifact-discovery, add-incremental-skeleton-planning) + add-manual-deps-field
- [x] Verify v2.1 Phase 2 (编排能力完善) has add-manual-deps-field entry
- [x] Verify each change row has: name, priority, effort, wave, manual_deps, description
- [x] Verify backward compatibility with existing parsers (roadmap_state.py, scan-state.sh)
## [2/2] Run gap analysis scan
- [x] Scan ADR gaps (待定 / 模板 status without推进 change)
- [x] Scan TODO/FIXME in skills/ and docs/ (literal `# TODO` / `# FIXME` comments only)
- [x] Scan test coverage gaps (modules without dedicated unit test)
- [x] Update proposal-suggestions.md with discovered gaps (status=pending, source=gap-analysis: refresh-input-sources)
