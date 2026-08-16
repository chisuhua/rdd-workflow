---
SCOPE: shared
STATUS: PROPOSED
DATE: 2026-08-16
CHANGE: add-contract-lint-ci-gate
RELATED: contract-lint (implements the diff engine for contract-lint capability)
---

# Capability: contract-diff-py

> Python module (`skills/_lib/contract_diff.py`) that wraps OpenAPI Diff library
> calls and Protobuf schema comparison, providing structured diff results for the
> `rddf contract-check` CLI. Complements `validate_delta_targets.py` for schema
> validation; contract-diff-py focuses on runtime contract-vs-implementation diffing.

## ADDED Requirements

### Requirement: contract_diff.py MUST provide DiffEngine class with run() method

The `skills/_lib/contract_diff.py` module MUST provide:

```python
class DiffEngine:
    def run(self, contract_path: Path, impl_path: Path, format: str = "openapi") -> DiffResult
```

`DiffResult` MUST be a dataclass with fields:
- `severity`: `Literal["Breaking-Change", "Non-Breaking", "New-Contract", "Identical"]`
- `diffs`: `List[DiffItem]` where each `DiffItem` has `type`, `path`, `message`
- `contract_sha`: `str`
- `impl_sha`: `str`

#### Scenario: DiffEngine.run() returns Breaking-Change result

- **WHEN** `DiffEngine().run(Path("auth-v2.yaml"), Path("src/api/auth.py"))` is called
- **AND** contract has required field `email` missing in impl
- **THEN** result severity is `"Breaking-Change"`
- **AND** result.diffs contains one DiffItem with type `"Breaking-Change"`

#### Scenario: DiffEngine.run() returns Identical for matching contract and impl

- **WHEN** `DiffEngine().run()` is called with perfectly matching contract and impl
- **THEN** result severity is `"Identical"`
- **AND** result.diffs is empty list

### Requirement: DiffEngine MUST auto-detect OpenAPI vs Protobuf format

The `DiffEngine` MUST:

1. Check `contract_path` for OpenAPI marker (`openapi:` in first 100 lines or `.yaml`/`.json` extension with OpenAPI content)
2. Check for Protobuf marker (`syntax = "proto3"` or `.proto` extension)
3. Raise `ValueError` for unsupported formats

#### Scenario: OpenAPI format auto-detected from content

- **WHEN** contract file contains `openapi: 3.0.0` in first 100 lines
- **THEN** DiffEngine uses OpenAPI Diff logic

#### Scenario: Protobuf format auto-detected from content

- **WHEN** contract file contains `syntax = "proto3"`
- **THEN** DiffEngine uses Protobuf comparison logic

#### Scenario: Unsupported format raises ValueError

- **WHEN** contract file is neither OpenAPI nor Protobuf
- **THEN** `ValueError("Unsupported contract format: must be OpenAPI 3.0+ or Protobuf 3+")` is raised

### Requirement: DiffEngine MUST compute SHA256 for both contract and impl files

The `DiffEngine.run()` method MUST:

1. Compute SHA256 of `contract_path` content (for caching)
2. Compute SHA256 of `impl_path` content
3. Include both in `DiffResult`

#### Scenario: SHA256 computed and included in result

- **WHEN** `DiffEngine().run()` is called with valid files
- **THEN** result.contract_sha is a 64-character hex string (SHA256)
- **AND** result.impl_sha is a 64-character hex string (SHA256)

### Requirement: DiffEngine MUST use openapi-diff library for OpenAPI comparison

The DiffEngine SHALL use the `openapi-diff` library to compute:

- Added/removed/changed paths
- Added/removed/changed request body fields
- Added/removed/changed response fields
- Breaking vs non-breaking classification based on `openapi-diff` semantic rules

`openapi-diff` is an external dependency. Installation is handled by `requirements.txt`.

#### Scenario: openapi-diff library used for OpenAPI Breaking-Change detection

- **WHEN** DiffEngine.run() is called with an OpenAPI contract
- **THEN** openapi-diff library is invoked to compute the diff
- **AND** breaking changes are classified with Breaking-Change severity

#### Scenario: openapi-diff library used for OpenAPI Non-Breaking detection

- **WHEN** DiffEngine.run() is called with an OpenAPI contract that has only additions
- **THEN** openapi-diff library identifies Non-Breaking changes
- **AND** no Breaking-Change is reported

### Requirement: DiffEngine MUST use protobuf reflection for Protobuf comparison

The DiffEngine SHALL parse `.proto` files using `protobuf` library and SHALL compare message types, fields, and services against the implementation (`.pb.go`, `.pb.swift`, etc.). The DiffEngine SHALL classify differences appropriately.

#### Scenario: Protobuf message field difference detected

- **WHEN** DiffEngine.run() is called with a Protobuf contract
- **AND** the implementation has a missing field
- **THEN** a DiffItem with appropriate severity is added to the result

#### Scenario: Protobuf message fields match

- **WHEN** DiffEngine.run() is called with matching Protobuf contract and impl
- **THEN** result severity is Identical

### Requirement: contract_diff.py MUST provide format_output() function for Markdown/JSON

The `contract_diff.py` module SHALL provide a `format_output()` function that accepts a DiffResult and format string. When format is `"markdown"` it SHALL return human-readable markdown with emoji indicators (✅ ⚠️ ❌). When format is `"json"` it SHALL return a valid JSON string matching DiffResult schema.

```python
def format_output(result: DiffResult, format: str = "markdown") -> str
```

#### Scenario: Markdown format with Breaking-Change

- **WHEN** `format_output(result, "markdown")` is called with Breaking-Change severity
- **THEN** output contains `❌ Breaking-Change` and per-item diff lines

#### Scenario: JSON format output

- **WHEN** `format_output(result, "json")` is called
- **THEN** output is valid JSON matching DiffResult schema

### Requirement: contract_diff.py MUST be importable from skills._lib

The module SHALL be installable such that `from skills._lib.contract_diff import DiffEngine, format_output` works in both the rdd-workflow repo (where `_lib/` is in `skills/`) and third-party repos using global install (where `_lib/` is in `~/.agents/skills/_lib/`). This aligns with the existing pattern used by `validate_delta_targets.py`.

#### Scenario: Import works in rdd-workflow repo

- **WHEN** Python code runs from rdd-workflow root
- **AND** `from skills._lib.contract_diff import DiffEngine` is executed
- **THEN** DiffEngine class is successfully imported

#### Scenario: Import works after global install

- **WHEN** Python code runs from a third-party repo with global install
- **AND** `from skills._lib.contract_diff import DiffEngine` is executed
- **THEN** DiffEngine class is successfully imported

### Requirement: contract_diff.py unit tests MUST cover five key paths

The `tests/unit/test_contract_diff.py` MUST cover:

1. OpenAPI Breaking-Change detection
2. OpenAPI Non-Breaking addition detection
3. Protobuf format handling
4. Cache-hit path (SHA matching)
5. Hub-offline fallback (when Hub unreachable)
6. Breaking-Change detection in isolation

**Note**: These are the six paths mentioned in the proposal; the unit test covers all six scenarios.

#### Scenario: Unit test for Breaking-Change detection

- **WHEN** `pytest tests/unit/test_contract_diff.py` is run
- **THEN** test cases cover OpenAPI Breaking-Change, Non-Breaking, cache-hit, hub-offline, breaking-detect

### Requirement: contract_diff.py MUST reconcile with validate_delta_targets.py scope

The `contract_diff.py` module focuses on **runtime diff** (Hub contract vs local impl) while `validate_delta_targets.py` focuses on **static spec validation**. These modules SHALL operate independently with no code sharing. The `contract_diff.py` module SHALL NOT import or depend on `validate_delta_targets.py`.

#### Scenario: No import dependency between modules

- **WHEN** Python code imports `contract_diff.py`
- **AND** `validate_delta_targets.py` is examined
- **THEN** no import statement connects them

#### Scenario: Complementary purposes

- **WHEN** `validate_delta_targets.py` runs
- **THEN** it validates spec.md MODIFIED/RENAMED targets exist in `openspec/specs/`
- **WHEN** `contract_diff.py` runs
- **THEN** it validates runtime contract-vs-implementation consistency

## MODIFIED Requirements

(None)

## REMOVED Requirements

(None)

## RENAMED Requirements

(None)
