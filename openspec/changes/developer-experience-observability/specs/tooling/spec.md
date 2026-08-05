# developer-experience-observability

## ADDED Requirements

### Requirement: Hook comment whitelist

The rdd-workflow hook system MUST skip comments matching bash idioms or magic-number annotations to reduce false positives.

#### Scenario: BASH_SOURCE guard comment

When a shell script comment contains `BASH_SOURCE[0]`, the hook MUST NOT flag it.
Given a change with hooks triggering on comments matching `developer-experience-observability` patterns
When the change is committed via `git commit`
Then no false-positive hook warning is emitted.

#### Scenario: Magic-number annotation

When a comment annotates a numeric threshold with explanation (e.g. "100ms threshold tuned for hardware X")
And the comment is in the same file as the threshold
Then the hook MUST NOT emit a lint warning on the threshold.
