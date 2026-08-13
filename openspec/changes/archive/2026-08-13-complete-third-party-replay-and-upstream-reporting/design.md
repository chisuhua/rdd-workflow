# Design: complete-third-party-replay-and-upstream-reporting

## Context

The default-ON orchestrator rollout records phase traces, but the global-install path has two distinct roots: the rdd-workflow package root and the third-party project root. Existing shell helpers derive `RDDF_PROJECT_ROOT` from their own location, while the CLI derives the project root from the invoking Git repository. The implementation must make these paths explicit and preserve fail-open behavior.

The issue path has three stages:

```text
third-party phase
  -> orchestrator trace under third-party/.rddf/state/trace
  -> finalize classification
  -> local third-party/.rddf/issues/*.md
  -> optional gh submit to chisuhua/rdd-workflow
```

## Decisions

### Root model

Introduce a single runtime root-resolution contract:

- `RDDF_TOOL_ROOT`: location of the installed rdd-workflow package/modules.
- `RDDF_PROJECT_ROOT`: current business project root, resolved from explicit env first, then Git root, then cwd.
- `RDDF_TRACE_DIR`: explicit override; otherwise `${RDDF_PROJECT_ROOT}/.rddf/state/trace`.

The shell wrapper must never derive `RDDF_PROJECT_ROOT` from `BASH_SOURCE`. `BASH_SOURCE` is valid only for locating tool code.

Global install shall expose shared shell helpers through the same resolver used by existing global-install bootstrap code. Project-local installs shall continue to work without a global install.

### Finalize/report contract

`analyze_phase_trace` remains a classifier. `orchestrate finalize` owns reporting:

1. Analyze the trace.
2. If the classification is reportable, call `report_flow_bug` with the business project root.
3. Set `report_written` from the returned issue path, not from classification existence.
4. Append finalize regardless of reporter success.

Reporter failures are warnings and do not change the subprocess exit code.

### CLI import and submission contract

CLI modules must import reporter modules through a package-safe path that works from:

- source checkout;
- global `~/.local/bin/rddf` install;
- project-local installation;
- third-party project cwd.

Local issue creation remains unconditional for reportable classifications. GitHub submission remains explicit opt-in for automatic reporting, uses `RDDF_REPORT_GH_REPO` when supplied, and defaults to `chisuhua/rdd-workflow`. Manual CLI behavior must not silently bypass the same safety policy.

### Configuration and archive close

Use one documented runtime configuration surface for reporting. Either wire `Config.reporting` through all reporter calls or remove unused fields; no schema field may silently have no effect.

Archive close is best-effort. It receives paths and change names through argv/env, never interpolated Python source. Missing imports, missing `gh`, no permission, and network failure produce manual links/warnings without blocking archive.

## Testing strategy

Use isolated temporary Git repositories to prove root ownership. Tests must assert that no file is created under the rdd-workflow tool root. Cover both global and project-local installation paths where practical. Mock `gh` at the subprocess boundary and assert exact `--repo chisuhua/rdd-workflow` behavior without making network calls.

The capability spec below is the normative acceptance contract; `tasks.md` maps each requirement to TDD and integration work.
