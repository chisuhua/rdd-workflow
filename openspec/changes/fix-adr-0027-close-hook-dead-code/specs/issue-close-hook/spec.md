## ADDED Requirements

### Requirement: fix-adr-0027-close-hook-dead-code
The system SHALL implement fix-adr-0027-close-hook-dead-code functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** `archive_change add-foo-feature main` 完整执行
- **WHEN** **THEN**
- **THEN** 1. `openspec archive add-foo-feature --yes` 成功,`openspec/changes/add-foo-feature/` 移到 `archive/`
2. `close_issues_for_change_hook` 调 `_load_issue_refs`
3. `_load_issue_refs` 尝试 `openspec/changes/add-f

#### Scenario: scenario-2
- **GIVEN** **WHEN** `ship_archive.sh` 完成 `openspec archive`
- **WHEN** **THEN** 走同一 hook,与场景 A 行为一致

#### Scenario: scenario-3
- **GIVEN** **WHEN** hook 仍然尝试(由 `|| true` 兜底)
- **WHEN** **THEN**
- **THEN** - `roadmap-meta.yaml` 未移动 → 第一次候选路径命中 → close 正常执行
- (这是为什么 G1 修复用双路径而不是 hook 顺序的修复:即使 hook 在前 archive 在后,也能工作)

