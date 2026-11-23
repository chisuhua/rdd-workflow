# e2e-test-infrastructure Specification

## Purpose
TBD - created by archiving change add-e2e-test-plan-phase1. Update Purpose after archive.
## Requirements
### Requirement: e2e-test-infrastructure

The rdd-workflow repository SHALL provide an A-layer end-to-end test infrastructure (CI-required, no agent credentials) that verifies:
- (1) phase scripts and scaffold helpers are invokable non-interactively,
- (2) fake-project execution context is isolated from the real repo state via sha256 locks,
- (3) golden output drift is detectable for C-layer scenarios.

#### Scenario: A-layer smoke runs in CI under 90 seconds

- **WHEN** `./test.sh --e2e-smoke` is invoked
- **THEN** all 10 bats cases in `tests/e2e/script/` pass
- **AND** total runtime is under 90 seconds (excludes compile/install)

#### Scenario: phase scripts accept --auto-approve flag without TTY hang

- **WHEN** any of `phase{0,1,1_5,2,2_5,3}_*.sh` is invoked with `--auto-approve`
- **THEN** the script exits within 10 seconds with status code != 124 (timeout)
- **AND** no interactive prompt is displayed

#### Scenario: scaffold_plan.sh accepts --no-confirm flag

- **WHEN** `scaffold_plan.sh --name <kebab> --proposal "..." --no-confirm` is invoked
- **THEN** a `quick-<kebab>.md` file is created in `${RDDF_QUICK_PLAN_DIR}`
- **AND** the file contains 5 TDD markers and a `## Acceptance` section with ≥1 AC checkbox

#### Scenario: zero pollution across 6 locked paths

- **WHEN** any test in `tests/e2e/script/` runs to completion
- **THEN** `isolation::verify_zero_pollution` returns 0 (no change)
- **AND** the 6 locked paths (`.rddf/`, `openspec/`, `.rddf/wt/`, `.rddf/state/iteration.json`, `.rddf/state/sessions.json`, `.rddf/state/roadmap-state.json`) match baseline sha256

#### Scenario: test.sh exposes 3 new modes for e2e dispatch

- **WHEN** `./test.sh --e2e-smoke` is invoked
- **THEN** `tests/e2e/script/` bats suite runs; absent dir produces SKIP message with exit 0
- **WHEN** `./test.sh --e2e-agent` is invoked without `RDDF_AGENT_E2E=1`
- **THEN** SKIP message prints and exit 0 (C-layer requires explicit opt-in)
- **WHEN** `./test.sh --e2e-all` is invoked
- **THEN** both e2e-smoke and e2e-agent run in sequence

#### Scenario: append_history.py validates and writes to .quick-history.jsonl

- **WHEN** a JSON entry matching `quick_history_schema.json` v1 is piped to `append_history.py` via stdin
- **AND** `RDDF_QUICK_HISTORY_FILE` env var redirects write path to fake root
- **THEN** the entry is validated and atomically appended to the target file
- **AND** validation failure produces exit 1 with no write performed

