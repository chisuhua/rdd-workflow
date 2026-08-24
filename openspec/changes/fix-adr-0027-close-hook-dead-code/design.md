# fix-adr-0027-close-hook-dead-code — Design

## Context

ADR-0027 §6(Close 环)规定:`guide-ship` Phase 3 archive 成功后,自动关闭通过 `issue_refs` 关联的 GitHub issue。第 5 环是反馈环闭环关键,但 Oracle 复核发现**实现是死代码**——所有调用恒 no-op,用户无任何报错。

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
| `openspec/changes/add-foo-feature/roadmap-meta.yaml` | module | Modified per proposal scope |
| `.rddf/issues/flow-bug-a1b2c3d4.md` | module | Modified per proposal scope |
| `ship_archive.sh` | module | Modified per proposal scope |
| `roadmap-meta.yaml` | module | Modified per proposal scope |

## Risks / Trade-offs

- **Risk**: Conflict with parallel in-flight changes touching same files.
  **Mitigation**: This change targets isolated subsystems; verify no overlap via `git diff` before archive.
- **Risk**: Schema-mandated `manual_deps`/`manual_blocks` may be incomplete.
  **Mitigation**: Run `rddf deps` after fill to validate dependency declarations.

## Implementation Notes

Key scenarios to verify (full Gherkin in proposal.md):

### 场景 A

**GIVEN** `guide-ship` Phase 3 worktree 模式,change `add-foo-feature` 有 `issue_refs: [42, 123]`
**WHEN** `archive_change add-foo-feature main` 完整执行
**THEN**
1. `openspec archive add-foo-feature --yes` 成功,`openspec/changes/add-foo-feature/` 移到 `archive/`
2. `close_issues_for_change_hook` 调 `_load_issue

### 场景 B

**GIVEN** Lightweight 模式(主仓库直接 archive,不走 worktree)
**WHEN** `ship_archive.sh` 完成 `openspec archive`
**THEN** 走同一 hook,与场景 A 行为一致

### 场景 C

**GIVEN** `openspec archive` 失败(exit code != 0)
**WHEN** hook 仍然尝试(由 `|| true` 兜底)
**THEN**
- `roadmap-meta.yaml` 未移动 → 第一次候选路径命中 → close 正常执行
- (这是为什么 G1 修复用双路径而不是 hook 顺序的修复:即使 hook 在前 archive 在后,也能工作)

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
