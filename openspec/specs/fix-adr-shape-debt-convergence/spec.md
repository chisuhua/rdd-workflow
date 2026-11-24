# fix-adr-shape-debt-convergence Specification

## Purpose

Define the contract that turns the ADR shape check from an always-opt-in warning into an incremental gate:
pre-existing shape debt is frozen in a per-file ledger, only debt outside that ledger fails, and the judging
criteria themselves are not relaxed. A gate that can never go green gets switched off — this one checks whether
new debt was added, not whether historical debt is gone.

## Requirements

### Requirement: The shape baseline MUST be a per-file ledger

`docs/adr/.adr-shape-baseline.json` MUST record frozen findings per file and per signal, with a count and a
recording date for each entry. A single scalar total MUST NOT be used: a total is meaningless once an ADR is
added or deleted, because it cannot say which file owes what.

#### Scenario: The ledger is read for one file

- **WHEN** the baseline is loaded and a file entry is inspected
- **THEN** it MUST be a mapping from signal name to `{count, detail, recorded_at}`
- **AND** the whole document MUST be a mapping from file name to such a mapping

### Requirement: An empty or missing baseline MUST be a hard error

The incremental mode MUST exit 2 when findings exist and the ledger is missing, unparsable or empty. An empty
ledger would make every finding look pre-existing and turn the gate green — the curtain failure this change
exists to remove.

#### Scenario: The ledger is emptied while findings exist

- **WHEN** the baseline file is replaced with `{}` and the incremental check runs over a corpus with findings
- **THEN** the check MUST exit 2
- **AND** it MUST report that the baseline cannot distinguish old debt from new

### Requirement: The baseline MUST only shrink

`--write-baseline` MUST refuse to write when the current findings exceed the ledger for any file and signal, and
MUST leave the file byte-identical in that case. Growth is fixed by fixing the ADR, not by recording the debt.

#### Scenario: A new finding appears and the writer runs

- **WHEN** an ADR gains a finding the ledger does not cover and `--write-baseline` runs
- **THEN** the writer MUST exit 1 and name the offending file and signal
- **AND** the ledger file MUST be unchanged

### Requirement: The incremental mode MUST report only debt outside the baseline

The diff MUST compare per file and signal by count rather than by detail text, so that an ADR growing from 300
to 340 lines still owes exactly one over-budget finding instead of reporting a new one on every edit.

#### Scenario: A pre-existing finding changes its wording

- **WHEN** an over-budget ADR grows further and the incremental check runs
- **THEN** the diff MUST report no new finding for that file
- **AND** a newly added process-log heading in the same file MUST be reported as exactly one new finding

### Requirement: A newly added ADR MUST be shape-clean

Because a new file is never in the ledger, every finding it produces is new debt. Adding an ADR that lacks the
required sections or the Verification chapter MUST fail the incremental check; adding a well-formed ADR MUST NOT.

#### Scenario: A second ADR is added without a Verification chapter

- **WHEN** a new ADR carrying only a Context section is added and the incremental check runs
- **THEN** the check MUST exit 1 and report the missing sections for that file
- **AND** a sibling well-formed ADR added at the same time MUST NOT be reported

### Requirement: The shape criteria MUST NOT be relaxed

The baseline mechanism MUST NOT change the signal set, the line budget, the Status-line budget or any severity.
Those are ADR-0060 decisions; relaxing them to reach green would need a new ADR. The mechanism MUST be additive.

#### Scenario: The implementation diff is inspected

- **WHEN** the diff of the gate module is searched for the signal names, the budget defaults or the severity assignments
- **THEN** no such line MUST appear as added or removed
- **AND** the diff MUST consist of additions only

### Requirement: ADR Status MUST be machine-readable without rewriting it

`extract_metadata` MUST expose `status_class` from a closed six-value set (draft, proposed, accepted, amended,
superseded, rejected) and MUST expose `status_raw` as the untouched Status text. Classification happens on read;
no ADR Status line is rewritten to fit the enum.

#### Scenario: An amended and superseded Status line is classified

- **WHEN** a Status value says it was accepted, amended and later superseded
- **THEN** the class MUST be superseded, because the widest-scope verdict wins
- **AND** the raw value MUST equal the text in the file character for character

### Requirement: The Status line MUST NOT carry a version history

A Status line MUST NOT accumulate commit hashes. Release and pull-request references are enough to locate an
implementation; hashes belong to git history, and a Status line that carries them crowds out the state itself.

#### Scenario: An ADR Status line still names commits

- **WHEN** the Status line of an ADR is matched against a commit-hash pattern
- **THEN** it MUST contain no match
- **AND** the accepted / superseded semantics MUST still be present

### Requirement: CI MUST run the shape gate in incremental mode and the local gate MUST mirror it

The CI workflow MUST run the incremental check as its own step with no conditional skip, and the local gate MUST
run the same command. A CI gate the local runner does not mirror is the drift that let CI stay red for months.

#### Scenario: The local runner is inspected

- **WHEN** the gates of the local test runner are listed
- **THEN** the incremental shape command MUST be among them
- **AND** the CI-mirror contract test MUST find the same command in the workflow

### Requirement: The baseline behaviours MUST stay covered by tests

Unit tests MUST cover the empty-ledger refusal, the report-only-new behaviour and the refusal to grow the ledger.
Each of the three is a guard on blank-able data, so a test that merely exercises the happy path is not enough.

#### Scenario: One of the three guards regresses

- **WHEN** the empty-ledger refusal, the diff or the growth refusal is removed
- **THEN** at least one unit test MUST fail
- **AND** it MUST name the guard that broke

### Requirement: Each shape signal MUST carry a two-sided fixture

For every signal the gate reports there MUST be a fixture that trips it exactly and a fixture that looks similar
but must stay silent. One-sided fixtures pass both when the check under-reports and when it over-reports.

#### Scenario: A process-log mention sits in prose rather than in a heading

- **WHEN** a sentence mentions a revision log inside the body text
- **THEN** the heading-level signal MUST NOT fire
- **AND** an actual revision-log heading in the same file MUST fire it
