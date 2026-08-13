# Design: preserve-orchestrator-command-stdout

## Context

ADR-0027 introduced the orchestrator wrapper for trace capture. The 2026-08-13 default-ON rollout activated it for all phase entries. The current capture mode (`subprocess.run(capture_output=True)` or PIPE-based wrapper) holds child process output hostage for trace recording, causing user-visible regressions:

1. **stdout 吞掉**: Users running `rddf orchestrate subprocess <cmd>` see no real-time output of `<cmd>`
2. **PIPE buffer 死锁**: Long-output subprocesses (≥10MB) block waiting for the orchestrator to drain, leading to OOM or timeout
3. **CI 日志丢失**: GitHub Actions runners don't see expected output if orchestrator swallows before flushing
4. **No escape hatch**: Users cannot disable capture to get zero-overhead execution

This proposal implements `tee` mode by default — the orchestrator runs the child with stdout/stderr inherited (not PIPE) and uses a dedicated reader thread/process to async-copy to the trace file. A `passthrough` mode skips trace writing entirely for users who don't need it.

## Decisions

### Capture mode taxonomy

Three modes for `RDDF_ORCHESTRATOR_CAPTURE`:

| Mode | stdout/stderr to caller | trace file | Use case |
|------|------------------------|------------|----------|
| `tee` (default) | ✅ passthrough | ✅ async tee | Normal operations |
| `capture` | ❌ hidden | ✅ captured | Legacy dogfooding reports |
| `passthrough` | ✅ passthrough | ❌ no trace | Zero-overhead escape hatch |

### Async reader implementation

Use `subprocess.Popen` with `stdout=None, stderr=None` (inherit from parent) for the main child. Then start a **dedicated reader subprocess** that re-runs the command with `stdout=PIPE` purely to drain into the trace file. This decouples caller-facing output from trace capture.

Alternative considered: Python `threading.Thread` reading from PIPE in-process. Rejected due to:
- GIL contention with the main process
- PIPE buffer overflow still possible (need O_NONBLOCK anyway)
- Thread crashes harder to recover from than subprocess

### Pipe buffer protection

Use `O_NONBLOCK` on the reader subprocess's PIPE writes when possible (Linux/macOS). Windows TODO: use `pipesize` workaround or buffering shim. Documented in `docs/architecture/extension-points.md`.

### Trace schema extension

Add `stdout_capture_mode` field to `.rddf/state/trace/<phase>.json`:

```json
{
  "phase": "guide-plan",
  "started_at": "...",
  "finished_at": "...",
  "stdout_capture_mode": "tee",
  "reader_died": false,
  "subprocess_results": [...]
}
```

### Failure semantics

Reader subprocess crash → main flow continues → trace marks `reader_died: true` → user sees normal output but trace partial. No retry (would obscure original failure). Logged as warning to stderr.

### File rotation

When trace file exceeds `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES` (default 100MB):
- Rename current to `<trace>.1`
- New trace file starts
- Rotation logged as trace event

Rationale: 100MB is enough for normal operations but small enough to avoid filling `/tmp` or `.rddf/state/`.

### Out-of-scope decisions

- **Cross-platform tee (Windows)**: Documented as TODO; POSIX priority.
- **Real-time output coloring/paging**: User-side concern, not orchestrator's job.
- **`rddf orchestrate show` output format**: Separate change.
- **Orchestrator's own stdout**: Not affected; orchestrator's stdout goes to terminal as normal.

## Risks

| Risk | Mitigation |
|------|-----------|
| Reader subprocess still OOMs on 100MB+ output | File rotation at 100MB default; user can lower `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES` |
| Async tee introduces latency in trace recording | Acceptable — trace is best-effort, not real-time |
| User sets `capture` mode but expects old behavior | Document in CHANGELOG + docs/architecture/extension-points.md |
| Windows compatibility gaps | Explicit TODO + document limitation; users on Windows can use WSL or skip mode |

## Migration

1. Implementation: add `tee | passthrough` modes to `skills/_lib/orchestrator_entry.sh::orchestrator_run`
2. Default: switch from `capture` to `tee` (the old behavior is one env var away)
3. Tests: ≥10 unit + ≥5 integration cases covering all 3 modes + edge cases
4. Docs: update `docs/architecture/extension-points.md` + `CHANGELOG.md`
5. Backward compat: `RDDF_ORCHESTRATOR_CAPTURE=capture` preserves legacy PIPE capture