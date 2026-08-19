## ADDED Requirements

### Requirement: RFC Draft Interview Generates Local Draft File

`rddf rfc-draft <name>` MUST run an interactive bash interview (title, stakeholders, gate, contract-impact, draft path) and atomically write `.rddf/state/.rfc-draft-<name>.json` conforming to `rfc_draft_schema.json` v1.

#### Scenario: Interview covers all required fields
**WHEN** user runs `rddf rfc-draft <name>`

**THEN** the interview MUST prompt for (in order): title, stakeholders (comma-separated), gate (default `Design-Gate`), contract-impact (default `Breaking-Change`), contract-draft path

**AND** MUST write a v1 schema-compliant JSON to `.rddf/state/.rfc-draft-<name>.json`

#### Scenario: Empty stakeholder rejected with retry
**WHEN** user submits empty stakeholders list

**THEN** the interview MUST re-prompt for stakeholders

**AND** MUST exit with code 3 if user re-submits empty 3 times

#### Scenario: Schema validation enforces required fields
**WHEN** the draft file is missing any required field (title / stakeholders / gate / contract_impact)

**THEN** `jsonschema` validation MUST fail

**AND** downstream `rddf rfc-create --from-draft` MUST refuse with exit 4

### Requirement: design-done Gate Enforces Draft Existence

`design_done_gate.py::check_rfc_draft` MUST return `True` (block) when a proposal in `openspec/changes/<name>/` has `category=cross-repo-federation` in its `roadmap-meta.yaml` and no `.rfc-draft-<name>.json` exists.

#### Scenario: Cross-repo proposal without draft blocks design-done
**WHEN** `openspec/changes/add-cross-repo-impact-detection/roadmap-meta.yaml` has `category: cross-repo-federation`

**AND** `.rddf/state/.rfc-draft-add-cross-repo-impact-detection.json` does not exist

**THEN** `check_rfc_draft` MUST return `True`

**AND** `check_design_done_gate()` MUST exit 1

#### Scenario: Draft present allows design-done
**WHEN** the corresponding draft JSON exists and passes schema validation

**THEN** `check_rfc_draft` MUST return `False`

#### Scenario: Non-cross-repo proposals skip draft gate
**WHEN** a proposal has `category != cross-repo-federation`

**THEN** `check_rfc_draft` MUST return `False` regardless of draft file existence
