# plan-quality-checklist

## ADDED Requirements

### Requirement: Plan quality checklist

Plans MUST pass a pre-publish checklist including BASH_SOURCE guards, fixture paths, and expected counts derived from real test runs.

#### Scenario: Script step without guard

When a step 5 contains shell script that defines functions but lacks `BASH_SOURCE[0]` guard, the plan generator MUST auto-append one.
Given a change with hooks triggering on comments matching `plan-quality-and-validation` patterns
When the change is committed via `git commit`
Then no false-positive hook warning is emitted.

#### Scenario: Magic-number annotation

When a comment annotates a numeric threshold with explanation (e.g. "100ms threshold tuned for hardware X")
And the comment is in the same file as the threshold
Then the hook MUST NOT emit a lint warning on the threshold.
