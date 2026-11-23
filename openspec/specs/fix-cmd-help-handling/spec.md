# fix-cmd-help-handling Specification

## Purpose
TBD - created by archiving change fix-cmd-help-handling. Update Purpose after archive.
## Requirements
### Requirement: uniform-help-handling

The `rddf` CLI dispatcher SHALL handle `--help` and `-h` uniformly for all subcommands by intercepting these flags at the dispatch layer (`_lib/cli/__init__.py::route()`) before invoking the per-subcommand handler. This ensures that argparse-style `EXIT 0` behavior is guaranteed for every subcommand, regardless of how individual handlers configure their parsers.

#### Scenario: contract-check --help returns EXIT 0

- **WHEN** the user invokes `rddf contract-check --help`
- **THEN** the CLI dispatcher SHALL intercept the `--help` flag at `route()` before invoking the `contract_check_cmd` handler
- **AND** an `ArgumentParser` with `prog="rddf contract-check"` and the contract-check description SHALL print usage information to stdout
- **AND** the dispatcher SHALL return `0` as the exit code

#### Scenario: archive-sync --help returns EXIT 0

- **WHEN** the user invokes `rddf archive-sync --help`
- **THEN** the CLI dispatcher SHALL intercept the `--help` flag at `route()` before invoking the `archive_sync_cmd` handler
- **AND** an `ArgumentParser` with `prog="rddf archive-sync"` and the archive-sync description SHALL print usage information to stdout
- **AND** the dispatcher SHALL return `0` as the exit code

#### Scenario: -h short form returns EXIT 0

- **WHEN** the user invokes any `rddf <sub> -h`
- **THEN** the dispatcher SHALL treat `-h` identically to `--help` (intercept at `route()`, print usage, return `0`)

#### Scenario: backward-compatible for 34 working subcommands

- **WHEN** the dispatcher intercepts `--help`/`-h` for any subcommand that already handles help correctly
- **THEN** the dispatcher SHALL print usage via the `_SUBCOMMAND_DESCRIPTION` registry (defaulting to empty description if not registered) and return `0`
- **AND** the underlying handler SHALL NOT be invoked

### Requirement: subcommand-description-registry

The CLI dispatcher SHALL maintain a `_SUBCOMMAND_DESCRIPTION` dict mapping subcommand names to human-readable descriptions. Descriptions are used in `--help` output to provide context beyond the bare command name. The registry SHALL be expandable without modifying the dispatcher logic.

#### Scenario: registry lookup with fallback

- **WHEN** the dispatcher prints help for subcommand `foo`
- **AND** `_SUBCOMMAND_DESCRIPTION["foo"]` is not registered
- **THEN** the dispatcher SHALL print usage info without a description (description defaults to empty string)
- **AND** the dispatcher SHALL still return `0`

