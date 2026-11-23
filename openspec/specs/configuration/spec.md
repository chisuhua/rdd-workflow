# configuration Specification

## Purpose
TBD - created by archiving change v2-core-foundation. Update Purpose after archive.
## Requirements
### Requirement: configuration-multi-source-merge
The system SHALL support configuration from multiple sources with a strict priority order.

Priority order (highest to lowest): runtime parameters > `loop.yaml` > `.rddf.json` > environment variables > built-in defaults.

#### Scenario: Runtime parameter overrides file
- **WHEN** user passes `--mode loop` at runtime
- **AND** `loop.yaml` specifies `mode: menu`
- **THEN** runtime value (`loop`) is used

#### Scenario: Environment variable overrides file
- **WHEN** env var `RDDF_MODE=loop` is set
- **AND** `.rddf.json` specifies `mode: menu`
- **THEN** env var value (`loop`) is used

### Requirement: configuration-defaults
The system SHALL provide built-in defaults for all configuration fields.

Default values:
- `interaction.mode`: `"hybrid"`
- `loop.max_iterations`: `100`
- `loop.max_retries`: `3`

#### Scenario: Minimal config accepted
- **WHEN** user provides only `{"version": "2.0", "interaction": {"mode": "hybrid"}}`
- **THEN** all other fields use built-in defaults

### Requirement: configuration-validation
The system SHALL validate configuration values and reject invalid ones with clear error messages.

#### Scenario: Invalid mode rejected
- **WHEN** user provides `mode: invalid_mode`
- **THEN** system rejects with error: "Invalid mode 'invalid_mode'. Must be one of: loop, menu, hybrid"

#### Scenario: Out-of-range value rejected
- **WHEN** user provides `max_iterations: -1`
- **THEN** system rejects with error: "max_iterations must be > 0"

