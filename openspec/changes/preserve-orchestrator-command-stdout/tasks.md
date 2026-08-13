# Tasks: preserve-orchestrator-command-stdout

> TDD 5-step structure per `rdd-workflow-writing-plans` skill.
> Each task: Write failing test → Verify fail → Implement → Verify pass → Commit.

## 1. Capture mode plumbing

- [ ] 1.1 Write failing test: `RDDF_ORCHESTRATOR_CAPTURE=tee` results in `trace.stdout_capture_mode == "tee"` after orchestrator run
- [ ] 1.2 Write failing test: `RDDF_ORCHESTRATOR_CAPTURE=passthrough` results in no trace file written
- [ ] 1.3 Write failing test: `RDDF_ORCHESTRATOR_CAPTURE=capture` (legacy) preserves old PIPE capture behavior
- [ ] 1.4 Implement env-var parsing in `skills/_lib/orchestrator_entry.sh`
- [ ] 1.5 Verify all 3 mode tests pass
- [ ] 1.6 Commit: `feat(orchestrator): add stdout_capture_mode (tee|capture|passthrough)`

## 2. Default mode switch + async tee

- [ ] 2.1 Write failing test: Default (no env var) uses `tee` mode
- [ ] 2.2 Write failing test: `tee` mode does NOT block subprocess when stdout is 1MB
- [ ] 2.3 Write failing test: `tee` mode does NOT block subprocess when stdout is 100MB
- [ ] 2.4 Implement reader subprocess + inherit stdout/stderr in main Popen
- [ ] 2.5 Verify mode + non-blocking tests pass
- [ ] 2.6 Commit: `feat(orchestrator): default tee mode with async reader subprocess`

## 3. Failure handling + buffer protection

- [ ] 3.1 Write failing test: When reader subprocess dies (SIGKILL simulation), main flow continues
- [ ] 3.2 Write failing test: Trace file marked with `reader_died: true` after reader crash
- [ ] 3.3 Write failing test: 100MB output triggers file rotation to `<trace>.1`
- [ ] 3.4 Implement reader_died detection + file rotation logic
- [ ] 3.5 Verify failure-handling tests pass
- [ ] 3.6 Commit: `feat(orchestrator): failure handling + trace rotation`

## 4. CI compatibility + trace schema

- [ ] 4.1 Write failing integration test: `CI=true rddf orchestrate subprocess bash -c 'echo "to CI log"'` → runner sees output
- [ ] 4.2 Write failing test: `trace.json` contains `stdout_capture_mode` field after run
- [ ] 4.3 Update `.rddf/state/trace/*.json` schema (add field)
- [ ] 4.4 Verify CI + schema tests pass
- [ ] 4.5 Commit: `feat(orchestrator): trace schema + CI compatibility`

## 5. Documentation + manual benchmark

- [ ] 5.1 Update `docs/architecture/extension-points.md` with "orchestrator 输出策略" section
- [ ] 5.2 Update `CHANGELOG.md` Unreleased with this change
- [ ] 5.3 Manual benchmark: 10MB output, measure overhead vs capture baseline (target: ≤5%)
- [ ] 5.4 Verify `./test.sh --full --regression` all green (no new failures)
- [ ] 5.5 Commit: `docs(orchestrator): output strategy guide + benchmark note`

## Acceptance criteria

- All TDD tasks above marked complete
- `./test.sh --full --regression` passes
- Documentation updated
- Manual benchmark recorded in change comments
- ADR-0027 §1.0.1 behavior preserved when `RDDF_ORCHESTRATOR_CAPTURE=capture`