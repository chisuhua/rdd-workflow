## Tasks

### Phase A — Code fix (P0, must land)

- [x] **Task 1: `_lib/archive.sh` L561 — delete `commit_archive_moves` call in false branch**
  - Modify: `_lib/archive.sh` L561
  - Diff: remove line `commit_archive_moves "$name" "$main_root" || true`
  - Rationale: per spec L254, false branch SHALL NOT execute `commit_archive_moves`
  - Test: AC-1, AC-2

- [x] **Task 2: `_lib/archive.sh::commit_archive_moves()` — add `git.openspec_tracked` guard**
  - Modify: `_lib/archive.sh` between L798 and L800 (after `SKIP_ARCHIVE_AUTO_COMMIT` check, before `git status` no-op exit)
  - Diff: add 10-line block reading `.rddf/project.yaml` via `project_config.sh::project_yaml_get`; if `git.openspec_tracked` is `false` or `False`, echo "ℹ️  commit_archive_moves: SKIPPED (git.openspec_tracked=false)" and `return 0`
  - Rationale: defense-in-depth single-point-of-truth guard (per L786 docstring historical multi-call-site risk)
  - Test: AC-4

### Phase B — Tests (P0)

- [x] **Task 3: Upgrade `tests/integration/test_archive_with_openspec_tracked_false.bats`**
  - Modify: `tests/integration/test_archive_with_openspec_tracked_false.bats`
  - Diff:
    - Keep case 1 (function-existence smoke) as regression guard
    - Replace case 2 (grep-source-text) with **behavioral test**:
      - Seed repo with tracked `openspec/changes/<name>/proposal.md` (mixed-state)
      - Set `.rddf/project.yaml` `git.openspec_tracked: false`
      - Stub `openspec` CLI on PATH (echo + create archive dir)
      - Source archive.sh, invoke `archive_change <name>`
      - Assert: `git log --oneline` has NO new commits; `git status --porcelain` shows archive/specs as `??` (untracked); stdout contains "跳过 git merge/commit" and "SKIPPED"
    - Add new case 3: **true-mode control**:
      - Default `.rddf/project.yaml` (no openspec_tracked field, defaults to true)
      - Same invocation
      - Assert: `git log --oneline` shows new commit with subject `archive(<name>): archive completed`
  - Test: AC-1, AC-2, AC-3

- [x] **Task 4: Extend `tests/integration/test_commit_archive_moves.bats`**
  - Modify: `tests/integration/test_commit_archive_moves.bats`
  - Diff: add new `@test` case
    - Setup: repo with `.rddf/project.yaml` `git.openspec_tracked: false` + dirty working tree (mimic post-archive state)
    - Source archive.sh, invoke `commit_archive_moves <name> <main_root>` directly
    - Assert: return 0; `git log --oneline` has NO new commit; stdout contains "SKIPPED"
  - Test: AC-4

### Phase C — Documentation sync (P1)

- [x] **Task 5: AGENTS.md "Archive Auto-Commit" section**
  - Modify: `AGENTS.md` "Archive Auto-Commit (v2.0.4 新增)" section
  - Diff: add one-line note: "**Skip when `git.openspec_tracked: false`**: openspec moves remain untracked in working tree (per `archive-openspec-tracked-skip-git` spec)."
  - Test: N/A (doc only)

- [x] **Task 6: README.md `git.openspec_tracked` field row**
  - Modify: `README.md` "支持的字段" table (L99 area)
  - Diff: change row text from "false 强制 rdd-builder 轻量模式" to "false → 强制轻量模式 + archive 不产生 git commit"
  - Test: N/A (doc only)

- [x] **Task 7: CHANGELOG.md entry**
  - Modify: `CHANGELOG.md` `[Unreleased]` section
  - Diff: add bullet "**fix**: `archive_change` now fully respects `git.openspec_tracked: false` (skips `commit_archive_moves` in addition to `git merge`); closes spec-implementation gap in ADR-0036 M3. See `openspec/changes/fix-archive-openspec-tracked-commit/`."
  - Test: N/A (doc only)

- [x] **Task 8: ADR-0036 §Implementation M3 row note**
  - Modify: `docs/adr/ADR-0036-rddf-project-yaml-config.md` L76 M3 row
  - Diff: change "✅ 已实施" to "✅ 已实施 (含 `commit_archive_moves` 守卫，per fix-archive-openspec-tracked-commit)"
  - Test: N/A (doc only)

### Phase D — Verification (P0, gates)

- [x] **Task 9: Targeted bats run**
  - Run: `bats tests/integration/test_archive_with_openspec_tracked_false.bats`
  - Expect: all cases pass (including new behavioral tests)
  - Run: `bats tests/integration/test_commit_archive_moves.bats`
  - Expect: all cases pass (including new openspec_tracked=false case)
  - Test: AC-5

- [x] **Task 10: Full regression gate**
  - Run: `./test.sh --full --regression`
  - Expect: no new failures beyond `tests/KNOWN_FAILURES.txt` baseline (per AGENTS.md "Archive 前全量回归门")
  - Test: AC-6

### Phase E — Commit + Archive

- [x] **Task 11: Worktree-internal aggregated commit**
  - Run: `git add openspec/changes/fix-archive-openspec-tracked-commit/ _lib/archive.sh tests/integration/test_archive_with_openspec_tracked_false.bats tests/integration/test_commit_archive_moves.bats AGENTS.md README.md CHANGELOG.md docs/adr/ADR-0036-rddf-project-yaml-config.md`
  - Run: `git commit -m "fix(archive): respect git.openspec_tracked=false in commit_archive_moves

  Per ADR-0036 M3 + complete-project-yaml-config-gaps spec
  §archive-openspec-tracked-skip-git (L246-262):
  - _lib/archive.sh L561: remove commit_archive_moves call in false branch
  - _lib/archive.sh::commit_archive_moves(): add openspec_tracked guard
  - tests/integration/test_archive_with_openspec_tracked_false.bats: upgrade to behavioral tests
  - tests/integration/test_commit_archive_moves.bats: add openspec_tracked=false case
  - Docs: AGENTS.md + README.md + CHANGELOG + ADR-0036

  Closes implementation_gap on adopted spec. Per rdd-verifier (ADR-0034)."`
  - Test: N/A (commit only)
  - Note: This is the **last time** openspec/ changes enter git — after this archive, all future openspec/ changes will not commit due to the fix.

- [x] **Task 12: Archive the change**
  - Run: `openspec archive fix-archive-openspec-tracked-commit --yes`
  - Effect: moves `openspec/changes/fix-archive-openspec-tracked-commit/` to `openspec/changes/archive/2026-09-10-fix-archive-openspec-tracked-commit/`
  - Commit: auto-commit helper runs `commit_archive_moves` (which is now no-op for this archive because the fix lands in the same commit). Archive's own auto-commit is the LAST commit that touches openspec/.
  - Test: N/A (archive flow)