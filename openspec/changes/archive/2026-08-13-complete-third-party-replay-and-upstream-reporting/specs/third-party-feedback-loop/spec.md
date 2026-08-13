# Spec: third-party-feedback-loop

> Capability: third-party projects can replay rdd-workflow phase execution and submit classified workflow defects to the upstream repository.

## ADDED Requirements

### Requirement: Business project root is separate from tool root

The runtime SHALL distinguish the installed rdd-workflow tool root from the current third-party business project root. `RDDF_PROJECT_ROOT` SHALL resolve to the invoking project's Git root when no explicit project root is provided. Shared helpers MUST NOT derive the business project root from their own `BASH_SOURCE` path.

#### Scenario: Global install from third-party repository

- **GIVEN** rdd-workflow is installed globally and the current directory is a third-party Git repository
- **WHEN** a phase entry script invokes an orchestrator helper
- **THEN** tool modules are loaded from the global installation
- **AND** `RDDF_PROJECT_ROOT` points to the third-party repository
- **AND** trace, session, and issue files are written below the third-party `.rddf/` directory
- **AND** no workflow state is written to the rdd-workflow tool repository

#### Scenario: Explicit project root wins

- **GIVEN** `RDDF_PROJECT_ROOT` is explicitly set to a valid project root
- **WHEN** the CLI or shell helper resolves runtime roots
- **THEN** the explicit value is used
- **AND** the tool root remains available independently for module loading

### Requirement: Phase traces are replayable from any project subdirectory

The orchestrator SHALL store and read traces from `${RDDF_PROJECT_ROOT}/.rddf/state/trace` by default. `RDDF_TRACE_DIR` SHALL remain an explicit override. `rddf orchestrate show <phase>` SHALL produce the same timeline when invoked from the project root or a descendant directory.

#### Scenario: Replay from project root

- **GIVEN** a finalized trace exists at `.rddf/state/trace/guide-plan-*.jsonl`
- **WHEN** the user runs `rddf orchestrate show guide-plan` from the project root
- **THEN** the command prints the trace timeline and exits successfully

#### Scenario: Replay from descendant directory

- **GIVEN** the same trace exists in the project root
- **WHEN** the user runs `rddf orchestrate show guide-plan` from a descendant directory
- **THEN** the command reads the project-root trace rather than a descendant-local `.rddf` directory
- **AND** the output is equivalent to the root invocation

### Requirement: Normal finalize writes reportable failures locally

When a phase trace contains a reportable workflow failure, normal finalize SHALL call `report_flow_bug` with the business project root before appending the finalize event. `report_written` SHALL be true only when a local issue file was successfully returned/written. Reporter failures SHALL be non-blocking and SHALL leave the trace available for diagnosis.

#### Scenario: Reportable subprocess failure

- **GIVEN** a phase has a failing subprocess classified as `flow-bug`, `gate-failure`, or `phase-crash`
- **WHEN** the phase reaches normal finalize
- **THEN** `.rddf/issues/<category>-<hash>.md` is created in the business project
- **AND** the finalize event records `report_written: true`
- **AND** the original phase result is preserved

#### Scenario: Non-reportable failure

- **GIVEN** a failure is classified as usage-error, environment-error, SIGINT, or SIGTERM
- **WHEN** normal finalize runs
- **THEN** no flow-bug issue is created
- **AND** `report_written` is false
- **AND** finalize still completes

#### Scenario: Reporter unavailable

- **GIVEN** issue writing or optional GitHub submission raises an expected runtime error
- **WHEN** finalize runs
- **THEN** the error is emitted as a warning
- **AND** the trace is finalized
- **AND** the phase is not converted into a new failure solely because reporting failed

### Requirement: Reporter CLI works in all installation modes

The `rddf issue list/show/submit` and `rddf report-issue` commands SHALL resolve reporter imports consistently from the source checkout, global installation, project-local installation, and a third-party project working directory.

#### Scenario: Manual local issue creation

- **GIVEN** a third-party project with `.rddf/state/`
- **WHEN** the user runs `rddf report-issue --no-submit` or `rddf issue list`
- **THEN** the command exits successfully
- **AND** any issue file is created/read under the third-party `.rddf/issues/` directory

#### Scenario: Upstream submission target

- **GIVEN** a local issue file and `gh` is available
- **WHEN** the user submits without an explicit repository override
- **THEN** the reporter uses `--repo chisuhua/rdd-workflow`
- **AND** it performs deduplication before creating a new issue
- **AND** it does not infer the third-party repository remote as the upstream target

#### Scenario: Submission unavailable

- **GIVEN** `gh` is missing, unauthorized, or unable to reach GitHub
- **WHEN** issue submission is attempted
- **THEN** the local issue remains intact
- **AND** the command returns a diagnosable manual-submission result
- **AND** the workflow/archive is not blocked

### Requirement: Reporting configuration has one effective contract

Reporting runtime behavior SHALL match its documented configuration. The implementation SHALL define the relationship among local buffering, automatic submission, category allowlists, `RDDF_REPORT_GH_REPO`, and archive close behavior. Unsupported schema fields SHALL be removed or wired; they MUST NOT silently do nothing.

#### Scenario: Automatic submission remains opt-in

- **GIVEN** automatic submission flags are unset or disabled
- **WHEN** a reportable failure is finalized
- **THEN** the local issue is written
- **AND** no GitHub submission is attempted

#### Scenario: Explicit upstream override

- **GIVEN** `RDDF_REPORT_GH_REPO` is set
- **WHEN** an eligible submission occurs
- **THEN** the configured repository is used consistently by automatic, manual, and archive-close paths

### Requirement: Archive close is safe in third-party projects

Archive close integration SHALL use safe argv/environment passing, preserve the non-blocking contract, and degrade to manual links when the third-party project lacks upstream write permission or required tools.

#### Scenario: No upstream permission

- **GIVEN** archive runs in a third-party project without push permission to the upstream repository
- **WHEN** the close hook executes
- **THEN** archive completes successfully
- **AND** the hook emits manual close links or a warning
- **AND** no issue state is written to the tool repository

#### Scenario: Malformed or hostile change name

- **GIVEN** a change name contains shell-sensitive characters rejected or accepted by the workflow
- **WHEN** archive invokes the close hook
- **THEN** the name is passed as an argument/value, not interpolated into Python source
- **AND** no unintended shell/Python code executes

### Requirement: Global-install integration is regression tested and documented

The repository SHALL provide isolated third-party integration tests and documentation for global installation, replay, issue buffering, upstream routing, and failure degradation.

#### Scenario: End-to-end external project

- **GIVEN** an isolated third-party Git project and global rdd-workflow installation
- **WHEN** the test runs a wrapped failing phase, finalizes it, replays it from a subdirectory, and submits the buffered issue with a mocked `gh`
- **THEN** all artifacts remain in the third-party project
- **AND** the upstream repository target is verified
- **AND** tool-root state remains unchanged

#### Scenario: Installation documentation

- **GIVEN** a user follows global-install documentation
- **WHEN** they need to replay a phase or submit an issue
- **THEN** the documentation identifies the command, trace location, `.rddf/issues/` location, upstream target, opt-in policy, and local fallback behavior
