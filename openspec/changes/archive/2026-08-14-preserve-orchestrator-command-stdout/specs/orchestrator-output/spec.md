# Spec: orchestrator-output

> Capability covering orchestrator subprocess output handling: stdout/stderr passthrough + async tee trace capture + CI compatibility + env-var opt-out.

## ADDED Requirements

### Requirement: orchestrator-subprocess-stdout-passthrough

The `rddf orchestrate subprocess` wrapper MUST pass the child process's stdout and stderr through to the caller's terminal by default, without buffering or capturing them.

#### Scenario: live stdout visible to caller

- WHEN a user runs `rddf orchestrate subprocess python3 -m foo --verbose` and `foo` produces stdout incrementally
- THEN the user's terminal displays each line as it is produced
- AND `foo` is not blocked by the orchestrator's pipe buffer

#### Scenario: stderr passthrough

- WHEN a child process writes to stderr
- THEN the caller's terminal sees the stderr output interleaved with stdout (no separate capture)

### Requirement: orchestrator-async-tee-to-trace

The orchestrator MUST asynchronously copy stdout and stderr to the trace file (`.rddf/state/trace/<phase>.json`) using a dedicated reader thread or process, without blocking the main flow.

#### Scenario: trace captures complete stdout

- WHEN a child process produces 100 stdout lines
- THEN the trace file contains all 100 lines in order
- AND the child process does not block on the reader

#### Scenario: reader failure does not crash main flow

- WHEN the trace reader thread dies (e.g., OOM or segfault)
- THEN the main phase continues to run
- AND the trace file marks `stdout_capture_mode: tee` with `reader_died: true`

#### Scenario: trace file rotation on size limit

- WHEN the trace file exceeds 100MB (or `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES`)
- THEN the current trace file is rotated to `<trace>.1`
- AND a new trace file starts capturing
- AND user stdout is not interrupted

### Requirement: orchestrator-pipe-buffer-protection

The orchestrator MUST protect against pipe buffer exhaustion when the child produces output faster than the reader drains.

#### Scenario: long output does not deadlock

- WHEN a child process produces 100MB of stdout
- THEN the child does not block due to full PIPE buffer
- AND the orchestrator uses `O_NONBLOCK` or dynamic buffer expansion to prevent deadlock

### Requirement: orchestrator-stdout-capture-mode-env

The orchestrator MUST honor the `RDDF_ORCHESTRATOR_CAPTURE` env var with three modes: `tee`, `capture`, `passthrough`.

#### Scenario: passthrough mode disables trace

- WHEN `RDDF_ORCHESTRATOR_CAPTURE=passthrough` is set
- THEN the orchestrator does not write to the trace file (zero overhead)
- AND stdout/stderr still passes through to caller

#### Scenario: capture mode preserves legacy behavior

- WHEN `RDDF_ORCHESTRATOR_CAPTURE=capture` is set
- THEN the orchestrator uses the original PIPE capture (ADR-0027 §1.0.1 behavior)
- AND the trace file contains the captured stdout/stderr
- AND caller does not see live output (matches old dogfooding reports)

### Requirement: orchestrator-stdout-mode-traceable

Every orchestrator run MUST record the capture mode used in the trace JSON.

#### Scenario: capture mode in trace

- WHEN an orchestrator run completes (any mode)
- THEN `cat .rddf/state/trace/<phase>.json | jq .stdout_capture_mode` returns one of `tee`, `capture`, or `passthrough`

### Requirement: orchestrator-ci-compatibility

The orchestrator MUST work correctly in CI environments without breaking runner log output.

#### Scenario: CI runner sees output

- WHEN `CI=true rddf orchestrate subprocess bash ci.sh` is run in GitHub Actions
- THEN the runner log contains the output of `ci.sh`
- AND the local trace file is optional (depending on mount of `/tmp` or similar)