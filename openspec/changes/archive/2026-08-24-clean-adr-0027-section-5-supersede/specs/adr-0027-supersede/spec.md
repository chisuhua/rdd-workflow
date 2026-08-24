## ADDED Requirements

### Requirement: clean-adr-0027-section-5-supersede
The system SHALL implement clean-adr-0027-section-5-supersede functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** 翻到 §5 末尾
- **WHEN** **THEN**
- **THEN** - 看到 supersession 注,提示设计已由 ADR-0029 替代
- 不需要逐字读 ADR-0029;知道 §5 是设计历史,真正路径看 ADR-0029

#### Scenario: scenario-2
- **GIVEN** **WHEN** 看到 YAML 示例
- **WHEN** **THEN**
- **THEN** - **不**看到 `retention_days: 30`(本提案删除该字段)
- 看到注释:`retention_days 因 prunable code path 不可达,本 ADR 已删除承诺`
- 不会被过期字段误导配置

#### Scenario: scenario-3
- **GIVEN** **WHEN** 寻找 `issue_reporter_schema.json`
- **WHEN** **THEN** **不**存在该 schema 文件;改为看到注释:`配套 schema 改为依赖现有 _lib/schemas/config_schema.json 的 reporting namespace;issue_reporter 不再单独维护 schema`

