# fix-review-debt-recorded-gate — Design

## Context

ADR-0014 §决策 5 规定 `gate.py` 注册 `review_debt_recorded`(warning 级)检查,确保用户在 `guide-ship` Phase 2.5 review 阶段记录债务或显式跳过。

**Architectural basis**: ADR-0014 (see proposal.md "Why" for full audit context).

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
| `ship_review.sh` | module | Modified per proposal scope |
| `proposal-suggestions.md` | module | Modified per proposal scope |
| `.rddf/improvements/cleanup-<change>-debt.md` | module | Modified per proposal scope |
| `.rddf/improvements/old-debt-2024.md` | module | Modified per proposal scope |

## Risks / Trade-offs

- **Risk**: Conflict with parallel in-flight changes touching same files.
  **Mitigation**: This change targets isolated subsystems; verify no overlap via `git diff` before archive.
- **Risk**: Schema-mandated `manual_deps`/`manual_blocks` may be incomplete.
  **Mitigation**: Run `rddf deps` after fill to validate dependency declarations.

## Implementation Notes

Key scenarios to verify (full Gherkin in proposal.md):

### 场景 A

**GIVEN** `.go` 文件新增 `// TODO: refactor this part`
**WHEN** Phase 2.5 commit 前 ship_review.sh 调 helper
**THEN**
- helper 扫 `.go` 文件(18 种语言 glob 含 `.go`)
- 探测 `.rddf/improvements/cleanup-<change>-debt.md` 是否存在且 mtime > execute_finished_at
- 若不存在 → 提示用户选项 1-3(范围內 / side-effect / arch drift)
- 若存在 → si

### 场景 B

**GIVEN** 用户在 `project-root/subdir/` 跑 `rddf doctor` 等触发 gate 的命令
**WHEN** helper 执行
**THEN**
- 必填参数 `project_root` 来自 `ctx`,绝对路径
- `Path(project_root) / ".rddf/improvements"` 解析正确
- 无 silent failure

### 场景 C

**GIVEN** `.rddf/improvements/` 目录无读权限或被删
**WHEN** helper 执行
**THEN**
- `except PermissionError as e:` → 记录具体 stderr 提示 `cannot read .rddf/improvements: <reason>`
- 返回 `(False, "warning")`(与 disk-error 相符的警告)
- 不静默 pass

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
