# general Specification

## Purpose
Cross-cutting contracts that keep this repository's contract surfaces aligned with the
implementation: the dependency-analysis skill's optional AI semantic pass, the ADR
directory's structure invariants, documentation-vs-code truthfulness, and the
environment-cache / architecture-discovery conventions.
## Requirements
### Requirement: general-deps-subagent-semantic-analysis

`skills/deps/SKILL.md` SHALL present the optional AI semantic analysis as a subagent
call in Step 3 that reads the change's `proposal.md`, `design.md` and `tasks.md`, SHALL
document the degraded path when the subagent is unavailable, and SHALL keep the
`AI 语义分析未启用` marker that downstream consumers match on.

#### Scenario: Step 3 subagent call references all three artifacts

- **WHEN** the Step 3 section of `skills/deps/SKILL.md` is read
- **THEN** it SHALL contain the subagent call syntax
- **AND** it SHALL reference `proposal.md`, `design.md` and `tasks.md`

#### Scenario: subagent failure falls back to static analysis

- **WHEN** the subagent is unavailable or fails
- **THEN** the skill SHALL document the fallback to the static three-axis analysis
- **AND** the fallback SHALL preserve the literal marker `AI 语义分析未启用`

#### Scenario: no unresolved TODO marker remains

- **WHEN** `skills/deps/SKILL.md` is inspected
- **THEN** it SHALL NOT contain a TODO marker for the subagent semantic analysis
- **AND** it SHALL NOT hardcode a `TODO.*deps.md L320` reference in the Step 5 heredoc or in section 5e

### Requirement: general-adr-directory-structure

The `docs/adr/` directory SHALL contain the reserved `ADR-0000-template.md`, an index
`README.md`, and at least one real ADR. The template SHALL carry its required
frontmatter and all four required sections, and every real ADR SHALL carry a
`# ADR-NNNN:` header, a decision section, a context section, and status + date fields.

#### Scenario: ADR directory holds the reserved template, an index and real ADRs

- **WHEN** `docs/adr/` is listed
- **THEN** `ADR-0000-template.md` SHALL exist
- **AND** `README.md` SHALL exist
- **AND** at least one real ADR file SHALL exist besides the template

#### Scenario: every real ADR carries the required structure

- **WHEN** each `docs/adr/ADR-*.md` file other than the template is inspected
- **THEN** it SHALL have a `# ADR-NNNN:` header
- **AND** it SHALL have a decision section (`## 决策` or `## Decision`)
- **AND** it SHALL have a `## Context` section
- **AND** it SHALL have status and date fields

#### Scenario: the ADR index documents the citation format

- **WHEN** `docs/adr/README.md` is read
- **THEN** it SHALL document the `ADR-NNN §N.M` citation format

### Requirement: general-harden-doc-consistency
The system SHALL harden documentation and code consistency for rdd-workflow v1.1 by removing orphan bash helpers, fixing hardcoded branch references, and synchronizing all docs with actual code state.

#### Scenario: Orphan bash helpers removed
- **WHEN** `_lib/state.sh` is inspected
- **THEN** it SHALL NOT export `safe_python_json`, `safe_python_yaml`, `read_suggestions`, or `write_suggestions` (zero call sites confirmed)
- **AND** the file SHALL either be removed entirely or reduced to a stub

#### Scenario: is_change_committed removed
- **WHEN** `_lib/worktree.sh` is inspected
- **THEN** it SHALL NOT export `is_change_committed` (zero call sites confirmed)

#### Scenario: no inline re-implementation of wt_path_for_branch
- **WHEN** the live tree (`_lib/`, `skills/`) is searched for an inline
  `wt_path_for_branch` re-implementation
- **THEN** none SHALL define one
- **AND** all callers SHALL use `_lib/worktree.sh::wt_path_for_branch` (after sourcing)

#### Scenario: find_default_branch works in worktree context
- **WHEN** `find_default_branch` is called from inside a worktree
- **THEN** it SHALL return the project's default branch (`master`/`main`/`develop`)
- **AND** it SHALL NOT return the worktree's own `openspec/<name>` branch as fallback

### Requirement: general-docs-match-code

The system SHALL ensure all user-facing documentation in `USAGE.md`, `README.md`,
`docs/adr/*.md`, `skills/*.md`, and `tests/README.md` accurately reflects the
actual code state as of the change's commit. The locked fields enumerated in
the Scenarios below SHALL additionally be enforced by the anti-drift tests
introduced in `openspec/specs/doc-truth-sync/spec.md::Requirement doc-contract-tests-required`.

#### Scenario: USAGE.md ship-side phase count

- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as **7 numbered subphases (Phase 1, 1.5,
  2, 2.5, 3, 4, 5)** with sequence
  `plan → verification → execute → review → archive → cleanup → ship-done`
- **AND** it SHALL NOT describe ship-side as "5 phases + 1 exit" (the v1.x
  model is stale as of v2.0.1)
- **AND** Phase 2.5 Review SHALL be explicitly named (execute 后债务扫描)

#### Scenario: USAGE.md state-file table uses dotted prefix convention

- **WHEN** `USAGE.md` is read
- **THEN** the state-file table SHALL list only files that exist on disk
- **AND** all state files SHALL match production paths — specifically:
  - `.rddf/state/.arch-handoff.json`
  - `.rddf/state/.plan-handoff.json`
  - `.rddf/state/deps-analysis.json`
  - `.rddf/state/.deps-candidates.json`
  - `.rddf/state/.deps-output.md` (with legacy undotted path noted as compat)
  - `.rddf/state/sessions.json`
  - `.rddf/state/iteration.json`
  - `.rddf/state/index.md`
  - `.rddf/state/roadmap-state.json` and/or `.rddf/state/.roadmap-state.json` only if the doc explicitly labels which one is canonical and which one is legacy/compat
- **AND** the table SHALL NOT contain `handoff.json` (undotted) or
  `.sisyphus/plans/<name>.md` (wrong directory)
- **AND** `improvement-suggestions.md` at project root SHALL remain undotted
  (git-tracked, intentional)

#### Scenario: USAGE.md describes lightweight and worktree ship modes

- **WHEN** `USAGE.md` is read
- **THEN** it SHALL describe ship-side as supporting two execution modes:
  - **⚡ 轻量模式 (lightweight)**: no other worktree AND only this one change,
    creates `openspec/<name>` branch directly in main repo (skipping worktree)
  - **🔀 worktree 模式**: active worktree OR multiple changes, creates
    `.rddf/wt/<name>` isolated worktree
- **AND** it SHALL explain that lightweight mode skips the
  `git worktree remove` step during archive (no worktree to remove)

#### Scenario: package.json skills array aligns with INSTALL.md description

- **WHEN** `package.json::skills[]` is read
- **AND** the canonical skill count is computed (`skills/<name>/SKILL.md`,
  excluding skills whose `SKILL.md` contains a `metadata:`/`deprecated:` marker)
- **THEN** the difference SHALL be 0
- **AND** `package.json` SHALL NOT contain a `_comment` field (Decision 3 翻 A 后所有 skill 都通过 npm 发布,无 src-only 例外)
- **AND** `skills/INSTALL.md` description SHALL NOT enumerate skill names or state a src-only delta(描述应采用计数式,如"详见 skills/ 目录")
- **AND** upstream `package.json` MUST contain `feature` and `rddf-session`(Decision 3 = A 已锁定)

#### Scenario: skill instruction files do not hardcode a concrete machine or project path

- **WHEN** the instruction surface (`skills/**/*.md`) is searched for hardcoded
  concrete machine or project paths (`/path/to/CppHDL`, `/workspace/project/<name>`,
  `/home/<user>/.config/...`)
- **THEN** none SHALL appear (generic placeholders such as `/path/to/<repo>`,
  `<project-root>`, `~/.config/opencode` and `${PROJECT_ROOT}` are allowed)

#### Scenario: skill files do not hardcode main branch

- **WHEN** `skills/**/*.md` is searched for the literal word "main 分支" or
  "main branch" in user-facing output
- **THEN** it SHALL NOT appear (use `${DEFAULT_BRANCH:-master}` or dynamic
  detection via `find_default_branch()` instead)

#### Scenario: superseded ADR-0001 is marked as superseded in the ADR index

- **WHEN** `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` is read
- **THEN** its status line SHALL state it is superseded by ADR-0002 + ADR-0003
- **AND** `docs/adr/README.md` SHALL list ADR-0001 with the same superseded status

#### Scenario: INSTALL.md version matches package.json

- **WHEN** `skills/INSTALL.md` is read
- **THEN** its version field SHALL match `package.json::version`
- **AND** its embedded package.json heredoc SHALL derive the `skills` array
  from the actual `package.json` (using python3 json.load, not hardcoded list)
- **AND** its description SHALL include the disk count matching
  `package.json::skills[]` length (Decision 3 = A 已锁定,无 src-only 例外);
  不应出现"13 vs 11"或"src-only delta"等表述

#### Scenario: proposal-suggestions-format consumer list is current

- **WHEN** `docs/improvement-suggestions-format.md` is read
- **THEN** its consumer list SHALL name only skills that have a
  `skills/<name>/SKILL.md` on disk
- **AND** it SHALL include `rdd-planner`, `rdd-builder`, `propose`, and `add-improve`

#### Scenario: propose uses 4-digit ADR pattern

- **WHEN** `skills/propose/scripts/propose_quality_check.py` L53 is read
- **THEN** the regex SHALL use `ADR-NNNN` (4-digit) to match
  `docs/adr/README.md` convention

#### Scenario: tests/README.md Layout matches the actual test tree

- **WHEN** `tests/README.md` Layout section is read
- **THEN** it SHALL list every top-level directory of `tests/` except generated
  ones (`__pycache__`)
- **AND** it SHALL list the root files `smoke.bats`, `test_helper.bash`, and
  `conftest.py`
- **AND** it SHALL mention `deps-subagent.bash` under `tests/_lib/`

#### Scenario: npm test runs both the bats and the pytest suites

- **WHEN** `package.json::scripts.test` is read
- **THEN** it SHALL invoke both `test:bats` and `test:python`
- **AND** `scripts.test:bats` SHALL use `--recursive`
- **AND** `USAGE.md` and `AGENTS.md` SHALL state that `npm test` runs the Python
  suite, and SHALL NOT claim that it skips it


### Requirement: general-add-env-cache-arch-discovery
The system SHALL persist auto-discovered third-party project artifact paths (ADR directory, roadmap path, architecture directory, ADR pattern) into `.env-cache.json` on first `rdd-env-check` run, and downstream consumers SHALL prefer this cache over the default convention.

#### Scenario: First run captures discovered paths
- **WHEN** `rdd-env-check` runs in a project with a custom ADR directory (e.g. `documentation/decisions`) and a non-default pattern (e.g. `RFC-*.md`)
- **AND** `.env-cache.json` does not exist (cache miss) or `cache.branch` differs from the current branch
- **THEN** env-check invokes `discover-arch-artifacts.sh::discover_all()`
- **AND** `.env-cache.json` records `discovered_adr_dir`, `discovered_roadmap_path`, `discovered_architecture_dir`, `discovered_adr_pattern`
- **AND** downstream consumers (`_read_arch_handoff_paths()` in `gate.py` and `detectors.py`) read the cache and use the discovered paths instead of hardcoded defaults

#### Scenario: Cache hit avoids re-scan
- **WHEN** `.env-cache.json` exists within TTL (3600s) and `cache.branch` matches `git branch --show-current`
- **THEN** env-check does NOT invoke `discover-arch-artifacts.sh` again
- **AND** consumers read `discovered_*` fields directly from cache

#### Scenario: Branch switch invalidates cache
- **WHEN** `cache.branch` differs from the current branch
- **THEN** env-check invalidates the existing cache
- **AND** runs `discover_all()` against the new branch state
- **AND** rewrites `.env-cache.json` with updated `branch` and `discovered_*` fields

#### Scenario: SKIP_AUTO_DISCOVERY opt-out preserves old behavior
- **WHEN** `SKIP_AUTO_DISCOVERY=yes` is set in the environment
- **THEN** env-check does NOT invoke `discover-arch-artifacts.sh`
- **AND** does NOT modify any `discovered_*` fields in cache
- **AND** prints `✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)` as visible confirmation

#### Scenario: Old 10-field cache files remain backward-compatible
- **WHEN** a pre-existing `.env-cache.json` (created before this change) lacks `discovered_*` fields
- **THEN** `_read_arch_handoff_paths()` returns the hardcoded default values for missing fields
- **AND** does NOT throw any exception
- **AND** behaves identically to the pre-change implementation for those fields

#### Scenario: Read-side fallback priority is env-cache > handoff > default
- **WHEN** `_read_arch_handoff_paths()` is called
- **THEN** it reads `discovered_adr_dir` (and 3 siblings) from `.env-cache.json` first
- **IF** any discovered field is absent or empty, it falls back to `.arch-handoff.json`
- **IF** handoff is also absent, it falls back to the hardcoded default (`docs/adr` / `roadmap.md` / `docs/architecture` / `ADR-*.md`)

#### Scenario: Discovery cache miss path is fast
- **WHEN** env-check runs in cold cache mode on a third-party project
- **THEN** the cache miss + discover + persist path completes in under 200ms
- **AND** does NOT invoke any `git` or `openspec` subprocess (pure filesystem walk)

