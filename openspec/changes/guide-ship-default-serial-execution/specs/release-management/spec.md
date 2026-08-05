# guide-ship-execution-mode

## ADDED Requirements

### Requirement: Default execution mode

Wave execution defaults to serial (1 concurrent); parallel is opt-in via `--parallel` flag or `RDD_SHIP_PARALLEL=yes` env var.

#### Scenario: No parallel flag

When `skill_use("guide-ship")` is called without `--parallel`, change waves execute serially with concurrency=1.
Given a change with hooks triggering on comments matching `guide-ship-default-serial-execution` patterns
When the change is committed via `git commit`
Then no false-positive hook warning is emitted.

#### Scenario: Magic-number annotation

When a comment annotates a numeric threshold with explanation (e.g. "100ms threshold tuned for hardware X")
And the comment is in the same file as the threshold
Then the hook MUST NOT emit a lint warning on the threshold.
