## ADDED Requirements

### Requirement: rdd-quick skill exists with ADR-0028 role boundaries
A new skill MUST exist at `skills/rdd-quick/SKILL.md` with complete frontmatter (`name`, `description`, `license`, `compatibility`, `metadata`, `role`) where `role.boundaries` declares ownership of the quick-path artifacts and explicitly disclaims all four-stage artifacts.

#### Scenario: frontmatter declares required role fields
- **WHEN** `skills/rdd-quick/SKILL.md` frontmatter is parsed
- **THEN** `role.title` MUST be present
- **AND** `role.perspective` MUST be present
- **AND** `role.boundaries.human_involvement` MUST be present

#### Scenario: role.boundaries.owns lists quick-path artifacts
- **WHEN** `role.boundaries.owns` is read
- **THEN** it MUST contain `.rddf/plans/quick-*.md`
- **AND** it MUST contain `.rddf/state/.quick-history.jsonl`

#### Scenario: role.boundaries.not_owns disclaims four-stage artifacts
- **WHEN** `role.boundaries.not_owns` is read
- **THEN** it MUST contain `openspec/changes/<name>/`
- **AND** it MUST contain `.rddf/wt/<name>/`
- **AND** it MUST contain `docs/adr/ADR-*.md`
- **AND** it MUST contain `.rddf/state/iteration.json`

### Requirement: SKILL.md documents a P0-P4 five-phase state machine
The skill MUST document five phases: P0 (plan generation), P1 (complexity triage), P2 (in-place execution), P3 (AC verification), P4 (retry / escalation).

#### Scenario: all five phases are documented
- **WHEN** `skills/rdd-quick/SKILL.md` body is read
- **THEN** it MUST contain phase markers for P0, P1, P2, P3 and P4
- **AND** each phase MUST state its entry condition and its output

#### Scenario: complexity triage principles are enumerated
- **WHEN** the P1 section is read
- **THEN** it MUST list at least 4 signals indicating a change is complex
- **AND** it MUST list at least 4 signals indicating a change is simple
- **AND** it MUST NOT specify a hardcoded numeric threshold for file count or task count

#### Scenario: Metis and Oracle review is a prose spawn instruction
- **WHEN** the P1 complex branch is read
- **THEN** it MUST instruct the executing AI agent to spawn Metis for ambiguity review
- **AND** it MUST instruct the executing AI agent to spawn Oracle for approach review
- **AND** it MUST require user confirmation before proceeding to P2

### Requirement: quick plan file carries TDD 5-step markers and an Acceptance section
The generated plan file MUST live at `.rddf/plans/quick-<name>.md` and MUST satisfy the existing `plan_tdd_check.py` contract plus carry its own AC source.

#### Scenario: plan file path uses the quick- prefix
- **WHEN** a quick plan is generated for name `foo`
- **THEN** the file MUST be written to `.rddf/plans/quick-foo.md`
- **AND** an existing `.rddf/plans/foo.md` MUST NOT be read or modified

#### Scenario: plan file contains all five TDD markers
- **WHEN** the generated plan file is read
- **THEN** it MUST contain `Write the failing test`
- **AND** it MUST contain `Run test to verify it fails`
- **AND** it MUST contain `Write minimal implementation`
- **AND** it MUST contain `Run test to verify it passes`
- **AND** it MUST contain `Defer commit`

#### Scenario: rdd-doctor plan-tdd check reports no warning
- **WHEN** `bash skills/rdd-doctor/scripts/doctor.sh --category plan-tdd` is run after generating a quick plan
- **THEN** the output MUST NOT contain a `plan-tdd` WARNING referencing the generated `quick-*.md` file

#### Scenario: plan file carries an Acceptance section
- **WHEN** the generated plan file is read
- **THEN** it MUST contain a `## Acceptance` heading
- **AND** that section MUST contain at least 1 checkbox line matching `- [ ]`

### Requirement: P3 verification reuses the rdd-verifier verdict contract
Verification MUST emit a verdict array whose item fields match `rdd-verifier`'s `VERDICT_ITEM_SCHEMA`, with acceptance criteria sourced from the plan file rather than from `proposal.md`.

#### Scenario: verdict item fields match the verifier schema
- **WHEN** the P3 verdict format is documented in SKILL.md
- **THEN** each verdict item MUST declare fields `ac_id`, `description`, `status`, `confidence`, `evidence` and `reasoning`
- **AND** `status` MUST be constrained to `pass`, `fail` or `partial`

#### Scenario: AC source is the plan file Acceptance section
- **WHEN** the P3 section is read
- **THEN** it MUST state that acceptance criteria are extracted from the plan file `## Acceptance` section
- **AND** it MUST NOT read `openspec/changes/<name>/proposal.md`

### Requirement: retry is bounded and escalation is guidance-only
Verification failure MUST retry at most 3 times, and on exhaustion MUST emit an upgrade summary to stdout without creating any openspec change.

#### Scenario: retry ceiling defaults to 3
- **WHEN** the P4 section is read
- **THEN** it MUST state a retry ceiling of 3
- **AND** it MUST document `RDDF_QUICK_MAX_RETRIES` as the override variable

#### Scenario: escalation emits a summary without writing a change
- **WHEN** the retry ceiling is reached
- **THEN** the upgrade summary MUST include the original proposal text, a `git diff --stat` of changes made, each failing AC with its verdict reasoning, and a `skill_use("rdd-planner")` next-step prompt
- **AND** no file under `openspec/changes/` MUST be created
- **AND** the audit log entry `outcome` MUST be `escalated`

### Requirement: quick history audit log is append-only with a versioned schema
Each execution MUST append exactly one JSONL line to `.rddf/state/.quick-history.jsonl`, validated against a versioned schema and written atomically.

#### Scenario: schema file exists at version 1
- **WHEN** `_lib/schemas/quick_history_schema.json` is read
- **THEN** it MUST declare version 1

#### Scenario: audit entry carries all eleven fields
- **WHEN** an audit entry is appended
- **THEN** it MUST contain `name`, `started_at`, `ended_at`, `plan_file`, `complexity`, `reviewed_by`, `verdict_summary`, `retry_count`, `outcome`, `commit_sha` and `upgraded_to_change`

#### Scenario: outcome vocabulary is constrained
- **WHEN** the `outcome` field is validated
- **THEN** the accepted values MUST be `completed`, `escalated` and `unverified`

#### Scenario: append is atomic and additive
- **WHEN** a second execution appends an entry to an existing log
- **THEN** the previously written line MUST remain byte-identical
- **AND** the write MUST use a temp-file-plus-rename sequence

### Requirement: zero pollution of the four-stage path
The implementation MUST be additive only — it MUST NOT modify the execute, archive or planner contracts, and MUST NOT write four-stage state files.

#### Scenario: untouched scripts keep their content hash
- **WHEN** the change is complete
- **THEN** `skills/execute/scripts/select_worktree.sh` MUST have an unchanged content hash
- **AND** `skills/execute/scripts/tasks_writeback.sh` MUST have an unchanged content hash
- **AND** `_lib/archive.sh` MUST have an unchanged content hash

#### Scenario: rdd-planner role section is byte-identical
- **WHEN** `skills/rdd-planner/SKILL.md` is diffed against its pre-change version
- **THEN** the only added line MUST be within the `## See also` section
- **AND** the `role:` frontmatter block MUST be byte-identical

#### Scenario: four-stage state files are not written
- **WHEN** a full rdd-quick run completes
- **THEN** `.rddf/state/iteration.json` MUST be unchanged
- **AND** `.rddf/state/sessions.json` MUST be unchanged
- **AND** `.rddf/state/roadmap-state.json` MUST be unchanged
- **AND** no directory under `.rddf/wt/` MUST be created
- **AND** no file under `openspec/changes/` or `openspec/specs/` MUST be created

#### Scenario: environment variables use a reserved prefix
- **WHEN** rdd-quick environment variables are documented
- **THEN** every variable MUST start with `RDDF_QUICK_` or be `SKIP_RDDF_QUICK_VERIFY`
- **AND** `QUICK_FINISH_DETECTED` MUST NOT be read or written
- **AND** `SKIP_PROMETHEUS_PLANNING` MUST NOT be read or written

### Requirement: documentation records the decision and disambiguates existing concepts
A new ADR plus AGENTS.md and README updates MUST distinguish rdd-quick from the three pre-existing "light" concepts and from the unapproved guide-ship-quick-finish proposal.

#### Scenario: ADR is created with the next sequential number
- **WHEN** `docs/adr/` is listed
- **THEN** a file matching `ADR-0047-*.md` MUST exist
- **AND** its status MUST be `已采纳`

#### Scenario: ADR contains a four-concept disambiguation table
- **WHEN** the ADR body is read
- **THEN** it MUST distinguish rdd-quick from `execution_mode: lightweight`
- **AND** from `git.openspec_tracked: false`
- **AND** from the serial/parallel execution mode
- **AND** it MUST state the boundary against the `guide-ship-quick-finish` proposal

#### Scenario: AGENTS.md and README are updated
- **WHEN** `AGENTS.md` is read
- **THEN** it MUST contain an rdd-quick section listing the reserved environment variables
- **WHEN** `README.md` skill list is read
- **THEN** it MUST contain a `rdd-quick/SKILL.md` entry
