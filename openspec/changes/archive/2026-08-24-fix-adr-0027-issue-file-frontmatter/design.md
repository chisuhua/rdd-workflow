# fix-adr-0027-issue-file-frontmatter — Design

## Context

ADR-0027 §4 规定 issue 文件必须含完整 8 段 frontmatter(`category`/`detected_at`/`rdd_workflow_version`/`dedup_hash`/`submitted`/`submitted_url`)+ **Reporter 段**(6 必填字段:python/git/os/project_hash/rddf_session_id/skill_invoked)+ **Stack trace 段**+ **Repro 段**。

**Architectural basis**: ADR-0027 (see proposal.md "Why" for full audit context).

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
| `.rddf/issues/<cat>-<hash>.md` | module | Modified per proposal scope |
| `sanitizer.py` | module | Modified per proposal scope |
| `.rddf/issues/phase-crash-<hash>.md` | module | Modified per proposal scope |

## Risks / Trade-offs

- **Risk**: Conflict with parallel in-flight changes touching same files.
  **Mitigation**: This change targets isolated subsystems; verify no overlap via `git diff` before archive.
- **Risk**: Schema-mandated `manual_deps`/`manual_blocks` may be incomplete.
  **Mitigation**: Run `rddf deps` after fill to validate dependency declarations.

## Implementation Notes

Key scenarios to verify (full Gherkin in proposal.md):

### 场景 A

**GIVEN** 用户跑 `rddf report-issue --exit-code 137 --phase guide-ship "execute crashed"`
**WHEN** `_render_issue_body` 执行
**THEN** 生成的 `.rddf/issues/phase-crash-<hash>.md` 含:
```yaml
---
category: phase-crash
detected_at: 2026-08-24T10:23:45Z
rdd_workflow_version: 2.1.0
dedup_hash: a1b2c3d4
submitted:

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
