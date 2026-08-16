# contract-lint Specification

## Purpose
CI gate integration: `rddf contract-check` CLI for validating Spoke implementations against Hub contracts before merge.

## Behavior
Exit codes:
- 0 = compliant (No-Diff or Low/Medium severity)
- 1 = Breaking-Change detected (CI should block merge)

Flags: `--hub <path>`, `--local <path>`, `--dry-run`, `--format json|markdown`

## Test Coverage
- 3 bats integration tests (ok exit 0 / breaking exit 1 / --dry-run)
