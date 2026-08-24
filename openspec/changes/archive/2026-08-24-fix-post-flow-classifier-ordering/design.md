# fix-post-flow-classifier-ordering — Design

## Context

ADR-0027 §1.2 规定 classifier 三段式(usage / environment / flow-bug)+ 4 类触发分类(F1 traceback in `_lib/` → `phase-crash`,F2 ConfigError / gate raised → `gate-failure`,F3 invalid state / unexpected status → `flow-bug`,F4-gate 自定义 → `gate-failure`)。

**Architectural basis**: ADR-0018, ADR-0027 (see proposal.md "Why" for full audit context).

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
| `_lib/post_flow_analysis.py` | module | Modified per proposal scope |

## Risks / Trade-offs

- **Risk**: Conflict with parallel in-flight changes touching same files.
  **Mitigation**: This change targets isolated subsystems; verify no overlap via `git diff` before archive.
- **Risk**: Schema-mandated `manual_deps`/`manual_blocks` may be incomplete.
  **Mitigation**: Run `rddf deps` after fill to validate dependency declarations.

## Implementation Notes

Key scenarios to verify (full Gherkin in proposal.md):

### 场景 A

**GIVEN** `_lib/post_flow_analysis.py` 抛 `ZeroDivisionError`,stderr 含 traceback 帧
**WHEN** classifier 执行
**THEN**
- F1 正则匹配(`Traceback` + 栈帧路径含 `skills/_lib/` 或 `_lib/`)
- 分类为 `phase-crash`
- `dedup_hash` 基于前 3 个 stack frame 归一化

### 场景 B

**GIVEN** `_lib/gate.py::_check_arch_debt` raise `ConfigError`,stderr 含 `gate raised in _check_*`
**WHEN** classifier 执行
**THEN**
- F4 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- Reporter 段记 `skill_invoked: gate-system`

### 场景 C

**GIVEN** schema 加载抛 `ConfigError`,stderr 含 `"Config validation failed: ..."`(不含 "gate raised")
**WHEN** classifier 执行
**THEN**
- F2 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- **不再是 F3-mislabeled as flow-bug**

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
