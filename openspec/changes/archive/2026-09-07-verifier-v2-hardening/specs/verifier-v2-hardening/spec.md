## ADDED Requirements

### Requirement: validate_verdict_completeness SHALL enforce verdict-length-equals-AC-count

The system SHALL provide `validate_verdict_completeness(verdict, acs)` in `_lib/verifier/protocol.py`. The function SHALL validate:
- `len(verdict) == len(acs)` (length match)
- `ac_id` set equality: every `ac.ac_id` appears exactly once in verdict; no unknown ac_id; no duplicates.

When `validate_verdict_completeness` returns non-empty problems, `run_one_change` MUST mark `state="failed"`, skip verdict cache write, and `archive_gate_check` MUST fail closed.

#### Scenario: verdict length matches AC count → pass

- **GIVEN** a proposal with 3 ACs (AC-1, AC-2, AC-3)
- **AND** the agent emits verdict `[{"ac_id":"AC-1","status":"pass"},{"ac_id":"AC-2","status":"pass"},{"ac_id":"AC-3","status":"pass"}]`
- **WHEN** `validate_verdict_completeness` is called
- **THEN** it returns empty problems list
- **AND** `run_one_change` proceeds with cache write

#### Scenario: verdict shorter than AC count → fail closed

- **GIVEN** a proposal with 5 ACs
- **AND** the agent emits verdict `[{"ac_id":"AC-1","status":"pass"}]` (only 1 of 5)
- **WHEN** `run_one_change` reads the verdict
- **THEN** `validate_verdict_completeness` returns problems `["missing AC-2", "missing AC-3", ...]`
- **AND** `state` is marked `failed` with `failed_acs` listing missing AC IDs
- **AND** `verdict_cache()` write is SKIPPED

#### Scenario: archive gate rejects incomplete cache

- **GIVEN** `.rddf/state/.ac-verdict-<change>.json` exists with `verdict` shorter than `ac_count`
- **AND** cache SHA matches current HEAD
- **WHEN** `archive_gate_check` consumes the cache
- **THEN** the gate fails closed with error message citing "verdict incomplete (3 of 5 ACs verified)"
- **AND** archive is blocked

#### Scenario: unknown ac_id in verdict → fail

- **GIVEN** proposal has AC-1, AC-2
- **AND** verdict contains `{"ac_id":"AC-9","code"}` (unknown) but no AC-2
- **WHEN** `validate_verdict_completeness` is called
- **THEN** problems include `["AC-9: unknown ac_id", "AC-2: missing"]`
- **AND** the verdict is rejected

#### Scenario: duplicate ac_id in verdict → fail

- **GIVEN** verdict `[{"ac_id":"AC-1","code"},{"ac_id":"AC-1","code"}]` (duplicate AC-1)
- **WHEN** `validate_verdict_completeness` is called
- **THEN** problems include `["AC-1: duplicate ac_id"]`
- **AND** the verdict is rejected

### Requirement: VERDICT_ITEM_SCHEMA SHALL be strict on evidence and reasoning

The `VERDICT_ITEM_SCHEMA` in `_lib/verifier/protocol.py` SHALL enforce:
- `evidence` array `minItems: 1` (non-empty)
- `reasoning` string `minLength: 1` (non-empty)
- `status: "fail"` MUST have reasoning containing at least one of `DRIFT_KEYWORDS` or `GAP_KEYWORDS`
- `status: "partial"` MUST have reasoning containing at least one keyword (same rule)

`pass` status does NOT require keyword in reasoning (passes don't route).

#### Scenario: pass with empty evidence → invalid

- **GIVEN** verdict item `{"ac_id":"AC-1","status":"pass","confidence":0.9,"evidence":[],"reasoning":"ok"}`
- **WHEN** `validate_verdict_items` is called
- **THEN** problems include `["AC-1: evidence empty (pass requires ≥1 tool call)"]`
- **AND** the item is flagged invalid

#### Scenario: fail without keyword → invalid

- **GIVEN** verdict item `{"ac_id":"AC-1","status":"fail","confidence":0.9,"evidence":[{"tool":"Read","query":"x","result_summary":"y"}],"reasoning":"Handler is broken"}`
- **WHEN** `validate_verdict_items` is called
- **THEN** problems include `["AC-1: fail reasoning must contain drift/gap keyword"]`
- **AND** `classify_failure` would default to `implementation_gap` (conservative); failure is flagged at verdict-write time

#### Scenario: fail with drift keyword → valid

- **GIVEN** verdict item `{"ac_id":"AC-1","status":"fail","confidence":0.9,"evidence":[{"tool":"Read","query":"x","result_summary":"y"}],"reasoning":"Handler exists but does not match AC"}`
- **WHEN** `validate_verdict_items` is called
- **THEN** problems list is empty
- **AND** `classify_failure` returns `proposal_drift`

### Requirement: stage_verification_context SHALL be atomic

`_lib/verifier/protocol.py::stage_verification_context` SHALL write the context file via temp-file + atomic rename (POSIX `os.replace` / `Path.replace`) to prevent interleaving when two processes stage the same change concurrently.

#### Scenario: atomic write under concurrent staging

- **GIVEN** two `stage_verification_context` calls for the same change running concurrently
- **WHEN** both attempts complete
- **THEN** the resulting context file is one of the two full writes (never a partial concatenation)
- **AND** no temp files (`rdd-verify-context-<change>.json.tmp`) remain

### Requirement: read_verdict_cache SHALL fail closed on unknown schema_version

`_lib/verifier/cache.py::read_verdict_cache` SHALL return None when:
- `schema_version` is missing
- `schema_version == 1` (ac-verifier era, deprecated)
- `schema_version` is unknown (e.g., 3+)

A `None` return forces `run_one_change` and `archive_gate_check` to treat the cache as stale/missing (fail closed).

#### Scenario: read schema_version=1 cache

- **GIVEN** `.rddf/state/.ac-verdict-ch.json` content `{"schema_version":1,"change":"ch",...}`
- **WHEN** `read_verdict_cache` is called
- **THEN** it returns None
- **AND** `archive_gate_check` fails closed with "cache schema_version=1 deprecated; run rddf rdd-verify"

#### Scenario: read missing schema_version

- **GIVEN** cache file with no `schema_version` field
- **WHEN** `read_verdict_cache` is called
- **THEN** it returns None

### Requirement: jsonschema absence SHALL be visible, not silent

When `jsonschema` is unavailable (`ImportError`), `validate_verdict_items` SHALL log a warning and return the verdict items as `valid` with a single problem `"schema validator unavailable; structural-only check applied"` — never silently accept. The structural fallback (regex `ac_id` + enum `status`) is best-effort.

#### Scenario: jsonschema unavailable + invalid ac_id

- **GIVEN** `jsonschema` not installed
- **AND** verdict `[{"ac_id":"ac1","status":"pass","confidence":0.5}]`
- **WHEN** `validate_verdict_items` is called
- **THEN** structural check flags `"ac1: bad ac_id"` (passes)
- **AND** problems include `"schema validator unavailable; structural-only check applied"`

### Requirement: run_one_change exit-2 SHALL map to pending (not halted)

`_lib/cli/rdd_verify_cmd.py::run_one_change` SHALL map `runner` exit_code 2 to `state="pending"`, `route="pending-agent"`, with `verdict_cache()` write skipped and audit `pending` event written. This aligns with `rddf ac-verify` shim's exit-2 semantic (benign skip when proposal missing).

`aggregate_exit` SHALL keep `pending` at priority 0 (does not block batch).

#### Scenario: proposal missing during batch run

- **GIVEN** queue contains change A (proposal exists) and change B (no proposal.md)
- **WHEN** `rddf rdd-verify` runs
- **THEN** A processes normally (passed/failed based on runner)
- **AND** B is marked `state=pending`, `route=pending-agent`
- **AND** aggregate exit is 0 (pending does not block)
- **AND** A's outcome is not affected by B's missing proposal

### Requirement: rdd-cli SHALL use `_lib.*` imports exclusively

New and modified code in `_lib/cli/rdd_verify_cmd.py` SHALL import via `_lib.verifier.*` paths, not the deprecated `skills._lib.verifier.*` shim path. Per AGENTS.md rule 25.

#### Scenario: rdd_verify_cmd.py has no skills._lib imports

- **WHEN** `_lib/cli/rdd_verify_cmd.py` is grep'd for `from skills._lib`
- **THEN** no matches

### Requirement: planner SHALL expose scan_deprecated_skills helper

`_lib/planner_*.py` SHALL provide `scan_deprecated_skills(skills_dir: Path) -> list[dict]` that reads `skills/<name>/SKILL.md` frontmatter and returns list of `{name, reason, removal_target, migration}` for skills with `metadata.deprecated` or `user-invocable: false`.

The propose step flow SHALL call this and surface the list in proposal-suggestions.md output (non-blocking).

#### Scenario: scan returns ac-verifier as deprecated

- **GIVEN** `skills/ac-verifier/SKILL.md` has `metadata.deprecated.deprecated_in: "rdd-verifier v2.0 (2026-09-07, per ADR-0045)"`
- **WHEN** `scan_deprecated_skills` is called
- **THEN** result includes `{"name":"ac-verifier","reason":"...","removal_target":"next minor release after 2.0","migration":"..."}`
- **AND** the propose flow displays this as a suggestion (not blocking)

### Requirement: verifier-protocol-template SHALL be documented for cross-stage reuse

`docs/superpowers/specs/verifier-protocol-template.md` SHALL document the shared pattern: SKILL.md § Protocol + `_lib/<phase>/protocol.py` data layer + staged context + agent writeback + SHA cache + fail-closed gate. Includes:
- staged context file naming convention (`rdd-<phase>-context-<change>.json`)
- cache schema v2 cross-stage consistency requirements
- fail-closed gate semantics (cache missing → blocked + audited bypass)

#### Scenario: template spec exists

- **WHEN** `docs/superpowers/specs/verifier-protocol-template.md` is read
- **THEN** it documents the 5-section pattern with at least one naming convention, schema reference, and gate semantic

### Requirement: remove-ac-verifier-completely SHALL be scheduled with manual_deps

The `remove-ac-verifier-completely` change SHALL be registered in `openspec/changes/` skeleton with `manual_deps: [inline-ac-verifier-into-rdd-verifier, verifier-v2-hardening]` in its `roadmap-meta.yaml`. The change deletes `skills/ac-verifier/` + scripts + providers + mocks, removes `_default_runner` alias, makes ac-verify CLI route emit friendly error, and strips deprecation banners from test files.

#### Scenario: skeleton change has correct manual_deps

- **WHEN** `openspec/changes/remove-ac-verifier-completely/roadmap-meta.yaml` is read
- **THEN** `manual_deps` lists both `inline-ac-verifier-into-rdd-verifier` and `verifier-v2-hardening`