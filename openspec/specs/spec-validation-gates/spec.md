# spec-validation-gates Specification

## Purpose
TBD - created by archiving change add-spec-validation-gates. Update Purpose after archive.
## Requirements
### Requirement: validate_baseline.py MUST verify file existence claims with file-exists prefix

The `skills/_lib/validate_baseline.py` script MUST support the `file-exists:<path>`
prefix in `.openspec.yaml` `baseline:` values. When a baseline claim starts with
this prefix, the script MUST check that `<path>` (resolved relative to the change
root) exists as a regular file in the filesystem. The script MUST exit 1 when the
file is missing, with an error message identifying the path and the affected claim key.

#### Scenario: Baseline claim with file-exists prefix passes when file present

- **WHEN** `.openspec.yaml` contains `baseline: { my-key: "file-exists:src/foo.cpp" }`
- **AND** the file `src/foo.cpp` exists relative to the change root
- **THEN** `validate_baseline.py <change-name>` exits 0
- **AND** stdout includes `✅ file-exists:src/foo.cpp OK`

#### Scenario: Baseline claim with file-exists prefix fails when file missing

- **WHEN** `.openspec.yaml` contains `baseline: { my-key: "file-exists:does/not/exist.cpp" }`
- **AND** the file `does/not/exist.cpp` does NOT exist
- **THEN** `validate_baseline.py <change-name>` exits 1
- **AND** stderr includes `❌ baseline.my-key` and `does/not/exist.cpp`
- **AND** stderr includes actionable fix hint (e.g., "Fix: create the file or correct the path")

### Requirement: validate_baseline.py MUST verify symbol existence claims with symbol-exists prefix

The `skills/_lib/validate_baseline.py` script MUST support the
`symbol-exists:<path>:<regex>` prefix. When a baseline claim starts with this prefix,
the script MUST read `<path>` and check that `<regex>` matches at least one line.
The script MUST exit 1 when no match is found.

#### Scenario: Symbol claim passes when regex matches

- **WHEN** `.openspec.yaml` contains `baseline: { sym: "symbol-exists:src/foo.cpp:class FooBar" }`
- **AND** `src/foo.cpp` contains the text `class FooBar`
- **THEN** `validate_baseline.py <change-name>` exits 0

#### Scenario: Symbol claim fails when regex does not match

- **WHEN** `.openspec.yaml` contains `baseline: { sym: "symbol-exists:src/foo.cpp:class FooBar" }`
- **AND** `src/foo.cpp` does NOT contain `class FooBar`
- **THEN** `validate_baseline.py <change-name>` exits 1
- **AND** stderr identifies the missing pattern and the file path

### Requirement: validate_baseline.py MUST verify git history claims with git-history prefix

The `skills/_lib/validate_baseline.py` script MUST support the `git-history:<symbol>`
prefix. When a baseline claim starts with this prefix, the script MUST run
`git log -S "<symbol>" --all --oneline` (with a default 10s timeout) and verify
at least 1 commit is returned. The script MUST exit 1 when zero commits are found.

#### Scenario: Git history claim passes when symbol has history

- **WHEN** `.openspec.yaml` contains `baseline: { hist: "git-history:CudaStub g_cuda_stub" }`
- **AND** `git log -S "CudaStub g_cuda_stub"` returns ≥1 commit
- **THEN** `validate_baseline.py <change-name>` exits 0

#### Scenario: Git history claim fails when symbol never committed (v1 regression)

- **WHEN** `.openspec.yaml` contains `baseline: { hist: "git-history:CudaStub g_cuda_stub" }`
- **AND** `git log -S "CudaStub g_cuda_stub"` returns 0 commits (symbol was never added)
- **THEN** `validate_baseline.py <change-name>` exits 1
- **AND** stderr message includes "CudaStub g_cuda_stub" and a fix hint
- **AND** this MUST catch the v1 incident pattern from g-gpu-client-default-stub-init

#### Scenario: Git history validator respects timeout

- **WHEN** `git log -S` takes longer than the configured timeout (default 10s)
- **THEN** the validator MUST exit 1 with timeout error message
- **AND** MUST NOT hang indefinitely

### Requirement: validate_baseline.py accepts unverifiable free-text claims as warnings

The `skills/_lib/validate_baseline.py` script MUST NOT treat free-text baseline
values (those without any of the supported prefixes `file-exists:`,
`symbol-exists:`, `git-history:`) as failures. When a baseline value has no
recognized prefix, the validator MUST log a warning indicating the claim is
unverifiable and exit 0 (or exit 2 if warnings are present, so CI can
distinguish strict pass from soft warn).

#### Scenario: Free-text baseline claim does not block validator

- **WHEN** `.openspec.yaml` contains `baseline: { free-text: "some description, no prefix" }`
- **THEN** `validate_baseline.py <change-name>` exits 0 (or 2 with warning)
- **AND** does NOT report the free-text claim as a failure

### Requirement: validate_delta_targets.py MUST check MODIFIED targets exist in main specs

The `skills/_lib/validate_delta_targets.py` script MUST parse
`<change>/specs/<cap>/spec.md` for `## MODIFIED Requirements` and
`## RENAMED Requirements` sections. For each requirement in these sections,
the script MUST verify the target capability exists in `openspec/specs/`
of the change root.

For MODIFIED requirements:
- Default target = the change's own capability name (from `.openspec.yaml` `name:` field)
- If requirement body contains `modifies: <cap>` or `target: <cap>` in the first 5 lines, override target to that cap
- MUST exit 1 if target capability is NOT in main `openspec/specs/`

For RENAMED requirements:
- Source = the old name in the header (e.g., `### Requirement: old-name -> new-name`)
- MUST exit 1 if source capability is NOT in main `openspec/specs/`

#### Scenario: MODIFIED requirement for new capability fails (v2 regression)

- **WHEN** a change's `specs/<cap>/spec.md` contains `## MODIFIED Requirements` section
- **AND** target capability is NOT in main `openspec/specs/`
- **THEN** `validate_delta_targets.py <change-name>` exits 1
- **AND** stderr identifies the invalid target capability
- **AND** this MUST catch the v2 incident pattern from g-gpu-client-meyers-singleton-fallback

#### Scenario: MODIFIED requirement passes when target exists

- **WHEN** a change's `specs/<cap>/spec.md` contains `## MODIFIED Requirements`
- **AND** target capability IS in main `openspec/specs/`
- **THEN** `validate_delta_targets.py <change-name>` exits 0

#### Scenario: RENAMED requirement passes when source exists

- **WHEN** a change's `specs/<cap>/spec.md` contains `## RENAMED Requirements` with header `### Requirement: old-name -> new-name`
- **AND** `openspec/specs/old-name/spec.md` exists in main
- **THEN** `validate_delta_targets.py <change-name>` exits 0

#### Scenario: ADDED requirements require no validation

- **WHEN** a change's `specs/<cap>/spec.md` contains ONLY `## ADDED Requirements` (no MODIFIED or RENAMED)
- **THEN** `validate_delta_targets.py <change-name>` exits 0
- **AND** no target existence checks are performed (new capabilities naturally have no main spec)

### Requirement: propose.md MUST call validate_baseline.py before writing artifacts

The `skills/propose.md` workflow MUST invoke `validate_baseline.py` after
`openspec new change <name>` creates the change directory but BEFORE writing
`proposal.md`, `design.md`, or other artifacts. If validation fails (exit 1),
the workflow MUST abort with a clear error message pointing to the failing claim.

#### Scenario: propose aborts when baseline claim is fabricated

- **WHEN** user runs `propose` workflow to create a new change
- **AND** the new change's `.openspec.yaml` contains a fabricated baseline claim (e.g., `file-exists:does/not/exist.cpp`)
- **THEN** `propose` workflow MUST exit before writing `proposal.md`
- **AND** user MUST see the validation error message
- **AND** the change directory exists but contains no proposal artifacts

### Requirement: guide-plan.md plan-done gate MUST validate all active changes

The Phase 4 plan-done gate in `skills/guide-plan.md` MUST invoke both
`validate_baseline.py` and `validate_delta_targets.py` on every active change
before writing `.rddf/state/.plan-handoff.json`. If ANY change fails validation,
the gate MUST block plan-done and exit 1.

#### Scenario: plan-done gate blocks when one change fails validation

- **WHEN** `guide-plan` reaches Phase 4 plan-done
- **AND** multiple active changes exist
- **AND** at least one change fails `validate_baseline.py` or `validate_delta_targets.py`
- **THEN** the gate MUST exit 1
- **AND** `.rddf/state/.plan-handoff.json` MUST NOT be written
- **AND** stderr MUST identify which change(s) failed

#### Scenario: plan-done gate proceeds when all changes pass validation

- **WHEN** `guide-plan` reaches Phase 4 plan-done
- **AND** all active changes pass both validators
- **THEN** the gate MUST write `.rddf/state/.plan-handoff.json`
- **AND** exit 0

### Requirement: guide-ship.md archive pre-flight MUST call validate_delta_targets.py

The Phase 3 archive section in `skills/guide-ship.md` MUST invoke
`validate_delta_targets.py` immediately before calling `openspec archive
<change-name> --yes`. If validation fails (exit 1), the workflow MUST abort
BEFORE calling openspec archive. This prevents the 6-step recovery chain
(edit spec → commit → push → bump submodule → push → retry) required when
`openspec archive` aborts due to MODIFIED-on-empty.

#### Scenario: Archive pre-flight catches invalid MODIFIED target

- **WHEN** user runs `guide-ship` Phase 3 archive on a change
- **AND** the change has `## MODIFIED Requirements` targeting non-existent capability
- **THEN** `validate_delta_targets.py` exits 1
- **AND** `openspec archive` is NOT called
- **AND** user sees the validation error message

#### Scenario: Archive proceeds when validation passes

- **WHEN** user runs `guide-ship` Phase 3 archive
- **AND** `validate_delta_targets.py` exits 0
- **THEN** `openspec archive <change-name> --yes` is called normally
- **AND** existing archive flow proceeds unchanged

### Requirement: Validators MUST be invokable from CI

The validator scripts MUST be callable from CI via:
```bash
python3 skills/_lib/validate_baseline.py <change-name>
python3 skills/_lib/validate_delta_targets.py <change-name>
```
Exit codes: 0 = pass, 1 = hard fail (blocks), 2 = soft warn (verifiable false + unverifiable mix).

`.github/workflows/test.yml` MUST include a step that runs both validators
against all active changes (excluding `archive/`).

#### Scenario: CI step iterates over all active changes

- **WHEN** CI runs the spec-validation step
- **AND** there are N active changes under `openspec/changes/` (excluding `archive/`)
- **THEN** the step MUST invoke both validators N times (once per change)
- **AND** if any invocation exits 1, the step MUST exit 1
- **AND** the CI workflow MUST fail when the step exits 1

#### Scenario: CI step skips archived changes

- **WHEN** CI runs the spec-validation step
- **AND** `openspec/changes/archive/` contains archived changes
- **THEN** the step MUST NOT iterate over `archive/` subdirectories
- **AND** only active changes are validated

### Requirement: Validators must not break existing tests

The validator scripts MUST preserve all 28 existing `tests/unit/` Python test
files and the `tests/smoke.bats` Bats test files. Validators MUST NOT modify
shared state (no writes to `.rddf/state/` outside their own scope, no global
Python state mutation). All existing tests MUST continue to pass after the
validators are added.

#### Scenario: Full pytest suite passes after validator addition

- **WHEN** `pytest tests/unit/` is run
- **THEN** all 28+2 = 30 test files (28 existing + 2 new validator tests) MUST pass
- **AND** no existing test is modified or skipped

#### Scenario: Full bats smoke suite passes after validator addition

- **WHEN** `bats tests/smoke.bats` is run
- **THEN** all smoke test cases MUST pass (no regression)
- **AND** `npm test` (which runs full bats suite) MUST pass

### Requirement: plan-done isComplete 校验

The plan-done gate SHALL query `openspec status --change <name> --json` for each active change and emit a warning when `isComplete` is false. This check coexists with the ADR-0015 `openspec_validate` check and MUST NOT duplicate its `openspec validate --all --strict --json` invocation.

#### Scenario: 未完成的 change 给出 warning

- GIVEN an active change whose `status --json` reports `isComplete: false`
- WHEN the plan-done gate runs
- THEN a warning listing the incomplete change is emitted, and the ADR-0015 strict validate check still runs exactly once

### Requirement: skip_specs 接入

For changes whose `roadmap-meta.yaml` has `change_type` of `doc-only` or `test-only`, the system SHALL write `skip_specs: true` into the change's `.openspec.yaml`, replacing ad-hoc zero-delta workarounds.

#### Scenario: doc-only change 免 delta

- GIVEN a change with `change_type: "doc-only"`
- WHEN the change is created
- THEN `.openspec.yaml` contains `skip_specs: true` and `openspec validate <name> --strict --json` passes without any specs delta

