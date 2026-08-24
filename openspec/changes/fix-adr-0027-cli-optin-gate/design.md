# fix-adr-0027-cli-optin-gate — Design

## Context

ADR-0027 §3 规定反馈环三重 opt-in 闸门:`reporting.enabled`(默认 false)、`reporting.auto_submit`(默认 false)、`reporting.submit_categories[<cat>]` 粒度 opt-in,叠加 CI 环境自动降级。§1.0 同时规定两平面(脚本 + agent)都必须经过同意边界。

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
| `.rddf/issues/phase-crash-<hash>.md` | module | Modified per proposal scope |
| `RDDF_REPORT_ENABLED=yes RDDF_REPORT_AUTO_SUBMIT=yes rddf issue submit .rddf/issues/phase-crash-<hash>.md` | module | Modified per proposal scope |

## Risks / Trade-offs

- **Risk**: Conflict with parallel in-flight changes touching same files.
  **Mitigation**: This change targets isolated subsystems; verify no overlap via `git diff` before archive.
- **Risk**: Schema-mandated `manual_deps`/`manual_blocks` may be incomplete.
  **Mitigation**: Run `rddf deps` after fill to validate dependency declarations.

## Implementation Notes

Key scenarios to verify (full Gherkin in proposal.md):

### 场景 A

**GIVEN** `guide-ship` Phase 2 execute 结束、exit code = 137(SIGKILL)
**WHEN** SKILL.md Phase Exit 段指示 agent 调 `rddf report-issue --exit-code 137 --no-submit --category phase-crash --phase guide-ship "execute crashed"`
**THEN**
1. argparse 接收全部已知 flag → exit 0
2. `--no-submit` 默认 true → `submit_issue_v

### 场景 B

**GIVEN** 用户在本地看到 `.rddf/issues/phase-crash-<hash>.md` 想提交
**WHEN** `RDDF_REPORT_ENABLED=yes RDDF_REPORT_AUTO_SUBMIT=yes rddf issue submit .rddf/issues/phase-crash-<hash>.md`
**THEN**
1. `issue_cmd::cmd_issue` 校验 `RDDF_REPORT_ENABLED=yes` → 通过
2. 校验 `RDDF_REPORT_AUTO_SUBMIT=yes` → 通过
3. 校验文件 frontma

### 场景 C

**GIVEN** 用户没设 `RDDF_REPORT_AUTO_SUBMIT`(即使 `RDDF_REPORT_ENABLED=yes`)
**WHEN** `rddf issue submit <file>`
**THEN**
1. `submit_issue_via_gh` 直接拒绝并打印提示:L2 opt-out by default,exit 2,非 0
2. 本地 issue 文件**不变**(L1 已写,保留供用户后续手动操作)
3. stderr 提示:`Set RDDF_REPORT_AUTO_SUBMIT=yes AND ensure file category is in

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
