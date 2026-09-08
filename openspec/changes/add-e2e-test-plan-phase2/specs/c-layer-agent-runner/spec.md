## ADDED Requirements

### Requirement: c-layer-agent-runner

The rdd-workflow repository SHALL provide a C-layer (agent simulation) test framework that validates prose UX of skills through three dispatch modes:
- (1) `validate` (CI default) — JSON schema + golden field check only,
- (2) `mock` — materializes pre-recorded `mock_output` from scenario JSON,
- (3) `real` — invokes an actual agent CLI (opencode / claude / codex) when `RDDF_AGENT_E2E=1` is set.

#### Scenario: validate mode rejects malformed scenario JSON

- **WHEN** `agent_runner::validate_scenario` is invoked with non-JSON content
- **THEN** exit code is 2 with stderr `ERROR: malformed JSON: ...`

#### Scenario: validate mode rejects missing required fields

- **WHEN** a scenario JSON is missing one of `scenario_id`, `skill`, `input`, `golden_output`, `isolation`
- **THEN** exit code is 1 with stderr `ERROR: missing required fields: [...]`

#### Scenario: mock mode materializes mock_output files to output_dir

- **WHEN** `agent_runner::run` is called with `AGENT_RUNNER_MODE=mock` and a scenario with `mock_output.files`
- **THEN** each file path in `mock_output.files` is created under `output_dir` with the specified content
- **AND** `output_dir/stdout.txt` contains the `mock_output.stdout` content

#### Scenario: verify mode checks golden_output key fields

- **WHEN** `agent_runner::verify` is called with output_dir and scenario
- **THEN** all `golden_output.files[].must_exist=true` paths must exist
- **AND** all `golden_output.stdout_contains[]` strings must appear in `output_dir/stdout.txt`
- **AND** all `golden_output.history_jsonl[]` entries must match at least one line in the jsonl

#### Scenario: detect_mode returns real when RDDF_AGENT_E2E=1 and agent CLI present

- **WHEN** `RDDF_AGENT_E2E=1` is set and `opencode`, `claude`, or `codex` is on PATH
- **THEN** `agent_runner::detect_mode` prints `real`

#### Scenario: test.sh --e2e-agent SKIPs cleanly when RDDF_AGENT_E2E not set

- **WHEN** `./test.sh --e2e-agent` is invoked without `RDDF_AGENT_E2E=1`
- **THEN** stdout contains `SKIP: C-layer e2e agent (set RDDF_AGENT_E2E=1 to enable)`
- **AND** exit code is 0 (not 1)

#### Scenario: rdd-quick C-layer covers P0-P4 + zero-pollution

- **WHEN** `tests/e2e/agent/test_rdd_quick_e2e.bats` runs in mock mode
- **THEN** all 8 scenarios (Q-E1..Q-E8) pass
- **AND** `$REPO_ROOT/.rddf/`, `openspec/`, `.rddf/wt/`, `iteration.json`, `sessions.json`, `roadmap-state.json` are all sha256-unchanged after the run
