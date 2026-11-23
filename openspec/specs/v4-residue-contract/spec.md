# v4-residue-contract Specification

## Purpose
TBD - created by archiving change fix-v4-residue-contract. Update Purpose after archive.

## Requirements

### Requirement: verification-failure-routes-to-v4-stages

When a change fails acceptance verification, the recorded route MUST name an existing v4 stage. Both an `implementation_gap` classification and a `proposal_drift` classification MUST route to `rdd-builder`; the difference between rewriting the proposal and fixing the implementation MUST be carried by the recorded classification, not by the route value. The route MUST NOT be a removed v3 skill name. The skill-level writer and the CLI classifier MUST apply the same mapping.

#### Scenario: implementation gap routes to builder

- GIVEN a change whose acceptance criteria failed because code is missing
- WHEN `route_loop.sh <change> implementation_gap` runs
- THEN the persisted `route` is `rdd-builder`
- AND the printed route line does not contain `guide-`

#### Scenario: proposal drift routes to builder

- GIVEN a change whose acceptance criteria failed because the implementation contradicts the proposal
- WHEN `route_loop.sh <change> proposal_drift` runs
- THEN the persisted `route` is `rdd-builder`
- AND the printed route line does not contain `guide-`
- AND the printed route line states that the proposal has to be rewritten

#### Scenario: CLI classifier agrees with the skill-level writer

- GIVEN a verdict item classified as `implementation_gap`
- WHEN `_classify_route` is called
- THEN it returns `rdd-builder`

### Requirement: route-schema-enums-preserve-legacy-values

The JSON Schema enums that constrain the `route` field (`_lib/schemas/iteration_schema.json`, `_lib/schemas/verifier_loop_schema.json`) MUST accept both the v4 route names and the legacy v3 route names.

Schema enums MUST NOT remove a legacy value, because previously persisted verifier state files still carry it.

#### Scenario: legacy verifier state remains loadable

- GIVEN `.rddf/state/verifier/my-change.json` contains `"route": "guide-ship"`
<!-- v4-residue:allow=guard -->
- WHEN the state is validated against the schema
- THEN validation succeeds
- AND the route value is preserved as-is

#### Scenario: new route values are accepted

- GIVEN a verifier state file containing `"route": "rdd-builder"`
- WHEN the state is validated against the schema
- THEN validation succeeds

### Requirement: feedback-source-schema-matches-runtime

The `source` enum in `_lib/schemas/feedback_entry_schema.json` MUST equal the set of accepted sources in `_lib/feedback_appender.py::VALID_SOURCES`.

The two definitions MUST be kept in sync by an automated check that fails when either side changes without the other.

The enum MUST retain the legacy v3 source names, because historical feedback entries use them.

#### Scenario: schema advertises every accepted source

- GIVEN the runtime accepts sources `rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`, `human`, and the three legacy `guide-*` names
- WHEN `rddf feedback show-schema` is executed
- THEN the printed `source` enum contains all eight values

#### Scenario: drift between schema and runtime is detected

- GIVEN a source value present in the runtime set but missing from the schema enum
- WHEN the consistency test runs
- THEN the test fails

### Requirement: user-facing-text-references-existing-skills

User-visible output (CLI help text, error messages, example commands, empty-state prompts) MUST NOT instruct the user to invoke a skill that no longer exists.

Any instruction to run a workflow stage MUST name the corresponding v4 skill.

#### Scenario: gate error message names the current skill

- GIVEN the arch-done handoff is missing
- WHEN the gate check reports the error
- THEN the remediation text names `rdd-arch`
- AND it does not contain `guide-arch`
<!-- v4-residue:allow=guard -->

#### Scenario: CLI help contains no removed skill names

- GIVEN `rddf --help` and `rddf sessions --help` output
- WHEN the output is scanned for `guide-arch`, `guide-plan`, `guide-ship`, `guide-design`
<!-- v4-residue:allow=guard -->
- THEN no match is found

#### Scenario: historical comments are not treated as user-facing text

- GIVEN a source comment that references a historical file name such as `guide-ship.md:447`
<!-- v4-residue:allow=guard -->
- WHEN the residue check runs
- THEN the comment does not produce a finding

### Requirement: v4-residue-doctor-category

`rdd-doctor` MUST provide a `v4-residue` category that detects references to removed v3 skills on contract-bearing surfaces: routing-type JSON Schema enums, user-facing string literals in library code, and the `name` field of skill frontmatter.

A routing enum MUST be reported when it cannot express any v4 route value, because every route it can express then points at a removed skill.

A finding on a routing enum or a skill name MUST be CRITICAL; a finding in user-facing text MUST be WARNING.

#### Scenario: routing enum without any v4 route value is reported

- GIVEN a routing enum in a JSON Schema that contains only removed skill names
- WHEN the `v4-residue` category runs
- THEN a CRITICAL finding is produced for that schema file

#### Scenario: routing enum keeping legacy values alongside v4 values is not reported

- GIVEN a routing enum that contains `rdd-builder`, `rdd-planner` and the historical `guide-ship`
<!-- v4-residue:allow=guard -->
- WHEN the `v4-residue` category runs
- THEN no finding is produced for that enum

#### Scenario: skill frontmatter with a removed name is reported

- GIVEN a `skills/<name>/SKILL.md` whose frontmatter `name` is `guide-plan`
<!-- v4-residue:allow=guard -->
- WHEN the `v4-residue` category runs
- THEN a CRITICAL finding is produced for that file

### Requirement: v4-residue-scan-exclusions

The `v4-residue` category MUST NOT scan historical record directories (`docs/`, `.rddf/`, `tests/`, `openspec/`).

Surfaces that legitimately accept historical values MUST be explicitly allowlisted, and the allowlist MUST be asserted by tests.

User-facing text detection MUST inspect string literals only, so that historical references inside comments and docstrings are not reported.

#### Scenario: legacy feedback sources are not reported

- GIVEN the feedback source enum contains `guide-design`
<!-- v4-residue:allow=guard -->
- WHEN the `v4-residue` category runs
- THEN no finding is produced for that enum

#### Scenario: historical documents are out of scope

- GIVEN a file under `docs/adr/` whose content mentions `guide-design`
<!-- v4-residue:allow=guard -->
- WHEN the `v4-residue` category runs
- THEN no finding is produced for that file

#### Scenario: a removed skill name inside a comment is not reported

- GIVEN a source comment that contains `skill_use("guide-plan")`
<!-- v4-residue:allow=guard -->
- WHEN the `v4-residue` category runs
- THEN no finding is produced for that file

#### Scenario: a removed skill name inside a string literal is reported

- GIVEN a source line whose string literal is `skill_use("guide-plan")`
<!-- v4-residue:allow=guard -->
- WHEN the `v4-residue` category runs
- THEN a WARNING finding is produced for that file

### Requirement: schema-path-guard-scans-code

The canonical schema path check MUST scan application code, not only documentation.

It MUST report references to `skills/_lib/schemas/` found in Python sources under `_lib/` and `skills/`, while continuing to allow that string inside an explicit shim-compatibility parenthetical.

#### Scenario: stale schema path in a source comment is reported

- GIVEN a Python file under `_lib/` whose comment references `skills/_lib/schemas/`
- WHEN the canonical schema path check runs
- THEN a WARNING finding is produced for that file

#### Scenario: documentation allowlist still works

- GIVEN `AGENTS.md` mentions `skills/_lib/schemas/` only inside a shim-compatibility parenthetical
- WHEN the canonical schema path check runs
- THEN no finding is produced for `AGENTS.md`
