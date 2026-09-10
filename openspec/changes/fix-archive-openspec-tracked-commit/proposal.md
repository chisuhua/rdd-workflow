# fix-archive-openspec-tracked-commit

> Per [ADR-0036](docs/adr/ADR-0036-rddf-project-yaml-config.md) M3 + [complete-project-yaml-config-gaps spec §archive-openspec-tracked-skip-git](openspec/specs/complete-project-yaml-config-gaps/spec.md#requirement-archive-openspec-tracked-skip-git).
> Closes the implementation gap in ADR-0036 M3 delivery: `git.openspec_tracked: false` skips `git merge` but does NOT skip `commit_archive_moves` in `_lib/archive.sh` L561.

## Why

ADR-0036 M3 (2026-09-02, 已采纳 + 已实施) introduced `git.openspec_tracked: false` to allow projects whose `openspec/` should never be tracked by git (heterogeneous projects like ChipForge hardware verification, doc-driven workflows). The accompanying spec [complete-project-yaml-config-gaps/spec.md §archive-openspec-tracked-skip-git](openspec/specs/complete-project-yaml-config-gaps/spec.md) L246-262 was ratified in the same change and explicitly mandates:

> WHEN `git.openspec_tracked: false`
> THEN `archive_change()` SHALL NOT execute `commit_archive_moves`
> AND SHALL execute only `openspec archive` + `mark_iteration_archived`.

**However, the implementation does NOT honor this requirement.** Reading `_lib/archive.sh`:

```bash
# L553-564 (false branch)
if [ "$openspec_tracked" = "false" ] || [ "$openspec_tracked" = "False" ]; then
    echo "📦 openspec_tracked=false: 跳过 git merge/commit"
    switch_to_default_branch "$main_root" "$default_branch" || return 1
    if ! openspec archive "$name" --yes; then
      echo "❌ openspec archive 失败"
      return 1
    fi
    cleanup_worktree_and_branch "$name" "$main_root" "$wt_path" "$branch" || true
    commit_archive_moves "$name" "$main_root" || true   # ← SPEC VIOLATION
    mark_iteration_archived "$name" "$main_root" ""
    return 0
fi
```

`commit_archive_moves` (L789-828) unconditionally runs `git add openspec/changes/${name}/ openspec/changes/archive/ openspec/specs/ && git commit -m "archive(${name}): archive completed"` — so even with `git.openspec_tracked: false`, the archive step still creates a commit that pulls `openspec/changes/archive/<name>/` and `openspec/specs/<name>/` into git.

### When does this bite?

- **Greenfield project starting with `openspec_tracked: false`** — `commit_archive_moves` sees a clean working tree (nothing was ever tracked) and exits at L800-802 with no-op. **Bug masked.**
- **Mixed-state project**: flag set after some `openspec/` files were already committed (e.g., a project that later adopts `openspec_tracked: false`) — `openspec archive` moves tracked→untracked, `commit_archive_moves` sees the moves, commits them. **Bug bites hard**: the setting becomes a lie.

### Impact

- Spec compliance failure (rdd-verifier would classify as `implementation_gap`)
- Heterogeneous-project users cannot reliably keep `openspec/` out of git
- Documentation drift: AGENTS.md "Archive Auto-Commit" section (v2.0.4) does not mention the `openspec_tracked=false` interaction
- Test gap: `tests/integration/test_archive_with_openspec_tracked_false.bats` has 3 cases, but 2 are grep-source-text rather than behavioral — the bug passes tests

## What Changes

### Code edits (P0 — must land)

1. **`_lib/archive.sh` L561 (false branch)**: **delete** the line `commit_archive_moves "$name" "$main_root" || true`. Per spec L254, the false branch SHALL NOT execute `commit_archive_moves`.
2. **`_lib/archive.sh::commit_archive_moves()` L789-828**: add a `git.openspec_tracked` guard **after** the existing `SKIP_ARCHIVE_AUTO_COMMIT` check (L795-798) and **before** the `git status` no-op exit (L800-802). Pattern matches the L546-550 reader:
  ```bash
  # Honor git.openspec_tracked=false (defense-in-depth: any future caller)
  local _tracked="true"
  if [ -f "$main_root/.rddf/project.yaml" ] && [ -f "$main_root/_lib/project_config.sh" ]; then
    source "$main_root/_lib/project_config.sh"
    _tracked=$(project_yaml_get "git.openspec_tracked" "true")
  fi
  if [ "$_tracked" = "false" ] || [ "$_tracked" = "False" ]; then
    echo "ℹ️  commit_archive_moves: SKIPPED (git.openspec_tracked=false)"
    return 0
  fi
  ```
  Rationale: single-point-of-truth guard protects all current + future callers (L786 docstring already notes historical multi-call-site risk).
3. **No changes to** `phase2_execute.sh` / `phase3_archive.sh` (verified: neither calls `commit_archive_moves`; the only current caller is `archive_change`).

### Test additions (P0)

1. **Upgrade `tests/integration/test_archive_with_openspec_tracked_false.bats`** (current 3 cases use grep-source-text rather than behavioral assertions — replace case 2/3 with real behavioral tests):
   - **New behavioral test** (mixed-state setup): seed repo with tracked `openspec/` files, set `git.openspec_tracked: false`, stub `openspec` CLI on PATH, invoke `archive_change` → assert `git log` has NO new commit, `git status` shows archive/specs as untracked, stdout contains "跳过 git merge/commit".
   - **New true-mode control**: `git.openspec_tracked: true` (default) → `archive_change` produces `archive(<name>): archive completed` commit (locks existing behavior).
   - **Keep case 1** (function existence smoke) for regression guard.
2. **Extend `tests/integration/test_commit_archive_moves.bats`**: add `openspec_tracked=false` case → `commit_archive_moves` returns 0, no `git add` / `git commit` executed, stdout contains "SKIPPED".

### Backward compatibility

- `git.openspec_tracked: true` (default) → zero behavior change. L566-599 path untouched.
- `SKIP_ARCHIVE_AUTO_COMMIT=yes` env var continues to work as universal escape hatch (covers true-mode users too).
- Mixed-state repos (already-tracked `openspec/`) will see `openspec/` permanently move to untracked after archive — **this is the desired behavior per user requirement**.

### Documentation sync

- **AGENTS.md** "Archive Auto-Commit" section: add one line about `openspec_tracked=false` interaction.
- **README.md** "项目级配置" section table (L99): clarify `git.openspec_tracked: false` semantics ("且 archive 不产生 git commit").
- **CHANGELOG.md**: add entry under current [Unreleased].
- **ADR-0036 §Implementation** (L76 table): amend M3 row to note that `commit_archive_moves` guard is part of M3 scope.
- **No new ADR** — spec already covers the requirement.

## Acceptance Criteria

- **AC-1**: With `.rddf/project.yaml` `git.openspec_tracked: false`, `archive_change <name>` does NOT execute `git commit` (verified by `git log --oneline` showing no new commits after invocation).
- **AC-2**: With `.rddf/projectacked: false`, `archive_change <name>` does execute `openspec archive` and `mark_iteration_archived` (verified by archive directory move + iteration.json update).
- **AC-3**: With `git.openspec_tracked: true` (default), `archive_change <name>` continues to produce exactly one `archive(<name>): archive completed` commit (verified by `git log` showing the commit subject).
- **AC-4**: `commit_archive_moves` standalone invocation respects `git.openspec_tracked: false` (verified by unit test returning 0 with no git activity).
- **AC-5**: All bats cases pass: `bats tests/integration/test_archive_with_openspec_tracked_false.bats`, `bats tests/integration/test_commit_archive_moves.bats`.
- **AC-6**: Full regression gate passes: `./test.sh --full --regression` reports no new failures beyond `tests/KNOWN_FAILURES.txt` baseline.

## Out of scope

- `.gitignore` for `openspec/` (方案 C — rejected; breaks state-detection)
- Removing the `openspec_tracked` config field (still useful for execution_mode resolution)
- Changes to `openspec-gate` skill (staged-files-warning is independent)

## Why priority P1

This is an `implementation_gap` per rdd-verifier classification (ADR-0034): the spec is approved and adopted, but the implementation does not satisfy it. ADR-0036 §Consequences (L64) explicitly flagged this risk: "任何错误会破坏现有归档路径". P1 (not P0) because:
- Workaround exists: `SKIP_ARCHIVE_AUTO_COMMIT=yes` env var (already in code at L795-798)
- Only affects projects with mixed-state `openspec/` history
- No data loss, no security implication

## Tasks

See `tasks.md`.