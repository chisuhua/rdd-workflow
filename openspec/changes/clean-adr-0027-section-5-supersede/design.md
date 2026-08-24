# clean-adr-0027-section-5-supersede — Design

## Context

Oracle 复核在审计 ADR-0027 实施现状时发现 4 个文档/对齐类问题(合成本 PR-6):

**Architectural basis**: ADR-0027, ADR-0029 (see proposal.md "Why" for full audit context).

## Goals / Non-Goals

**Goals:**

- Implement the changes scoped in proposal.md "What Changes" → "In Scope"
- Pass all acceptance criteria defined in proposal.md scenarios (场景 A/B/C)
- Add regression tests at unit and/or bats integration level

**Non-Goals:**

- Any item marked `**不**` in proposal.md "What Changes" → "In Scope" (out of scope)
- Refactoring unrelated to the fix
- Adding new external dependencies

## Decisions

### 1. Implementation approach

**Decision**: Apply minimum-diff edits to existing files listed in scope; add tests in `tests/unit/` (Python) or `tests/integration/` (bats) as appropriate to scope.

**Rationale**: Matches the codebase convention of co-locating tests with code they exercise; minimum diff keeps review surface small.

**Alternatives considered:**

- Full module rewrite: rejected — increases blast radius and conflicts with other in-flight changes

### 2. Test placement

**Decision**: Place new tests adjacent to the module they exercise (bats for shell scripts, pytest for Python).

**Rationale**: Matches existing pattern in `tests/integration/` and `tests/unit/`.

### 3. Schema/convention compliance

**Decision**: Maintain compatibility with existing `.openspec.yaml` schema (with `schema: spec-driven` field) and `roadmap-meta.yaml` ADR-0022 fields (`manual_deps`, `manual_blocks`).

## Affected Components

| Component | Type | Reason |
|-----------|------|--------|
| `.rddf/state/.issue-reporter.json` | module | Modified per proposal scope |
| `.rddf/state/.reporting-config.json` | module | Modified per proposal scope |
| `_lib/schemas/issue_reporter_schema.json` | module | Modified per proposal scope |
| `issue_reporter_schema.json` | module | Modified per proposal scope |

## Risks / Trade-offs

- **Risk**: Conflict with parallel in-flight changes touching same files.
  **Mitigation**: This change targets isolated subsystems; verify no overlap via `git diff` before archive.
- **Risk**: Schema-mandated `manual_deps`/`manual_blocks` may be incomplete.
  **Mitigation**: Run `rddf deps` after fill to validate dependency declarations.

## Implementation Notes

Key scenarios to verify (full Gherkin in proposal.md):

### 场景 A

**GIVEN** 用户读 ADR-0027 §5 "Triage - guide-design / guide-arch 消费 issue"
**WHEN** 翻到 §5 末尾
**THEN**
- 看到 supersession 注,提示设计已由 ADR-0029 替代
- 不需要逐字读 ADR-0029;知道 §5 是设计历史,真正路径看 ADR-0029

### 场景 B

**GIVEN** 用户阅读 ADR-0027 §3 "默认配置"
**WHEN** 看到 YAML 示例
**THEN**
- **不**看到 `retention_days: 30`(本提案删除该字段)
- 看到注释:`retention_days 因 prunable code path 不可达,本 ADR 已删除承诺`
- 不会被过期字段误导配置

### 场景 C

**GIVEN** 实施者读 ADR §6 "schema 版本"段
**WHEN** 寻找 `issue_reporter_schema.json`
**THEN** **不**存在该 schema 文件;改为看到注释:`配套 schema 改为依赖现有 _lib/schemas/config_schema.json 的 reporting namespace;issue_reporter 不再单独维护 schema`

## Verification Plan

1. **Unit tests** — Run `pytest tests/unit/ -q` after edits; expect new tests pass, no existing test breaks.
2. **Integration tests** — Run `bats tests/integration/<new>.bats` for shell-touching changes.
3. **Acceptance scenarios** — Manually verify scenarios in proposal.md (场景 A 主路径).
4. **Full regression** — Run `./test.sh --full --regression` before archive; ensure no new failures vs `tests/KNOWN_FAILURES.txt`.

## Success Criteria

- All scenarios in proposal.md pass.
- All new tests in scope pass.
- No regressions in adjacent modules.
- `openspec validate <change>` passes.
