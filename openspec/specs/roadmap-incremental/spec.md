# roadmap-incremental Specification

## Purpose
TBD - created by archiving change move-populate-roadmap-into-guide-arch. Update Purpose after archive.
## Requirements
### Requirement: arch-done-roadmap-sync

The `guide-arch` skill SHALL automatically invoke the roadmap incremental update step before writing the arch-done handoff in Phase 6 (arch-done exit), eliminating the manual workflow break point between arch-done and roadmap regeneration.

#### Scenario: phase 6 auto-trigger
- **WHEN** `guide-arch` Phase 5 ( arch validation ) gate passes
- **AND** the user has not set `RDDF_ROADMAP_UPDATE=off`
- **THEN** Phase 6 SHALL execute the Roadmap Sync step before writing the arch-handoff
- **AND** the Roadmap Sync SHALL invoke `roadmap_incremental_update.sh --code-verify=on`
- **AND** the exit code SHALL propagate ( 0 = success, non-zero = sync failure )

#### Scenario: skip step via env var
- **WHEN** the user has set `RDDF_ROADMAP_UPDATE=off`
- **THEN** Phase 6 SHALL skip the Roadmap Sync step
- **AND** Phase 6 SHALL NOT write `.rddf/state/.populate-state.json`
- **AND** the exit code SHALL be 0

#### Scenario: gate semantic is warning-level
- **WHEN** the Roadmap Sync detects `last_generated_at < git HEAD timestamp`
- **THEN** the system SHALL write a warning entry to `.rddf/state/.arch-quality-report.json`
- **AND** the arch-done exit SHALL NOT be blocked (consistent with ADR-0018 / ADR-0007 warning-only philosophy)
- **AND** only `STRICT_ARCH_GATE=yes` SHALL escalate the warning to a blocking error

### Requirement: incremental-decision-matrix

The roadmap update SHALL determine its execution mode via a four-mode decision matrix based on the detected changes in ADR documents and code repository.

#### Scenario: skip mode (no changes)
- **WHEN** state file exists AND `state.codebase_commit == HEAD` AND all ADR file hashes are unchanged
- **THEN** the system SHALL execute `mode=skip`
- **AND** SHALL write `No changes detected` to stderr
- **AND** SHALL NOT rewrite any phase fragment file
- **AND** SHALL exit with code 0

#### Scenario: adr_only mode
- **WHEN** at least one ADR file hash has changed OR a new ADR has been added OR an ADR has been deleted
- **AND** no code files have changed since `state.codebase_commit`
- **THEN** the system SHALL execute `mode=adr_only`
- **AND** SHALL re-verify only the changed ADR set against the existing code (no fresh code scan)
- **AND** SHALL rewrite only the phase fragments whose input ADR set changed

#### Scenario: code_only mode
- **WHEN** no ADR file has changed
- **AND** `git diff <state.codebase_commit>..HEAD` yields changed code files
- **THEN** the system SHALL execute `mode=code_only`
- **AND** SHALL extract symbols from changed files via `rg`
- **AND** SHALL query the reverse index `state.reverse_index[symbol]` for affected ADRs
- **AND** SHALL re-verify only the affected ADRs
- **AND** SHALL preserve unchanged ADR verification records

#### Scenario: full mode (fallback)
- **WHEN** no state file exists OR schema version mismatches OR `git_commit_exists(state.codebase_commit) == false` OR `RDDF_CODEGRAPH_FINGERPRINT=stale` OR the user passes `--roadmap-update=force`
- **THEN** the system SHALL execute `mode=full`
- **AND** SHALL re-verify all ADRs from scratch
- **AND** SHALL rewrite all phase fragments
- **AND** SHALL rebuild the reverse index

### Requirement: state-file-schema-v2

The system SHALL persist incremental state in `.rddf/state/.populate-state.json` conforming to schema version 2.

#### Scenario: state structure
- **WHEN** the system writes state after a successful update
- **THEN** the file SHALL contain top-level fields: `version: 2`, `generated_at`, `codebase_commit`, `adrs[adr_id]`, `reverse_index[symbol]`, `phases[phase_id]`
- **AND** the `codegraph_fingerprint` field SHALL be optional

#### Scenario: write order safety
- **WHEN** the system completes an update
- **THEN** the system SHALL call `save_supplementary` (v1.1) BEFORE `save_populate_state` (v2)
- **AND** if a crash occurs between the two writes, the state SHALL be stale → next run reverts to `mode=full` (conservative)

#### Scenario: schema mismatch rejection
- **WHEN** an existing state file has `version != 2`
- **THEN** `load_populate_state_or_default` SHALL return `None`
- **AND** the system SHALL fallback to `mode=full`
- **AND** SHALL NOT corrupt or overwrite the legacy state file

#### Scenario: atomic write
- **WHEN** the system writes state
- **THEN** the write SHALL be atomic (tempfile + `os.replace`)
- **AND** a partial write SHALL NOT be observable by concurrent readers

### Requirement: codegraph-signal-via-env-var

The roadmap update SHALL consume the codegraph freshness signal via environment variable, not via in-process MCP calls.

#### Scenario: env var presence
- **WHEN** the agent side has set `RDDF_CODEGRAPH_FINGERPRINT=<fingerprint>` before invoking `roadmap_incremental_update.py`
- **THEN** the Python module SHALL read the env var only (no MCP calls)
- **AND** SHALL compare against the stored `state.codegraph_fingerprint`

#### Scenario: stale signal fallback
- **WHEN** `RDDF_CODEGRAPH_FINGERPRINT=stale`
- **THEN** `detect_code_changes` SHALL return `status=stale`
- **AND** the decision matrix SHALL escalate to `mode=full`
- **AND** stderr SHALL emit `⚠️  RDDF_CODEGRAPH_FINGERPRINT=stale, falling back to full verification`

#### Scenario: threshold configurability
- **WHEN** the user sets `RDDF_CODEGRAPH_STALE_DAYS=N`
- **THEN** the staleness threshold SHALL be N days (default: 7, `0` = never stale)

#### Scenario: missing env var
- **WHEN** `RDDF_CODEGRAPH_FINGERPRINT` is unset
- **THEN** the system SHALL treat codegraph signal as absent
- **AND** SHALL still attempt `mode=code_only` if git diff yields changes (rg-based symbol extraction)

### Requirement: shared-adr-catalog-module

The ADR metadata scanning logic SHALL live in `skills/_lib/adr_catalog.py` to eliminate cross-skill scripts dependency (ADR-0021).

#### Scenario: module extraction
- **WHEN** `populate_lib.py::catalog_sources` is called by any skill
- **THEN** the underlying scan logic SHALL execute via `from _lib.adr_catalog import scan_adr_catalog`
- **AND** the function signature SHALL remain backward-compatible

#### Scenario: file_hash stability
- **WHEN** an ADR file content is unchanged
- **THEN** `scan_adr_catalog` SHALL return the same `file_hash` (sha256) as on a previous call
- **AND** `detect_adr_changes` SHALL NOT flag the ADR as changed

### Requirement: thin-wrapper-standalone-skill

The `populate-roadmap-from-arch` skill SHALL be preserved as a thin wrapper at version 1.2 to maintain backward compatibility with v1.1 users.

#### Scenario: deprecation banner
- **WHEN** a user invokes `skill_use("populate-roadmap-from-arch")` after v2.2 ships
- **THEN** the skill SHALL display a deprecation banner pointing to `guide-arch` Phase 6 as the preferred entry point
- **AND** SHALL still execute the same functionality via the new `roadmap_incremental_update.sh`

#### Scenario: --standalone flag
- **WHEN** the user passes `--standalone` to `populate-roadmap-from-arch/scripts/populate.sh`
- **THEN** the script SHALL bypass guide-arch and execute the update directly
- **AND** SHALL preserve all CLI flags (`--code-verify`, `--incremental`, `--roadmap-update`, etc.)

### Requirement: per-worktree-state-isolation

State files SHALL be isolated per working directory, eliminating concurrent write conflicts between worktrees.

#### Scenario: worktree first run
- **WHEN** the user invokes Roadmap Sync inside a new worktree
- **AND** `.rddf/state/.populate-state.json` does not exist in that worktree
- **THEN** the system SHALL execute `mode=full`
- **AND** SHALL exit with code 0 after writing the worktree-local state

#### Scenario: cross-worktree state isolation
- **WHEN** the user switches between worktrees
- **THEN** each worktree SHALL have its own `.rddf/state/.populate-state.json`
- **AND** the system SHALL NOT read or write another worktree's state
- **AND** the first run after switching SHALL be `mode=full` (no state carry-over)

### Requirement: git-history-edge-cases

The incremental update SHALL handle rebase / cherry-pick / merge commit / force-push scenarios without crashing.

#### Scenario: force-push ref missing
- **WHEN** `git_commit_exists(state.codebase_commit) == false` (force-push / branch reset / GC)
- **THEN** the system SHALL fallback to `mode=full`
- **AND** SHALL emit a stderr warning
- **AND** SHALL exit with code 0

#### Scenario: rebase after state
- **WHEN** the user rebases commits on top of `state.codebase_commit`
- **AND** the original commit object still exists (within reflog / GC window)
- **THEN** the system SHALL execute `mode=code_only` or `mode=full` (depending on diff size)
- **AND** SHALL exit with code 0
- **AND** SHALL update `state.codebase_commit` to the new HEAD

#### Scenario: merge commit
- **WHEN** the user merges a branch that includes N commits touching M symbols
- **THEN** the system SHALL detect M changed symbols
- **AND** SHALL re-verify all ADRs referencing any of those symbols (potentially more than strictly needed; conservative correctness)

### Requirement: reset-command

The system SHALL provide a one-line reset path for users to discard stale state.

#### Scenario: manual reset
- **WHEN** the user runs `rm .rddf/state/.populate-state.json`
- **THEN** the next Roadmap Sync SHALL behave as if no state exists (`mode=full`)

#### Scenario: documentation reference
- **WHEN** the user reads `AGENTS.md` 常见陷阱 section OR `populate-roadmap-from-arch/SKILL.md` troubleshooting
- **THEN** the reset command SHALL be documented with the format `rm .rddf/state/.populate-state.json`
- **AND** the consequence (full re-run) SHALL be explained

