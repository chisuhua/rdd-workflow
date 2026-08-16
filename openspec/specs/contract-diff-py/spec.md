# contract-diff-py Specification

## Purpose
Pure-Python module that compares Hub OpenAPI contracts against Spoke local implementations. Detects Breaking-Change severity when Spoke missing required Hub fields.

## Public API
- `DiffEngine.run()` — returns DiffResult with severity classification
- `Severity` enum — Breaking-Change / High / Medium / Low / No-Diff
- `format_output(result, format)` — JSON or Markdown output

## Behavior
With openapi-diff library: parses Hub contract, scans Spoke impl for required fields, returns Breaking-Change if missing. Fallback to YAML+grep when openapi-diff not installed.

## Test Coverage
- 5 pytest unit tests (breaking detection / compliant / JSON / Markdown / severity)
