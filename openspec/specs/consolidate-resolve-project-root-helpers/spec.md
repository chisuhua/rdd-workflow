# consolidate-resolve-project-root-helpers Specification

## Purpose
TBD - created by archiving change consolidate-resolve-project-root-helpers. Update Purpose after archive.
## Requirements
### Requirement: contract-file-defines-4-invariants

`skills/_lib/_resolve_project_root_contract.yaml` SHALL define 4 invariants that all 3 project_root resolution implementations (bash `_resolve_project_root`, Python `skills._lib._python_resolve_project_root.resolve_project_root`, Python `_lib.cli.__main__.resolve_project_root`) MUST satisfy:

- **invariant_env_override**: if `RDDF_PROJECT_ROOT` env var is set and non-empty, return its value
- **invariant_git_probe**: if env var unset AND cwd is inside a git repo, return git toplevel (submodule-aware per ADR-0033)
- **invariant_cwd_fallback**: if env var unset AND cwd is NOT in a git repo, return cwd as-is
- **invariant_function_signature**: bash returns string from function, Python returns `str` from `resolve_project_root() -> str`

#### Scenario: contract file exists and is valid YAML

- **WHEN** reading `skills/_lib/_resolve_project_root_contract.yaml`
- **THEN** the file SHALL be well-formed YAML, parseable via `yaml.safe_load`
- **AND** the file SHALL define all 4 invariants with `id`, `semantics`, `applies_to` keys
- **AND** the file SHALL reference ADR-0033 for git probe behavior

#### Scenario: contract version field for evolution

- **WHEN** the contract YAML is modified in future
- **THEN** the `schema_version` field SHALL be bumped
- **AND** all 3 implementations + 2 compliance tests SHALL be re-verified

### Requirement: bash-helper-satisfies-contract

`skills/_lib/orchestrator_entry.sh::_resolve_project_root` (line 33-40) SHALL satisfy all 4 contract invariants.

#### Scenario: bash helper returns env override

- **WHEN** `RDDF_PROJECT_ROOT=/explicit/path` env var is set
- **AND** bash helper `_resolve_project_root` is invoked
- **THEN** the helper SHALL return `/explicit/path`

#### Scenario: bash helper returns git toplevel

- **WHEN** `RDDF_PROJECT_ROOT` env var is unset
- **AND** cwd is inside a git repo
- **THEN** the helper SHALL return `git rev-parse --show-toplevel` output (submodule-aware per ADR-0033)

#### Scenario: bash helper returns cwd as fallback

- **WHEN** `RDDF_PROJECT_ROOT` env var is unset
- **AND** cwd is NOT inside any git repo
- **THEN** the helper SHALL return `$PWD` (cwd as-is)

### Requirement: python-wrapper-satisfies-contract

`skills._lib._python_resolve_project_root.resolve_project_root` (shipped commit 281423d) SHALL satisfy all 4 contract invariants, behaving identically to the bash helper under identical conditions.

#### Scenario: python wrapper returns env override

- **WHEN** `RDDF_PROJECT_ROOT=/explicit/path` env var is set
- **THEN** `skills._lib._python_resolve_project_root.resolve_project_root()` SHALL return `/explicit/path`

#### Scenario: python wrapper returns git toplevel (in git repo)

- **WHEN** `RDDF_PROJECT_ROOT` env var is unset
- **AND** cwd is inside a git repo
- **THEN** the wrapper SHALL delegate to `_lib.cli.__main__.resolve_project_root()` which returns git toplevel

#### Scenario: python wrapper returns cwd fallback (non-git)

- **WHEN** `RDDF_PROJECT_ROOT` env var is unset
- **AND** cwd is NOT inside any git repo
- **THEN** the wrapper SHALL return `os.getcwd()` as-is

### Requirement: python-cli-satisfies-contract

`_lib.cli.__main__.resolve_project_root` (per ADR-0033) SHALL satisfy all 4 contract invariants, with one documented exception: invariant_env_override is NOT supported by default in the CLI layer (callers must set env var before invoking if override needed; contract documents this layer-specific behavior).

#### Scenario: python CLI returns git toplevel

- **WHEN** `RDDF_PROJECT_ROOT` env var is unset
- **AND** cwd is inside a git repo
- **THEN** `_lib.cli.__main__.resolve_project_root()` SHALL return git toplevel

#### Scenario: python CLI returns cwd fallback

- **WHEN** `RDDF_PROJECT_ROOT` env var is unset
- **AND** cwd is NOT inside any git repo
- **THEN** the CLI resolver SHALL return `os.getcwd()` as-is

