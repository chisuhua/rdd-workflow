# spec-delta-generator-fidelity Specification

## Purpose
TBD - created by archiving change fix-proposal-generator-output-fidelity. Update Purpose after archive.

## Requirements

### Requirement: spec-delta-generation-is-opt-in

The delta generator MUST generate a change-local spec delta **only when the improvement declares a `delta` head line**. When the declaration is absent it MUST skip generation (leaving no delta artifact behind) and MUST NOT be treated as a failure, so that improvements predating this contract keep working. When the declaration is present but the semantic-requirement carrier is missing or incomplete, generation MUST be refused with a non-zero exit code naming what is missing.

#### Scenario: no declaration means no delta and no failure

- GIVEN an improvement without a `delta` head line
- WHEN the approval pipeline runs
- THEN no delta file is written for the change
- AND the pipeline does not fail (the proposal is still produced)

#### Scenario: declared delta with incomplete carrier is refused

- GIVEN an improvement declaring a `delta` head line but omitting the semantic requirement carrier
- WHEN the delta generator is invoked
- THEN generation is refused with a non-zero exit code
- AND the diagnostic names the missing carrier

### Requirement: spec-delta-shape-guard

Before writing a change-local spec delta, the generator MUST reject the draft when it contains a machine-generated requirement name of the form `acceptance-<n>` or `capability-<n>`, or a tautological scenario `WHEN` clause of the form `the change is applied` / `the feature is applied` / `it is applied`. The guard MUST use the same predicate module as the repository's existing requirement-form guard, so that the producer and the checker cannot drift apart.

#### Scenario: machine-generated requirement name is rejected

- GIVEN an improvement whose acceptance criteria can only be rendered as `acceptance-1`, `acceptance-2`, …
- WHEN the delta generator renders the change-local spec delta
- THEN the generation is refused with a non-zero exit code
- AND the diagnostic names the offending requirement name

#### Scenario: tautological WHEN clause is rejected

- GIVEN an improvement whose acceptance criteria render to a scenario whose `WHEN` is `the change is applied`
- WHEN the delta generator renders the change-local spec delta
- THEN the generation is refused with a non-zero exit code
- AND the diagnostic names the offending scenario

#### Scenario: guard predicate is shared with the checker

- GIVEN the shared requirement-form predicate module used by the repository's form guard
- WHEN the delta generator and the form guard are inspected
- THEN both import the same predicate definitions
- AND a second, divergent copy of the predicates does not exist

### Requirement: spec-delta-semantic-requirement-carrier

The improvement MUST be able to carry a **semantic requirement** that the delta generator renders into a requirement with a non-tautological scenario. The carrier is a **bold head line** (`**语义要求**: name | body | scenario | WHEN | THEN`, entries separated by `;;`). When the carrier is absent or a field is missing the generator MUST refuse and name what is missing — it MUST NOT fall back to machine-generated names.

#### Scenario: semantic requirement renders a meaningful requirement

- GIVEN an improvement carrying the bold head line `**语义要求**: family-domain-has-four-values | CEP SHALL 以锁定表为唯一真源 | 用户声明来源族 | the CEP instance declares its source family | the family domain has exactly four values`
- WHEN the delta generator renders the change-local spec delta
- THEN the delta contains `### Requirement: family-domain-has-four-values`
- AND the corresponding scenario's `WHEN` and `THEN` equal the author's texts (not a tautology)

#### Scenario: missing carrier is refused with a named diagnostic

- GIVEN an improvement without any semantic requirement carrier
- WHEN the delta generator renders the change-local spec delta
- THEN the generation is refused with a non-zero exit code
- AND the diagnostic names the missing carrier

#### Scenario: carrier with a missing field is refused

- GIVEN an improvement whose semantic requirement omits the `THEN` field
- WHEN the delta generator renders the change-local spec delta
- THEN the generation is refused with a non-zero exit code
- AND the diagnostic names the incomplete entry

### Requirement: spec-delta-modified-target

When an improvement declares that the change modifies an existing capability, the delta generator MUST emit `## MODIFIED Requirements`, MUST place the delta under `specs/<target-capability>/`, and MUST copy the target requirement from the main spec **including every scenario the main spec already declares** (a dropped scenario aborts `openspec archive`).

#### Scenario: declared target yields a MODIFIED delta

- GIVEN an improvement declaring `delta: modified cep-core-contracts`
- WHEN the delta generator renders the change-local spec delta
- THEN the delta's first section header is `## MODIFIED Requirements`
- AND the delta is written to `specs/cep-core-contracts/spec.md`
- AND the requirement name matches the main spec exactly

#### Scenario: dropped existing scenario aborts generation

- GIVEN an improvement declaring a MODIFIED target whose main-spec requirement declares three scenarios
- WHEN the delta generator renders the delta with only two of them
- THEN the generation is refused with a non-zero exit code
- AND the diagnostic names the missing scenario

### Requirement: spec-delta-version-branch

The delta generator MUST detect the openspec CLI version with a **semantic** comparison (so that `1.14.3` is correctly greater than `1.7.0`) and MUST select the guard implementation accordingly: for versions that provide the native scenario-conservation check it MUST reuse that semantics, and for older versions it MUST implement the equivalent `missing == ∅` rule itself (a missing scenario list may be empty; new scenarios are allowed).

#### Scenario: modern openspec reuses native semantics

- GIVEN an environment whose openspec version is at least 1.7.0
- WHEN the delta generator selects its guard implementation
- THEN the native scenario-conservation semantics is used
- AND the version comparison is semantic, not lexicographic

#### Scenario: legacy openspec self-implements the same rule

- GIVEN an environment whose openspec version is older than 1.7.0
- WHEN the delta generator selects its guard implementation
- THEN it implements the equivalent rule itself
- AND a missing-scenario list of empty length is accepted while a non-empty one is refused

### Requirement: spec-delta-no-partial-artifact

When the delta generation is refused, the pipeline MUST NOT leave an empty or partial delta file behind, MUST NOT leave a half-written proposal behind, and MUST remain re-runnable: a subsequent run MUST be able to regenerate the delta.

#### Scenario: refusal leaves no empty delta file

- GIVEN a change whose delta generation is refused by the shape guard
- WHEN the pipeline finishes
- THEN no zero-length delta file exists for that change
- AND no half-written proposal exists for that change
- AND re-running the pipeline regenerates the delta attempt
