# subagent-quota-degradation

## ADDED Requirements

### Requirement: Quota-aware execution strategy

The orchestrator MUST probe subagent quota before parallel dispatch and degrade to direct execution when quota is exhausted.

#### Scenario: Quota exhausted mid-wave

When `task()` returns `quota_exceeded`, the orchestrator MUST retry once then fall back to direct execution within the current session.
Given a change with hooks triggering on comments matching `subagent-orchestrator-execution-strategy` patterns
When the change is committed via `git commit`
Then no false-positive hook warning is emitted.

#### Scenario: Magic-number annotation

When a comment annotates a numeric threshold with explanation (e.g. "100ms threshold tuned for hardware X")
And the comment is in the same file as the threshold
Then the hook MUST NOT emit a lint warning on the threshold.
