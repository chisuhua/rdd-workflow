## ADDED Requirements

### Requirement: tribunal-cross-validation
The system SHALL provide a `Tribunal` class for multi-agent cross-validation of workflow decisions.

The Tribunal invokes two distinct agents: an Executor (verifies task completion) and a Reviewer (verifies quality and correctness). Both must be different agents.

#### Scenario: Both agents invoked
- **WHEN** Tribunal is invoked for a change
- **THEN** Executor agent returns `exec_score` (0.0-1.0)
- **AND** Reviewer agent returns `review_score` (0.0-1.0)
- **AND** both scores are recorded to event log

#### Scenario: Same agent warning
- **WHEN** Executor and Reviewer are configured to be the same agent
- **THEN** Tribunal emits warning
- **AND** asks user to confirm before proceeding

### Requirement: tribunal-weighted-judgment
The system SHALL compute a final judgment using weighted scoring.

Formula: `final_score = exec_score * 0.4 + review_score * 0.6`. Pass condition: `final_score >= 0.8 AND both pass AND conflict < 0.4`.

#### Scenario: High confidence passes
- **WHEN** exec_score=0.9, review_score=0.95
- **THEN** final_score = 0.93
- **AND** Tribunal returns pass

#### Scenario: High conflict warns
- **WHEN** exec_score=0.9, review_score=0.4
- **THEN** conflict = 0.5
- **THEN** Tribunal returns fail with warning about high disagreement

#### Scenario: Borderline final score
- **WHEN** exec_score=0.7, review_score=0.85
- **THEN** final_score = 0.79
- **THEN** Tribunal returns fail (below 0.8 threshold)

### Requirement: tribunal-graceful-degradation
The system SHALL handle Tribunal agent invocation failures gracefully.

#### Scenario: oh-my-opencode CLI unavailable
- **WHEN** Tribunal cannot invoke Executor or Reviewer
- **THEN** system falls back to single-agent verification
- **AND** warning event is recorded

### Requirement: sanitizer-data-redaction
The system SHALL sanitize sensitive data before cross-agent invocation.

Detected patterns: API keys (regex), passwords (env var patterns), sensitive paths (`/etc/`, `~/.ssh/`). Replaced with `<REDACTED>` placeholder. Whitelist supported for allowed paths.

#### Scenario: API key detected
- **WHEN** payload contains `api_key=sk-1234...`
- **THEN** sanitizer replaces with `api_key=<REDACTED>`

#### Scenario: Whitelisted path allowed
- **WHEN** payload contains `/home/user/project/file.py` and whitelist includes it
- **THEN** sanitizer does not redact
