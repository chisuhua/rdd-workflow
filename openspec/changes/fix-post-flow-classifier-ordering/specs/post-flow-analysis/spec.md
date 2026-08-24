## ADDED Requirements

### Requirement: fix-post-flow-classifier-ordering
The system SHALL implement fix-post-flow-classifier-ordering functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** classifier 执行
- **WHEN** **THEN**
- **THEN** - F1 正则匹配(`Traceback` + 栈帧路径含 `skills/_lib/` 或 `_lib/`)
- 分类为 `phase-crash`
- `dedup_hash` 基于前 3 个 stack frame 归一化

#### Scenario: scenario-2
- **GIVEN** **WHEN** classifier 执行
- **WHEN** **THEN**
- **THEN** - F4 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- Reporter 段记 `skill_invoked: gate-system`

#### Scenario: scenario-3
- **GIVEN** **WHEN** classifier 执行
- **WHEN** **THEN**
- **THEN** - F2 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- **不再是 F3-mislabeled as flow-bug**

