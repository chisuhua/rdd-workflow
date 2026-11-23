# fix-p3-verifier-gate Specification

## Purpose
Make the builder's archive phase refuse to archive a change whose acceptance criteria
have not been verified: the archive gate runs before the archive, a missing or stale
verdict cache fails the phase with actionable guidance, and the skip switch only works
when the operator records a reason.
## Requirements
### Requirement: phase3-runs-the-archive-gate-before-archiving

The archive phase SHALL run the archive gate before it archives, and SHALL NOT contain a
path on which an unset verifier exit code lets the archive through.

#### Scenario: the phase has no default pass on the verifier exit code

- **WHEN** the source of `phase3_archive.sh` is inspected
- **THEN** it SHALL NOT contain a path that lets the archive proceed when the verifier
  exit code is still at its initial value

### Requirement: no-verifier-run-reference-in-code

The `skills/` and `_lib/` trees SHALL NOT reference the removed `verifier_run` entry
point. Historical artefacts under `.rddf/plans/` and `.rddf/reviews/` are out of scope.

#### Scenario: no verifier_run reference remains in the code trees

- **WHEN** `skills/` and `_lib/` are searched for `verifier_run`
- **THEN** no reference SHALL be found

### Requirement: archive-gate-runs-when-openspec-is-untracked

The archive gate SHALL be enforced on the untracked-`openspec` path too — a change whose
verdict cache is missing SHALL be refused there as well.

#### Scenario: an untracked-openspec archive without a verdict cache is refused

- **WHEN** the archive phase archives a change while `openspec` is untracked and no
  verdict cache exists
- **THEN** the archive SHALL be refused

### Requirement: missing-verdict-cache-fails-phase3-with-recovery-hints

When the verdict cache is missing or incomplete, the phase SHALL exit non-zero and its
message SHALL list the ways out: run the verifier, skip with a reason, or check the cache
location.

#### Scenario: a missing verdict cache fails the phase with guidance

- **WHEN** the archive phase archives a change whose verdict cache is missing
- **THEN** the phase SHALL exit non-zero
- **AND** the message SHALL name the verifier, the skip switch with a reason, and the
  cache location

#### Scenario: an incomplete verdict cache fails the phase

- **WHEN** the archive phase archives a change whose verdict cache does not cover its
  acceptance criteria
- **THEN** the phase SHALL exit non-zero

### Requirement: skip-rdd-verifier-requires-a-bypass-reason

`SKIP_RDD_VERIFIER=yes` SHALL only bypass the gate when `RDDF_VERIFIER_BYPASS_REASON` is
also set; without a reason the phase still fails closed, and with a reason the bypass is
recorded in the bypass audit log.

#### Scenario: skipping without a reason still fails closed

- **WHEN** `SKIP_RDD_VERIFIER=yes` is set without `RDDF_VERIFIER_BYPASS_REASON`
- **THEN** the archive phase SHALL fail closed

#### Scenario: skipping with a reason passes and is audited

- **WHEN** `SKIP_RDD_VERIFIER=yes` and `RDDF_VERIFIER_BYPASS_REASON=<text>` are both set
- **THEN** the archive phase SHALL proceed
- **AND** the bypass SHALL be written to `.bypass-audit.jsonl`

### Requirement: stale-verdict-cache-blocks-the-archive

A verdict cache whose `codebase_commit` does not match the branch tip SHALL NOT let the
archive through.

#### Scenario: a stale verdict cache blocks the archive

- **WHEN** the archive phase archives a change whose verdict cache records a
  `codebase_commit` that differs from the branch tip
- **THEN** the archive SHALL be refused

### Requirement: strict-ac-gate-blocks-a-cached-ac-failure

A verdict cache that records a failed acceptance criterion SHALL block the archive
while the strict gate is enabled.

#### Scenario: a cached AC failure blocks the archive under the strict gate

- **WHEN** the archive gate runs against a verdict cache whose recorded acceptance
  criterion failed, with `STRICT_AC_GATE=yes`
- **THEN** the gate SHALL block the archive
- **AND** the message SHALL state that the AC verification failed under the strict gate
