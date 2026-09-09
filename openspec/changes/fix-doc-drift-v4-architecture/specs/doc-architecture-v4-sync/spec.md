## ADDED Requirements

### Requirement: user-facing-docs-reflect-v4-four-stage

The rdd-workflow repository's user-facing documentation (`README.md`, `USAGE.md`, `AGENTS.md` banner sections, `CHANGELOG.md` `[Unreleased]` section) MUST describe the architecture as a v4 four-stage pipeline (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`) plus a `rdd-quick` small-change bypass path, per ADR-0043 / ADR-0044 / ADR-0047. Documentation MUST NOT contain references to a five-phase model (`arch → design → plan → ship → verify`) or to deprecated skill names (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`, `guide-spec`).

#### Scenario: README.md "使用流程" sublist uses 4 stage skills + 1 bypass

- **WHEN** a new user reads `README.md` lines 57-72 ("使用流程" sublist)
- **THEN** the sublist shows exactly 4 stage skill entries (Arch / Planner / Builder / Verifier) and 1 bypass entry (Quick)
- **AND** the 4 stage entries map to `rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier` in that order
- **AND** the Quick entry maps to `rdd-quick` with a brief description noting it bypasses `openspec change` and `worktree`
- **AND** no entry in the sublist uses a `guide-*` skill name

#### Scenario: README.md "v4.0+ 当前架构" section uses four-stage vocabulary

- **WHEN** a reader scans `README.md` for the architecture description (around the former "v3.0 新特性" section, now renamed "v4.0+ 当前架构")
- **THEN** the H3 header reads "v4.0+ 当前架构" (or equivalent) and explicitly says "四阶段" or "4 阶段"
- **AND** the phase table has exactly 4 rows (Arch / Planner / Builder / Verifier) — 0 rows for the old "Design" or "Plan" standalone phases
- **AND** the skill chain in the section reads `rdd-arch → rdd-planner → rdd-builder → rdd-verifier` (4 links, no 5th)

#### Scenario: README.md directory tree includes rdd-planner and rdd-quick

- **WHEN** a reader scans the directory tree in `README.md` (around L395-430)
- **THEN** `rdd-planner/SKILL.md` is present as a tree entry
- **AND** `rdd-quick/SKILL.md` is present as a tree entry
- **AND** `rdd-builder/SKILL.md` appears at most once (not 3× as in the pre-patch tree)

#### Scenario: USAGE.md H2 phase architecture header is four-stage

- **WHEN** `USAGE.md` is read for the architecture overview (around the H2 "核心概念" / phase architecture table)
- **THEN** the H2/H3 header explicitly says "四阶段架构 (rdd-arch → rdd-planner → rdd-builder → rdd-verifier, v4.0+ per ADR-0043)" or equivalent
- **AND** the phase responsibility table has distinct rows for `rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`
- **AND** the state-file writer column (L60-75) references `rdd-planner` and `rdd-builder` (not `guide-plan` and `guide-ship`)

### Requirement: architectural-docs-no-deprecated-guide-star-skill-names

The rdd-workflow repository's architectural documentation (`docs/architecture/{overview,workflow-phases,README}.md`) MUST NOT reference the deprecated `guide-arch`, `guide-design`, `guide-plan`, `guide-ship`, or `guide-spec` skill names in any non-historical context (i.e., as the canonical entry skill of a stage).

#### Scenario: overview.md phase guides table uses rdd-* skill names

- **WHEN** a reader consults `docs/architecture/overview.md` for the phase skill mapping
- **THEN** the phase guides table (around L60-75) lists exactly 5 rows: `rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`, `rdd-quick`
- **AND** zero rows reference `guide-arch`, `guide-design`, `guide-plan`, or `guide-ship`
- **AND** the bypass row (`rdd-quick`) carries a 1-line description noting it bypasses `openspec change` and `worktree` per ADR-0047

#### Scenario: workflow-phases.md mermaid diagram has 4 stage nodes + 1 bypass

- **WHEN** `docs/architecture/workflow-phases.md` is rendered (e.g., on GitHub or in a local preview)
- **THEN** the mermaid diagram has exactly 4 main stage nodes (arch, planner, builder, verifier)
- **AND** a bypass edge or sub-node labeled `rdd-quick` connects to the entry of the pipeline
- **AND** no node is labeled `design` or `plan` (these are merged into `planner` and `builder` respectively in v4)

#### Scenario: workflow-phases.md per-stage Entry skill column uses rdd-* names

- **WHEN** a reader consults the per-stage detail sections in `docs/architecture/workflow-phases.md` (around L20-127)
- **THEN** every "Entry skill" reference uses an `rdd-*` name
- **AND** the Stage 2 (planner) Entry skill is `rdd-planner` (not `guide-design` from the v3 5-phase model)
- **AND** the Stage 3 (builder) Entry skill is `rdd-builder` (not `guide-plan` or `guide-ship`)
- **AND** the Stage 4 (verifier) Entry skill is `rdd-verifier` (unchanged from v3)

#### Scenario: workflow-phases.md state-file path matches rdd-verifier canonical

- **WHEN** a developer wiring up rdd-verifier integration consults `docs/architecture/workflow-phases.md` for the state file path
- **THEN** the path cited for the per-change loop state is `.rddf/state/verifier/<change>.json` (canonical per `rdd-verifier/SKILL.md` "State Files Owned" table)
- **AND** the deprecated path `.rdd/state/.rdd-verifier-state.json` is NOT cited in any non-historical context

#### Scenario: workflow-phases.md does not reference deprecated ac-verifier

- **WHEN** a reader consults `docs/architecture/workflow-phases.md` for the verify sub-skill reference
- **THEN** the only sub-skill cited is `rdd-verifier` (which self-contains LLM verification per ADR-0045)
- **AND** `ac-verifier` is NOT cited as a sub-skill of the verify stage

### Requirement: architecture-overview-inverted-rule-corrected

The architectural rule in `docs/architecture/overview.md` (around L123) about phase count MUST correctly state that v4 is a four-stage architecture, NOT assert that "four stages" is stale.

#### Scenario: overview.md L123 rule explicitly cites v4 as four-stage

- **WHEN** a maintainer consults the "Why Five Phases, Not Three" section of `docs/architecture/overview.md` (around L115-127, renamed in v4 to "Why Four Stages")
- **THEN** the section title says "Why Four Stages" (or equivalent) and the rule text reads: "any doc that still says 'three phases' (the v2.0 model) or 'five phases' (the v3.0 model) is stale; v4 is four stages per ADR-0043"
- **AND** zero occurrences of the inverted rule "any doc that still says 'three phases' or 'four phases' is stale" remain in `docs/architecture/overview.md`

### Requirement: rdd-arch-skill-md-rename-history-bug-fixed

The `skills/rdd-arch/SKILL.md` frontmatter-aware intro block (around L34) MUST correctly state the rename history: from `guide-arch` to `rdd-arch`, not a self-reference to `rdd-arch → rdd-arch`.

#### Scenario: rdd-arch/SKILL.md L34 says "from guide-arch to rdd-arch"

- **WHEN** a reader consults the "Stage 3 (2026-09-03)" intro paragraph in `skills/rdd-arch/SKILL.md` (around L34)
- **THEN** the line reads "此 skill 从 `guide-arch` 重命名为 `rdd-arch`（per D1a 渐进策略）" or equivalent
- **AND** the line does NOT read "此 skill 从 `rdd-arch` 重命名为 `rdd-arch`" (the self-reference bug)

### Requirement: rdd-arch-skill-md-describes-v4-four-stage

The `skills/rdd-arch/SKILL.md` architecture overview sections (L40, L64-69, L74-80) MUST describe the v4 four-stage model with the `rdd-quick` bypass, not the v3 5-stage model.

#### Scenario: rdd-arch/SKILL.md L40 says "四阶段架构"

- **WHEN** a reader consults the "本技能是 rdd-workflow 工作流" intro paragraph in `skills/rdd-arch/SKILL.md` (around L40)
- **THEN** the paragraph explicitly says "四阶段架构" (four-stage architecture)
- **AND** references the v4 model with "v4.0+, per ADR-0043/0044" or equivalent
- **AND** does NOT say "五阶段架构" (five-phase architecture)

#### Scenario: rdd-arch/SKILL.md sub-skill table has 4 stage rows + 1 bypass

- **WHEN** a reader consults the sub-skill table in `skills/rdd-arch/SKILL.md` (around L64-69)
- **THEN** the table has exactly 5 rows: 4 stage rows (`rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`) and 1 bypass row (`rdd-quick`)
- **AND** zero rows reference `guide-design`, `guide-plan`, or `guide-ship`

#### Scenario: rdd-arch/SKILL.md workflow diagram has 4 stages + 1 bypass

- **WHEN** the workflow ASCII diagram in `skills/rdd-arch/SKILL.md` (around L74-80) is rendered
- **THEN** the diagram shows 4 stage boxes in order (`arch 端` → `planner 端` → `builder 端` → `verifier 端`)
- **AND** a bypass arrow labeled `rdd-quick` is shown
- **AND** the diagram does NOT show 5 stage boxes (the v3 `design` + `plan` standalone boxes are merged)

### Requirement: skills-directory-has-5-rdd-stage-skills-and-0-guide-star-skill-subdirs

The `skills/` directory on disk MUST contain exactly 5 `rdd-*` skill subdirectories (`rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`, `rdd-quick`) and ZERO `guide-*` skill subdirectories (excluding `guide/` which is the standalone recommender skill, not a stage).

#### Scenario: skills/ disk layout matches the 5-stage + 1-bypass model

- **WHEN** the doc-contract test enumerates `skills/*/` directories
- **THEN** the set `{"rdd-arch", "rdd-planner", "rdd-builder", "rdd-verifier", "rdd-quick"}` is present (5 entries)
- **AND** no entry named `guide-arch`, `guide-design`, `guide-plan`, `guide-ship`, or `guide-spec` is present
- **AND** the entry `guide` is present (this is the standalone recommender, not a stage)

### Requirement: doc-contract-test-locks-v4-state

A new doc-contract test (`tests/integration/test_v4_doc_drift_contracts.bats`) MUST be present, contain exactly 10 test cases covering each drift site from the audit, and exhibit the "fails on pre-patch / passes on post-patch" property.

#### Scenario: doc-contract test passes on post-patch tree

- **WHEN** `./test.sh --bats tests/integration/test_v4_doc_drift_contracts.bats` is run against the post-patch tree
- **THEN** all 10 test cases pass
- **AND** total runtime is under 5 seconds (pure grep assertions, no I/O bound)

#### Scenario: doc-contract test fails on pre-patch tree

- **WHEN** `./test.sh --bats tests/integration/test_v4_doc_drift_contracts.bats` is run against the pre-patch tree (e.g., after `git stash` of the Phase A + B commits)
- **THEN** at least 8 of 10 test cases fail (the 2 exceptions are cases 8 and 9 which test path/file existence, which may already be correct pre-patch)
- **AND** the test output names each failing case and the specific grep pattern that did not match

#### Scenario: doc-contract test runs in CI

- **WHEN** the standard CI workflow (`.github/workflows/test.yml`) runs the bats recursive step
- **THEN** the new test file is included in the recursive invocation
- **AND** any regression to a v3 5-phase description OR any reintroduction of a `guide-*` skill name in the cited files causes the CI step to fail
