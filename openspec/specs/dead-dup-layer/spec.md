# dead-dup-layer Specification

## Purpose
TBD - created by archiving change remove-dead-dup-layer. Update Purpose after archive.

## Requirements

### Requirement: shim-layer-contains-no-duplicate-implementations

The `skills/_lib/` directory MUST contain only compatibility shims. It MUST NOT contain complete copies of canonical modules.

The `skills/_lib/` directory MUST NOT contain JSON schema files, because JSON documents cannot be identity-merged.

A Python file under `skills/_lib/` that exceeds the shim size threshold MUST appear in an explicit allow-list together with a non-empty rationale, and every allow-list entry MUST reference a file that exists.

#### Scenario: duplicate iteration modules are removed

- GIVEN `skills/_lib/iteration/` contained copies of `store.py`, `schema.py`, `render.py`, `repair.py`, `l2.py`, `archive_sidecar.py`, `post_archive.py`
- WHEN the duplicate layer is removed
- THEN only `skills/_lib/iteration/__init__.py` remains
- AND `import skills._lib.iteration.store` resolves to `_lib/iteration/store.py`

#### Scenario: the shim layer holds no JSON documents

- GIVEN the canonical schema location is `_lib/schemas/`
- WHEN `skills/_lib/` is scanned for `*.json`
- THEN no file is found

#### Scenario: an oversized file without an allow-list entry is reported

- GIVEN a Python file under `skills/_lib/` that exceeds the shim size threshold
- WHEN the file is not listed in the allow-list
- THEN the structural check reports it

#### Scenario: every allow-list entry exists and carries a rationale

- GIVEN the allow-list of oversized shim files
- WHEN each entry is inspected
- THEN the referenced file exists
- AND the rationale is non-empty

### Requirement: removed-schema-directory-is-not-importable

The removed schema directory MUST NOT be importable as a module from the shim layer, and the check MUST isolate the shim layer's global fallback path so the result does not depend on whether a global installation is present.

#### Scenario: the removed schema directory cannot be imported

- GIVEN the shim package search path is restricted to the repository's `skills/_lib/`
- WHEN `skills._lib.schemas` is imported
- THEN the import fails

### Requirement: canonical-schemas-are-the-single-source

Every JSON Schema consumed by the project MUST exist under `_lib/schemas/`, and `skills/_lib/schemas/` MUST NOT exist.

Schemas that exist only in the shim directory MUST be moved to the canonical location with byte-identical content, and the curated schema index MUST list every canonical schema and no other.

#### Scenario: shim-only schemas are moved to the canonical location

- GIVEN `populate_state_schema.json`, `populate_supplementary_schema.json` and `rfc_draft_schema.json` exist only under `skills/_lib/schemas/`
- WHEN the duplicate layer is removed
- THEN all three exist under `_lib/schemas/`
- AND their content is byte-identical to the previous copies

#### Scenario: the schema index matches the canonical directory

- GIVEN the canonical directory contains N schema files
- WHEN the schema index in `docs/schemas/README.md` is compared with the directory
- THEN the referenced set and the on-disk set are equal in both directions

### Requirement: schema-validation-paths-resolve-to-real-files

A schema path computed from a module's own location MUST resolve to an existing file inside the project.

When such a path does not resolve, the dependent validation MUST NOT be silently skipped.

#### Scenario: populate state schema path resolves

- GIVEN the module `populate_lib.py` computes the path of `populate_state_schema.json`
- WHEN the path is evaluated
- THEN the resolved path exists on disk

#### Scenario: populate payload validation is actually executed

- GIVEN the canonical schema files are present
- WHEN a populate payload is written
- THEN the payload is validated against the schema
- AND the validation is not skipped because the schema file was missing

### Requirement: stale-registrations-and-proxies-are-removed

Module registrations and proxy modules MUST NOT point at directories that do not exist, and MUST NOT reference skill names removed by the v4 rename.

#### Scenario: dash-bridge registrations resolve

- GIVEN the dash-bridge list in the CLI package initializer and the pytest conftest
- WHEN every registered target directory is checked
- THEN every target directory exists

#### Scenario: proxies do not point at removed skills

- GIVEN a proxy module under `skills/` that re-exports a package through `__path__`
- WHEN its target directory is checked
- THEN the target directory exists

### Requirement: schema-tests-target-canonical-files

Schema tests MUST validate the canonical schema files, and MUST NOT assert a hard-coded count of schema files.

Every canonical schema MUST declare a top-level `version` annotation whose constant is one of the accepted metadata versions, positioned after the `$schema` keyword.

#### Scenario: canonical schema is validated

- GIVEN a schema test that loads `arch_handoff_schema.json`
- WHEN the test runs
- THEN the loaded file is the one under `_lib/schemas/`

#### Scenario: no hard-coded schema count

- GIVEN the schema-version test
- WHEN the schema list is built
- THEN it is discovered from the canonical directory
- AND the test contains no assertion on the number of schemas

#### Scenario: every canonical schema declares a version annotation

- GIVEN the canonical schema directory
- WHEN each schema file is parsed
- THEN each one has a top-level `version` object with an accepted constant
- AND that object appears after the `$schema` keyword

#### Scenario: every canonical schema is valid JSON

- GIVEN the canonical schema directory
- WHEN each schema file is parsed as JSON
- THEN no parse error occurs
