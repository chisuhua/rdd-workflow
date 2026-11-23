# contract-diff-py Specification

## Purpose
Pure-Python module that compares Hub OpenAPI contracts against Spoke local implementations. Detects Breaking-Change severity when Spoke missing required Hub fields.

## Public API
- `DiffEngine.run()` — returns DiffResult with severity classification
- `Severity` enum — Breaking-Change / High / Medium / Low / No-Diff
- `format_output(result, format)` — JSON or Markdown output

## Behavior
With openapi-diff library: parses Hub contract, scans Spoke impl for required fields, returns Breaking-Change if missing. Fallback to YAML+grep when openapi-diff not installed.

## Requirements
### Requirement: contract-diff-returns-a-graded-diff-result

`DiffEngine.run()` SHALL compare the Hub OpenAPI contract against the Spoke local
implementation and return a `DiffResult` whose severity classifies the difference;
`format_output(result, format)` SHALL render that result as JSON or as Markdown.

#### Scenario: a missing required Hub field is a breaking change

- **WHEN** the Spoke implementation lacks a field the Hub contract requires
- **THEN** the result's severity SHALL be a breaking change

#### Scenario: a compliant implementation yields no difference

- **WHEN** the Spoke implementation satisfies the Hub contract
- **THEN** the result's severity SHALL be no difference

#### Scenario: the result renders in the requested format

- **WHEN** the result is formatted
- **THEN** it SHALL render as JSON or as Markdown, per the requested format

## Test Coverage
- 5 pytest unit tests (breaking detection / compliant / JSON / Markdown / severity)
