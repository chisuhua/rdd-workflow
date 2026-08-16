# contract-cache: Specifications

> Source: `_lib/schemas/contract_cache_schema.json` v1
> Change: add-cross-repo-state-schemas

## ADDED Requirements

### Requirement: Hub contract version caching

The system SHALL cache Hub contract versions and SHA-256 checksums for offline fallback.

#### Scenario: Cache contract after Hub sync
- **WHEN** a sync with Hub completes
- **THEN** `.rddf/state/.contract-cache.json` is updated with new `contracts` array
- **AND** `last_sync` timestamp is updated
- **AND** `hub_repo` and `hub_ref` identify the sync source

#### Scenario: Use cached contract for offline work
- **WHEN** a Spoke works offline and needs to validate a contract
- **THEN** the local cache in `.contract-cache.json` provides version and checksum
- **AND** `sha256` allows integrity verification

#### Scenario: Contract sync from specific ref
- **WHEN** syncing from a specific branch or tag (e.g., `v1.2.0`)
- **THEN** `hub_ref` records the Git ref used

---

### Requirement: Contract cache entry validation

Contract cache entries MUST contain required fields and valid patterns.

#### Scenario: Valid contract entry
- **GIVEN** a contract entry with `path`, `sha256`, `format`, `version`
- **WHEN** schema validation runs
- **THEN** the entry passes validation

#### Scenario: Invalid SHA-256 checksum format
- **GIVEN** a contract entry with `sha256` not matching 64-char hex pattern
- **WHEN** schema validation runs
- **THEN** validation fails with pattern error

#### Scenario: Invalid contract path pattern
- **GIVEN** a contract entry with `path` not starting with `contracts/`
- **WHEN** schema validation runs
- **THEN** validation fails with pattern error

#### Scenario: Invalid format enum
- **GIVEN** a contract entry with `format` not in `openapi-3.0, openapi-3.1, protobuf-3, json-schema-draft-7`
- **WHEN** schema validation runs
- **THEN** validation fails with enum error

---

### Requirement: Contract cache file structure

The `.rddf/state/.contract-cache.json` file SHALL contain version, sync metadata, and contracts array.

#### Scenario: File contains required top-level fields
- **WHEN** the cache file is read
- **THEN** it contains `version` (const: 1), `last_sync`, and `contracts` array

#### Scenario: Empty contracts array when no contracts synced
- **WHEN** no contracts have been synced from Hub
- **THEN** `contracts` is an empty array `[]`
