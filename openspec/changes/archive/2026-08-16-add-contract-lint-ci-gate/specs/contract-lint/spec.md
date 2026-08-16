---
SCOPE: shared
STATUS: PROPOSED
DATE: 2026-08-16
CHANGE: add-contract-lint-ci-gate
RELATED: gate-mechanism (severity-segregated gating pattern)
---

# Capability: contract-lint

> Contract consistency checking between Hub (OpenAPI/Protobuf contracts) and Spoke
> (local implementations). Provides `rddf contract-check` CLI, Hub/Spoke CI workflows,
> and `STRICT_CONTRACT_GATE` mode for breaking-change detection.

## ADDED Requirements

### Requirement: rddf contract-check CLI MUST provide three operation modes

The `rddf contract-check` command MUST support three mutually-exclusive modes
controlled by flags:

- `--warn-only` (default): Output warnings but exit 0 (soft fail)
- `--strict`: Exit 1 on any difference (Breaking-Change or Non-Breaking)
- `--diff-only`: Output diff summary without pass/fail exit code

**Alternatives considered:**
- Single `--strict` flag (warn by default): Rejected because explicit `--warn-only`
  is clearer for CI configuration.

#### Scenario: warn-only mode exits 0 with warnings

- **WHEN** user runs `rddf contract-check --contract auth-v2.yaml --impl src/api/auth.py --warn-only`
- **AND** there are Non-Breaking differences
- **THEN** exit code is 0
- **AND** stdout shows warning summary

#### Scenario: strict mode exits 1 on any difference

- **WHEN** user runs `rddf contract-check --contract auth-v2.yaml --impl src/api/auth.py --strict`
- **AND** there is at least one Breaking-Change or Non-Breaking difference
- **THEN** exit code is 1
- **AND** stdout shows error summary

#### Scenario: diff-only mode shows diff without exit code

- **WHEN** user runs `rddf contract-check --contract auth-v2.yaml --impl src/api/auth.py --diff-only`
- **AND** there are differences
- **THEN** exit code is 0
- **AND** stdout shows detailed diff
- **AND** no pass/fail judgment is rendered

### Requirement: rddf contract-check MUST classify diff severity into three levels

The `rddf contract-check` output MUST classify each difference into exactly one of:

- `Breaking-Change`: API contract incompatible (e.g., removed required field, changed type)
- `Non-Breaking`: Backward-compatible addition (e.g., added optional field)
- `New-Contract`: New endpoint/path in Hub not in local impl

#### Scenario: Breaking-Change detected for removed required field

- **WHEN** Hub contract has `required: [email, password]` but local impl missing `email`
- **THEN** diff includes `Breaking-Change: POST /v2/login missing required field 'email'`

#### Scenario: Non-Breaking detected for added optional field

- **WHEN** Hub contract adds `device_fingerprint` as optional but local impl lacks it
- **THEN** diff includes `Non-Breaking: POST /v2/login has new optional field 'device_fingerprint'`

#### Scenario: New-Contract detected for endpoint only in Hub

- **WHEN** Hub contract defines `GET /v2/user/profile` but local impl has no such path
- **THEN** diff includes `New-Contract: GET /v2/user/profile exists in Hub but not in local`

### Requirement: rddf contract-check MUST support OpenAPI 3.0+ and Protobuf 3+ formats

The `rddf contract-check` command MUST accept:

- OpenAPI 3.0+ YAML/JSON files (detected by `openapi:` version field)
- Protobuf 3+ proto files (detected by `syntax = "proto3"`)

**Out of scope for v1**: OpenAPI 2.x (Swagger), GraphQL schemas, JSON Schema only.

#### Scenario: OpenAPI 3.0 contract checked successfully

- **WHEN** `--contract auth-v2.yaml` contains `openapi: 3.0.0`
- **AND** `--impl src/api/auth.py` contains Python HTTP handler definitions
- **THEN** diff is computed using OpenAPI Diff logic

#### Scenario: Protobuf 3 contract checked successfully

- **WHEN** `--contract auth.proto` contains `syntax = "proto3"`
- **AND** `--impl src/proto/auth.pb.go` contains Go protobuf definitions
- **THEN** diff is computed using Protobuf schema comparison

### Requirement: rddf contract-check MUST cache contract versions in .contract-cache.json

The rddf contract-check command SHALL store SHA256 of contract content in `.rddf/state/.contract-cache.json` when a contract is fetched from Hub. The SHA256 SHALL be stored alongside `fetched_at` timestamp and `hub_owner` for cache validation.

```json
{
  "contracts": {
    "auth-v2.yaml": {
      "sha": "abc123...",
      "fetched_at": "2026-08-16T10:00:00Z",
      "hub_owner": "myorg"
    }
  }
}
```

Cache hit occurs when local SHA matches cached SHA.

#### Scenario: Cache hit skips re-fetch

- **WHEN** `RDDF_HUB_TOKEN` is set but Hub is unreachable
- **AND** `.contract-cache.json` contains SHA matching local `.rddf/state/contracts/auth-v2.yaml`
- **THEN** command runs in offline mode using local cache
- **AND** stdout shows `Using cached contract (sha matches)`

#### Scenario: Cache miss triggers re-fetch or warning

- **WHEN** `RDDF_HUB_TOKEN` is set and Hub is reachable
- **AND** local contract SHA differs from cached SHA
- **THEN** fresh contract is fetched from Hub
- **AND** `.contract-cache.json` is updated

### Requirement: rddf contract-check MUST operate in offline mode when Hub is unreachable

The rddf contract-check command SHALL operate in offline mode when Hub is unreachable. In offline mode, the command SHALL use the locally cached contract if SHA matches, or use the local contract file directly if no cache exists. The command SHALL output a WARNING that Hub was unreachable and SHALL NOT block on Hub unavailability.

#### Scenario: Hub unreachable with valid cache runs successfully

- **WHEN** `RDDF_HUB_OWNER` and `RDDF_HUB_TOKEN` are set
- **AND** Hub API returns non-200
- **AND** local `.rddf/state/contracts/auth-v2.yaml` exists with matching SHA in cache
- **THEN** command completes with WARNING: `Hub unreachable, using local cache`
- **AND** exit code follows `--warn-only`/`--strict`/`--diff-only` semantics

#### Scenario: Hub unreachable without cache runs with warning

- **WHEN** `RDDF_HUB_OWNER` and `RDDF_HUB_TOKEN` are set
- **AND** Hub API returns non-200
- **AND** no local cache exists for the contract
- **THEN** command completes with WARNING: `Hub unreachable, no cache available`
- **AND** uses local contract file directly

### Requirement: STRICT_CONTRACT_GATE=yes MUST upgrade warn to hard block on Breaking-Change

When `STRICT_CONTRACT_GATE=yes` environment variable is set, the rddf contract-check command SHALL exit 1 (blocking ship phase) when Breaking-Change is detected. Non-Breaking or New-Contract differences SHALL result in exit 0. This allows Spoke repositories to opt into strict gating without changing CLI flags.

#### Scenario: STRICT_CONTRACT_GATE=yes blocks Breaking-Change

- **WHEN** `STRICT_CONTRACT_GATE=yes` is set
- **AND** `rddf contract-check` finds a Breaking-Change difference
- **THEN** exit code is 1
- **AND** output includes `STRICT_CONTRACT_GATE: blocking ship due to Breaking-Change`

#### Scenario: STRICT_CONTRACT_GATE=yes allows Non-Breaking differences

- **WHEN** `STRICT_CONTRACT_GATE=yes` is set
- **AND** `rddf contract-check` finds only Non-Breaking and/or New-Contract differences
- **THEN** exit code is 0

### Requirement: rddf contract-check --all MUST check all contracts in .rddf/state/contracts/

When `--all` flag is provided without `--contract`, the rddf contract-check command SHALL scan `.rddf/state/contracts/` for cached contracts, run diff against corresponding local implementation files, and aggregate results into a single report.

#### Scenario: --all processes multiple contracts

- **WHEN** `.rddf/state/contracts/` contains `auth-v2.yaml` and `billing-v1.yaml`
- **AND** corresponding implementation files exist locally
- **THEN** both are checked
- **AND** output shows per-contract summaries
- **AND** exit code reflects worst severity across all checks

### Requirement: rddf contract-check output MUST support JSON and Markdown formats

The `--format json` and `--format markdown` flags MUST control output format.

Default format is human-readable with emoji indicators.

#### Scenario: JSON format output structure

- **WHEN** `--format json` is specified
- **THEN** stdout is valid JSON with structure:
```json
{
  "contract": "auth-v2.yaml",
  "impl": "src/api/auth.py",
  "severity": "Breaking-Change",
  "diffs": [
    {
      "type": "Breaking-Change",
      "path": "POST /v2/login",
      "message": "missing required field 'email'"
    }
  ],
  "summary": { "breaking": 1, "non-breaking": 0, "new": 0 }
}
```

### Requirement: Hub CI workflow MUST detect contracts/ changes and notify Spoke repos

The `.github/workflows/contract-lint.yml` in Hub repos MUST:

1. Trigger on `push` to `contracts/` directory
2. Compute diff of changed contract files
3. For each affected contract, identify dependent Spoke repos
4. Create GitHub Issue or PR comment on each Spoke repo

**Manual gate note**: Hub CI configuration is out of scope for this change.
The `contract-lint.yml` template is provided as documentation.

#### Scenario: Hub CI detects contract change and creates issue

- **WHEN** Hub repo push includes changes to `contracts/auth-v2.yaml`
- **AND** `spokes.json` lists `spoke-a` and `spoke-b` as consumers
- **THEN** Issues are created on both spoke repos
- **AND** Issue title includes `[Hub] Contract sync required: auth-v2.yaml`

### Requirement: Spoke CI workflow MUST run rddf contract-check on pull requests

The `.github/workflows/contract-lint.yml` in Spoke repos MUST:

1. Trigger on `pull_request` events
2. Run `rddf contract-check --all --strict` (or `--warn-only` per repo config)
3. Fail the PR check if contract check fails

#### Scenario: Spoke PR fails contract check

- **WHEN** Spoke repo PR introduces code breaking Hub contract
- **AND** `rddf contract-check --all --strict` returns exit 1
- **THEN** PR check status is failure
- **AND** check run shows contract diff summary

### Requirement: rddf contract-check MUST integrate with guide-ship phase

The rddf contract-check command SHALL be integrable with guide-ship phase. When `guide-ship` executes a change in a Spoke repo, Phase 2 execute MAY invoke `rddf contract-check` as part of implementation verification. If `STRICT_CONTRACT_GATE=yes` and Breaking-Change is detected, the ship phase SHALL block. Contract check results SHALL be included in execute step 7 report when integration is enabled.

**Hub/Spoke CI is manual gate**: External repo CI cannot be automatically enforced by `guide-ship`. The Spoke CI workflow is opt-in configuration.

#### Scenario: guide-ship Phase 2 calls contract-check when enabled

- **WHEN** `guide-ship` Phase 2 executes with `CONTRACT_CHECK_ENABLED=yes`
- **AND** `rddf contract-check --all --strict` is run
- **AND** Breaking-Change is detected
- **THEN** ship phase is blocked
- **AND** error output indicates Breaking-Change details

## MODIFIED Requirements

(None)

## REMOVED Requirements

(None)

## RENAMED Requirements

(None)
