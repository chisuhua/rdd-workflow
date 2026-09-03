## ADDED Requirements

### Requirement: schema-strict-validation

The `_lib/schemas/config_schema.json` SHALL define `project`, `adr`, `git`, and `verification` sections with strict type validation (additionalProperties: false), and `ConfigParser.parse()` SHALL raise `ConfigError` when project.yaml contains fields violating these schemas.

#### Scenario: invalid openspec_tracked type
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: "yes"}` (string instead of boolean)
- **THEN** `ConfigParser.parse()` SHALL raise `ConfigError`
- **AND** the error message SHALL mention `git.openspec_tracked`

#### Scenario: invalid verification.provider enum
- **WHEN** `.rddf/project.yaml` contains `verification: {provider: foo}`
- **THEN** `ConfigParser.parse()` SHALL raise `ConfigError`
- **AND** the error message SHALL mention `verification.provider`

#### Scenario: unknown adr subfield rejected
- **WHEN** `.rddf/project.yaml` contains `adr: {unknown_field: bar}`
- **THEN** `ConfigParser.parse()` SHALL raise `ConfigError`
- **AND** the error message SHALL mention `unknown_field`

#### Scenario: missing project.yaml no schema validation
- **WHEN** `.rddf/project.yaml` does not exist
- **THEN** `ConfigParser.parse()` SHALL succeed without schema validation for project/adr/git/verification sections

### Requirement: defaults-project-present

The `_lib/core/defaults.py::DEFAULTS` dictionary SHALL include a `project` key (empty dict or with subfield defaults) so `get_defaults()['project']` is a dict, ensuring structural consistency when project.yaml is absent.

#### Scenario: project key in DEFAULTS
- **WHEN** `from _lib.core.defaults import get_defaults; cfg = get_defaults()`
- **THEN** `cfg['project']` SHALL be a `dict`
- **AND** `cfg['project']` SHALL be safe to mutate (deep copy semantics)

### Requirement: schema-root-level-extras-allowed

The `_lib/schemas/config_schema.json` SHALL keep root-level `additionalProperties: true` (default) so users may add custom root-level keys in `.rddf/project.yaml` without breaking schema validation, while the 4 new sections (`project`/`adr`/`git`/`verification`) enforce `additionalProperties: false` for their internal contents.

#### Scenario: root-level custom keys allowed
- **WHEN** `.rddf/project.yaml` contains `my_custom_tooling: {x: 1}` at root level (alongside `project` / `adr` / etc.)
- **THEN** `ConfigParser.parse()` SHALL succeed without raising `ConfigError`
- **AND** the merged config SHALL retain `my_custom_tooling` as-is

#### Scenario: new section strict on internal contents
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false, extra_field: bar}`
- **THEN** `ConfigParser.parse()` SHALL raise `ConfigError`
- **AND** the error message SHALL mention `git.extra_field`

### Requirement: verifier-explicit-runner-override

The `_lib/cli/rdd_verify_cmd.py::cmd_rdd_verify(args, runner=None)` SHALL treat an explicit `runner` argument as authoritative, overriding any `verification.provider` auto-detection from `.rddf/project.yaml`. Provider detection SHALL apply only when `runner is None`.

#### Scenario: explicit runner wins over provider
- **WHEN** `cmd_rdd_verify(args, runner=mock_runner)` is called with explicit runner
- **AND** `.rddf/project.yaml` contains `verification: {provider: hook}`
- **THEN** `mock_runner` SHALL be invoked for each change
- **AND** `_hook_runner` SHALL NOT be invoked (explicit wins)

#### Scenario: provider detected when no explicit runner
- **WHEN** `cmd_rdd_verify(args)` is called (no runner argument, defaults to None)
- **AND** `.rddf/project.yaml` contains `verification: {provider: hook}`
- **THEN** `_hook_runner` SHALL be invoked for each change

#### Scenario: default runner when no provider and no explicit runner
- **WHEN** `cmd_rdd_verify(args)` is called
- **AND** `.rddf/project.yaml` does not exist OR lacks `verification.provider`
- **THEN** `_default_runner` SHALL be invoked (existing ac-verifier behavior)

### Requirement: arch-handoff-adr-pattern-fallback

The `populate_lib.py::catalog_sources()` SHALL resolve `adr_pattern` with priority `explicit arg > .rddf/state/.arch-handoff.json adr_pattern field > .rddf/project.yaml adr.pattern direct read > 4-digit default`. The direct project.yaml read SHALL apply when the arch-handoff file is missing, lacks `adr_pattern` field, OR the file is corrupted/unreadable.

#### Scenario: arch-handoff adr_pattern present
- **WHEN** `.rddf/state/.arch-handoff.json` exists with `adr_pattern: "^ADR-(\\d{3})-.*\\.md$"`
- **AND** `catalog_sources(project_root=...)` is called without explicit `adr_pattern`
- **THEN** `catalog_sources` SHALL use `^ADR-(\\d{3})-.*\\.md$` (from handoff)

#### Scenario: arch-handoff exists but missing adr_pattern field
- **WHEN** `.rddf/state/.arch-handoff.json` exists without `adr_pattern` field
- **AND** `.rddf/project.yaml` contains `adr: {pattern: "^ADR-(\\d{3})-.*\\.md$"}`
- **AND** `catalog_sources(project_root=...)` is called without explicit `adr_pattern`
- **THEN** `catalog_sources` SHALL fall back to `.rddf/project.yaml` `adr.pattern`
- **AND** SHALL use `^ADR-(\\d{3})-.*\\.md$` (from project.yaml)

#### Scenario: arch-handoff missing
- **WHEN** `.rddf/state/.arch-handoff.json` does not exist
- **AND** `.rddf/project.yaml` contains `adr: {pattern: "^ADR-(\\d{3})-.*\\.md$"}`
- **AND** `catalog_sources(project_root=...)` is called without explicit `adr_pattern`
- **THEN** `catalog_sources` SHALL fall back to `.rddf/project.yaml` `adr.pattern`

#### Scenario: arch-handoff corrupted
- **WHEN** `.rddf/state/.arch-handoff.json` exists but contains invalid JSON
- **AND** `.rddf/project.yaml` contains `adr: {pattern: ...}`
- **THEN** `catalog_sources` SHALL NOT raise (graceful fallback)
- **AND** SHALL fall back to `.rddf/project.yaml` `adr.pattern`

#### Scenario: no handoff and no project.yaml
- **WHEN** neither arch-handoff nor project.yaml provides `adr_pattern`
- **THEN** `catalog_sources` SHALL use 4-digit default `^ADR-(\\d{4})-.*\\.md$`

### Requirement: arch-handoff-schema-v2-adr-pattern

The `_lib/schemas/arch_handoff_schema.json` SHALL bump from `version: 1` to `version: 2` and include a new optional `adr_pattern` field (type: string) under `properties`, allowing the arch-handoff to carry the project-level adr pattern.

#### Scenario: v2 schema accepts adr_pattern
- **WHEN** `arch_handoff_schema["version"]` is read
- **THEN** `version` SHALL equal `2`
- **AND** `properties.adr_pattern` SHALL exist with `type: string`

#### Scenario: v1 handoff backward compat
- **WHEN** an existing v1 arch-handoff file (without `adr_pattern` field) is loaded
- **THEN** `catalog_sources` SHALL treat `adr_pattern` as None
- **AND** SHALL fall back to `.rddf/project.yaml` direct read (per `arch-handoff-adr-pattern-fallback`)

#### Scenario: write_arch_handoff includes adr_pattern
- **WHEN** `write_arch_handoff()` is called
- **AND** `.rddf/project.yaml` contains `adr: {pattern: "^ADR-(\\d{3})-.*\\.md$"}`
- **THEN** the written arch-handoff SHALL contain `adr_pattern: "^ADR-(\\d{3})-.*\\.md$"` field

### Requirement: rddf-execution-mode-env-not-read-by-parse

The `_lib/ship_execution_mode.sh::parse_execution_mode()` SHALL NOT read `RDDF_EXECUTION_MODE` environment variable. The env var (when set by `guide-ship` Phase 1) is a downstream signal only.

#### Scenario: parse_execution_mode ignores RDDF_EXECUTION_MODE
- **WHEN** `RDDF_EXECUTION_MODE=parallel` is set in environment
- **AND** `RDD_SHIP_PARALLEL` is unset
- **AND** `.rddf/project.yaml` does not exist
- **AND** no CLI flag is passed
- **THEN** `parse_execution_mode` SHALL return "serial" (default, NOT "parallel")

#### Scenario: parse_execution_mode reads project.yaml directly
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** no CLI flag is passed
- **THEN** `parse_execution_mode` SHALL return "serial" (project.yaml direct read, independent of RDDF_EXECUTION_MODE env var)

#### Scenario: Phase 1 sets env var as output
- **WHEN** `guide-ship` Phase 1 detects `git.openspec_tracked: false`
- **THEN** Phase 1 SHALL `export RDDF_EXECUTION_MODE=serial` for downstream tools
- **AND** the env var SHALL NOT be read by `parse_execution_mode` (per Decision 9)

### Requirement: verifier-hook-provider-routing

The `rddf rdd-verify` subcommand SHALL detect `.rddf/project.yaml` `verification.provider` field and route to `_lib/verifier/hook_runner.py::run_verification_hook()` when set to `hook`, replacing the default LLM-based verifier runner.

#### Scenario: provider=hook routes to _hook_runner
- **WHEN** `.rddf/project.yaml` contains `verification: {provider: hook}`
- **AND** `rddf rdd-verify <change>` is invoked
- **THEN** the system SHALL call `_hook_runner(change_name, project_root)`
- **AND** `_hook_runner` SHALL invoke `run_verification_hook(change_name, project_root)`
- **AND** `run_verification_hook` SHALL execute `{project_root}/tools/verify_change.sh <change>`

#### Scenario: hook exit 0 maps to passed
- **WHEN** the hook script exits with code 0
- **THEN** `_hook_runner` SHALL return `{"exit_code": 0, "verdict": [{"ac_id": "hook-<change>", "status": "pass"}], "failed_acs": []}`
- **AND** `rddf rdd-verify` SHALL exit with code 0 (aggregate passed)

#### Scenario: hook exit 1 maps to failed
- **WHEN** the hook script exits with code 1
- **THEN** `_hook_runner` SHALL return `{"exit_code": 1, "verdict": [{"ac_id": "hook-<change>", "status": "fail"}], "failed_acs": ["hook-<change>"]}`
- **AND** `rddf rdd-verify` SHALL exit with code 1 (aggregate failed)

#### Scenario: hook exit 2+ or timeout maps to error
- **WHEN** the hook script exits with code 2 or higher, OR exceeds 300-second timeout
- **THEN** `_hook_runner` SHALL return `{"exit_code": 3, "error": "..."}`
- **AND** `rddf rdd-verify` SHALL exit with code 3 (aggregate error)

#### Scenario: hook missing returns skipped
- **WHEN** `{project_root}/tools/verify_change.sh` does not exist
- **THEN** `_hook_runner` SHALL return `{"exit_code": 0, "note": "hook script missing", ...}`
- **AND** `rddf rdd-verify` SHALL exit with code 0 (skipped = pass for backward compatibility)

#### Scenario: hook path outside tools/ rejected
- **WHEN** the hook script resolves to a path outside `{project_root}/tools/`
- **THEN** `_hook_runner` SHALL raise `HookPathError`
- **AND** `rddf rdd-verify` SHALL exit with code 3 (error)

#### Scenario: default provider is llm
- **WHEN** `.rddf/project.yaml` does not exist OR does not contain `verification.provider`
- **THEN** the system SHALL default to `provider="llm"`
- **AND** SHALL invoke `_default_runner` (existing ac-verifier behavior)

### Requirement: verifier-cache-hook-key

The `_lib/verifier/cache.py::cache_key()` function SHALL accept `provider` and `hook_path` parameters, producing distinct cache keys for `provider="hook"` vs `provider="llm"` to prevent cross-provider cache poisoning.

#### Scenario: cache key differs between providers
- **WHEN** `cache_key("c", root, provider="llm")` and `cache_key("c", root, provider="hook", hook_path=...)` are computed
- **THEN** the two keys SHALL be different SHA256 hex digests

#### Scenario: cache key stable across calls for same hook
- **WHEN** `cache_key("c", root, provider="hook", hook_path=path)` is called twice with same arguments
- **THEN** the two calls SHALL return identical SHA256 hex digests

#### Scenario: default cache_key backward compat
- **WHEN** `cache_key("c", root)` is called without provider argument
- **THEN** the function SHALL default to `provider="llm"`
- **AND** the cache key SHALL match the pre-change behavior (existing tests pass)

### Requirement: guide-ship-phase-1-detect-lightweight

The `skills/guide-ship/SKILL.md` Phase 1 SHALL include Step 1.5 that reads `.rddf/project.yaml` `git.openspec_tracked` field BEFORE worktree creation (Step 2), and force lightweight mode when set to `false`.

#### Scenario: openspec_tracked=false triggers lightweight
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** the user invokes `skill_use("guide-ship")`
- **THEN** Phase 1 Step 1.5 SHALL print "⚡ 强制轻量模式 (openspec_tracked=false, branch only, no worktree)"
- **AND** SHALL set `RDDF_EXECUTION_MODE=lightweight` environment variable
- **AND** subsequent worktree creation (Step 2) SHALL be skipped
- **AND** the system SHALL proceed directly to lightweight branch execution

#### Scenario: openspec_tracked=true (default) preserves current behavior
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: true}` OR does not exist
- **THEN** Phase 1 Step 1.5 SHALL NOT modify `RDDF_EXECUTION_MODE`
- **AND** SHALL proceed with normal worktree creation flow

### Requirement: ship-execution-mode-project-yaml-priority

The `_lib/ship_execution_mode.sh::parse_execution_mode()` SHALL resolve execution mode in priority order: CLI flag (`--parallel`/`--serial`) > `.rddf/project.yaml` `git.openspec_tracked` field > `RDD_SHIP_PARALLEL` env var > default (serial).

#### Scenario: CLI flag overrides project.yaml
- **WHEN** `--parallel` CLI flag is passed
- **AND** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **THEN** `parse_execution_mode` SHALL return "parallel" (CLI priority)

#### Scenario: project.yaml overrides env var
- **WHEN** no CLI flag is passed
- **AND** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `RDD_SHIP_PARALLEL=yes` is set
- **THEN** `parse_execution_mode` SHALL return "serial" (project.yaml priority > env var)

#### Scenario: env var used when no project.yaml
- **WHEN** no CLI flag is passed
- **AND** `.rddf/project.yaml` does not exist
- **AND** `RDD_SHIP_PARALLEL=yes` is set
- **THEN** `parse_execution_mode` SHALL return "parallel"

#### Scenario: default serial when nothing set
- **WHEN** no CLI flag is passed
- **AND** no `.rddf/project.yaml` exists
- **AND** `RDD_SHIP_PARALLEL` is unset
- **THEN** `parse_execution_mode` SHALL return "serial" (default)

### Requirement: archive-openspec-tracked-skip-git

The `_lib/archive.sh::archive_change()` function SHALL detect `.rddf/project.yaml` `git.openspec_tracked` field, and when set to `false`, SHALL skip `git merge` and `commit_archive_moves` operations, executing only `openspec archive` and `mark_iteration_archived`.

#### Scenario: openspec_tracked=false skips git merge
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: false}`
- **AND** `archive_change(change_name)` is invoked
- **THEN** the function SHALL NOT execute `git merge <branch> <default_branch>`
- **AND** SHALL NOT execute `commit_archive_moves`
- **AND** SHALL execute `openspec archive <change> --yes`
- **AND** SHALL execute `mark_iteration_archived <change>`
- **AND** SHALL print "📦 openspec_tracked=false: 跳过 git merge/commit"

#### Scenario: openspec_tracked=true (default) executes git merge
- **WHEN** `.rddf/project.yaml` contains `git: {openspec_tracked: true}` OR does not exist
- **AND** `archive_change(change_name)` is invoked
- **THEN** the function SHALL execute `check_worktree_commits`, `git merge`, `verify_merge_result`, `commit_archive_moves`, `openspec archive`, `mark_iteration_archived` (full sequence)

### Requirement: populate-adr-pattern-from-handoff

The `populate_lib.py::catalog_sources()` and `_lib/roadmap_incremental_update.py::incremental_update()` functions SHALL accept and propagate `adr_pattern` parameter, sourced from `.rddf/state/.arch-handoff.json` (priority: explicit arg > arch-handoff > 4-digit default).

#### Scenario: adr_pattern from arch-handoff
- **WHEN** `.rddf/state/.arch-handoff.json` contains `adr_pattern: "^ADR-(\\d{3})-.*\\.md$"`
- **AND** `catalog_sources(project_root=...)` is called without explicit `adr_pattern`
- **THEN** `catalog_sources` SHALL use `^ADR-(\\d{3})-.*\\.md$` as the pattern
- **AND** SHALL identify ADR-040, ADR-041, ADR-042 (3-digit)

#### Scenario: explicit arg overrides handoff
- **WHEN** `catalog_sources(project_root=..., adr_pattern="^ADR-(\\d{4})-.*\\.md$")` is called with explicit arg
- **AND** handoff contains different `adr_pattern`
- **THEN** `catalog_sources` SHALL use the explicit arg pattern (highest priority)

#### Scenario: no handoff falls back to 4-digit default
- **WHEN** no `.rddf/state/.arch-handoff.json` exists
- **AND** `catalog_sources(project_root=...)` is called without explicit `adr_pattern`
- **THEN** `catalog_sources` SHALL use default 4-digit pattern `^ADR-(\\d{4})-.*\\.md$`
- **AND** SHALL maintain backward compatibility with existing 36 ADR documents

### Requirement: zero-regression-backward-compat

The change SHALL preserve 100% backward compatibility: all existing 2421 pytest tests and existing bats integration tests SHALL continue to pass without modification, and absence of `.rddf/project.yaml` SHALL yield identical behavior to pre-change state.

#### Scenario: missing project.yaml no schema validation
- **WHEN** `.rddf/project.yaml` does not exist
- **THEN** no schema validation SHALL be triggered for project/adr/git/verification sections
- **AND** all existing pytest tests in `tests/unit/test_config.py`, `tests/unit/test_adr_catalog.py`, `tests/unit/test_hook_runner.py` SHALL pass

#### Scenario: default provider llm no behavior change
- **WHEN** `.rddf/project.yaml` does not exist OR does not contain `verification.provider`
- **THEN** `rddf rdd-verify` SHALL invoke `_default_runner` (existing ac-verifier)
- **AND** existing `test_rdd_verifier_e2e.bats` 8 cases SHALL pass without modification

#### Scenario: default openspec_tracked no worktree change
- **WHEN** `.rddf/project.yaml` does not exist OR contains `git: {openspec_tracked: true}`
- **THEN** `guide-ship` Phase 1 SHALL proceed with normal worktree creation
- **AND** existing `test_guide_ship_execution_mode.bats` 12 cases SHALL pass without modification

### Requirement: adr-0036-post-hoc-fix-record

The `docs/adr/ADR-0036-rddf-project-yaml-config.md` SHALL contain a new `## Post-hoc Fix Record (2026-09-02)` section AFTER the original `## Consequences` section (NOT appended to Consequences), documenting this change's fix scope (8 checkbox-as-done gaps identified in i10 archive audit).

#### Scenario: ADR-0036 Post-hoc Fix Record added
- **WHEN** this change is merged to master
- **THEN** `docs/adr/ADR-0036-rddf-project-yaml-config.md` SHALL contain a new heading `## Post-hoc Fix Record (2026-09-02)` AFTER the `## Consequences` section
- **AND** SHALL reference `openspec/changes/2026-09-02-complete-project-yaml-config-gaps/` as the fix change
- **AND** SHALL enumerate the 8 fixed task items (1.1, 1.5, 3.1, 3.2, 3.4, 3.5, 4.2, 4.3)

#### Scenario: ADR-0036 original Consequences preserved
- **WHEN** this change is merged
- **THEN** `docs/adr/ADR-0036-rddf-project-yaml-config.md` original `## Consequences` section SHALL remain UNCHANGED
- **AND** the original decision (project.yaml as project-level config source) SHALL NOT be reversed

#### Scenario: ADR-0036 status unchanged
- **WHEN** this change is merged
- **THEN** `docs/adr/ADR-0036-rddf-project-yaml-config.md` status SHALL remain "已采纳"
- **AND** the post-hoc fix record SHALL be a new section, not a status change

### Requirement: full-regression-pre-archive

The change SHALL NOT be archived (via `openspec archive`) until `./test.sh --full --regression` exits 0, per AGENTS.md §"Archive 前全量回归门 (MANDATORY)".

#### Scenario: regression gate blocks archive
- **WHEN** `./test.sh --full --regression` exits non-zero (any new failure not in KNOWN_FAILURES.txt)
- **THEN** `openspec archive complete-project-yaml-config-gaps --yes` SHALL fail
- **AND** the error message SHALL reference the failing test(s)

#### Scenario: regression gate allows archive when green
- **WHEN** `./test.sh --full --regression` exits 0 (only KNOWN_FAILURES.txt entries remain failing)
- **THEN** `openspec archive complete-project-yaml-config-gaps --yes` SHALL succeed

### Requirement: preventive-tasks-diff-check-mandatory

The change SHALL include `tests/integration/test_archive_gate_tasks_checklist_match.bats` (MANDATORY, not optional) that validates `tasks.md` checkbox states against file-level git diff, preventing future checkbox-as-done incidents (root cause of this change). The test runs before archive and SHALL fail the archive flow if any `- [x]` task does not correspond to a file change in the diff.

#### Scenario: checkbox-as-done detected
- **WHEN** `openspec/changes/<name>/tasks.md` contains `- [x]` for a task
- **AND** `git diff master..HEAD` does not include the file referenced by the task
- **THEN** the bats test SHALL fail
- **AND** the failure message SHALL identify the orphan checkbox and its expected file

#### Scenario: all checkboxes match diff passes
- **WHEN** all `- [x]` tasks in `tasks.md` reference files present in `git diff master..HEAD`
- **THEN** the bats test SHALL pass
- **AND** `openspec archive` SHALL proceed

#### Scenario: open checkboxes not validated
- **WHEN** `tasks.md` contains `- [ ]` (open) checkboxes
- **THEN** the bats test SHALL NOT validate them (only `- [x]` checked)

#### Scenario: archive flow requires this test to pass
- **WHEN** `openspec archive <change> --yes` is invoked
- **THEN** the bats test SHALL run first
- **AND** SHALL exit 0 before archive proceeds
- **AND** if exit non-zero, archive SHALL abort