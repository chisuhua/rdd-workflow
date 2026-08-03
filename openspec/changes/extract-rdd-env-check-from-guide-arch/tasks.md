## 1. Setup

- [ ] 1.1 Read `proposal.md`, `design.md`, `improvements/extract-rdd-env-check-from-guide-arch.md` and confirm In Scope / Out of Scope boundaries
- [ ] 1.2 Verify dependencies: bash, git and openspec available; confirm jq/python3 are not required by the runtime path
- [ ] 1.3 Check current branch + worktree strategy; preserve ADR-0016 discovery and avoid changes to rddf-session protocol, gate/handoff scripts and all Phase 2-6 behavior

## 2. Implementation (TDD 5 步)

- [ ] 2.1 Write failing tests: add 3 bats cases for cache hit, TTL expiry/cache deletion and branch-change invalidation; add assertions for the 10-field JSON contract, openspec-missing non-zero exit with repair guidance, no jq/python3 runtime dependency, atomic cache path and one-line Phase 1 status
- [ ] 2.2 Verify tests fail (red): confirm `skills/rdd-env-check/`, `.rddf/state/.env-cache.json` handling and `skills/_lib/env_checks.sh` do not yet satisfy the new assertions
- [ ] 2.3 Implement change: create `skills/rdd-env-check/SKILL.md` + `scripts/env_check.sh`; extract shared `_check_*` functions to `skills/_lib/env_checks.sh`; write the 10-field cache atomically with default 3600s / `RDD_ENV_CACHE_TTL` override and branch invalidation; refactor `arch_env_check.sh` plus design/plan/ship Phase 1 callers to use cache with full-check fallback; keep ADR-0016 discovery live and compress guide-arch first-screen output to one line
- [ ] 2.4 Verify tests pass (green): assert cache hit completes under 100ms excluding subprocess startup, expiry/deletion/branch change rerun the full check, new and compatibility JSON field sets match, missing openspec blocks entry, and the existing 49 related tests remain green
- [ ] 2.5 Refactor + commit: remove duplicated environment checks, verify `_lib/env_checks.sh` has at least 4 `_check_*` references across the two scripts, keep runtime limited to bash + git + openspec, review the diff for proposal-only scope, then commit the implementation

## 3. Verification

- [ ] 3.1 Run `openspec validate extract-rdd-env-check-from-guide-arch --json` — 接受 specs/ 缺失 ERROR (本次 fill 不写 specs/, plan 阶段决策)
- [ ] 3.2 Run `python3 -m pytest tests/unit/ -q --tb=short` and `python3 -m pytest tests/integration/ -q --tb=short` (passes)
- [ ] 3.3 Run the 3 new bats cache cases, the existing 49 related tests, then `npm test` for the full bats regression suite (passes)
- [ ] 3.4 Compare `rdd-env-check` and compatibility `arch_env_check.sh` JSON keys; confirm exactly `timestamp`, `ttl_s`, `branch`, `openspec_ver`, `git_clean`, `build_dir`, `adr_count`, `roadmap_exists`, `gap_count`, `active_changes`
- [ ] 3.5 Run cache-hit timing and Phase 1 output checks: total setup < 100ms excluding subprocess startup and first-screen status is one line containing Env state, ADR count and roadmap state
- [ ] 3.6 Run with openspec removed from temporary PATH and with jq/python3 unavailable; confirm non-zero blocking + repair guidance for openspec and no optional-tool runtime failure
- [ ] 3.7 Run a manual arch → design → plan → ship Phase 1 walkthrough; confirm cache fallback/invalidations work and Phase 2-6 behavior is unchanged
- [ ] 3.8 Run `git show HEAD:openspec/changes/extract-rdd-env-check-from-guide-arch/design.md` (artifact committed)
- [ ] 3.9 Run `git show HEAD:openspec/changes/extract-rdd-env-check-from-guide-arch/tasks.md` (artifact committed)
- [ ] 3.10 Run `git show HEAD:openspec/changes/extract-rdd-env-check-from-guide-arch/.openspec.yaml` (metadata committed)

## 4. Documentation

- [ ] 4.1 Add and review `skills/rdd-env-check/SKILL.md` usage, JSON/cache contract, TTL override and failure behavior
- [ ] 4.2 Update `skills/guide-arch/SKILL.md` Phase 1 documentation to remove the full environment-check transcript and describe the one-line cached status while retaining ADR-0016 discovery
- [ ] 4.3 Add entry to `CHANGELOG.md` (if present)
- [ ] 4.4 Create or update an ADR only if required to record the proposal-mandated responsibility split; do not modify ADR-0003 or the rddf-session protocol
