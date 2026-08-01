## Context

`skills/_lib/workflow_synthesizer.py` contains `_detect_working_tree_issues()`, a helper used by the `guide` recommender to turn `git status --short` and `git ls-files --others` output into a structured list of `WorkingTreeIssue` objects. The function is called during every `guide_entry` invocation, both in interactive and `--json` mode.

On 2026-08-01 the scanner reported a single working-tree issue on a dirty master tree where the real state was ` M proposal-suggestions.md` plus two untracked `improvements/*.md` files. The reported issue was classified as `staged` and its path was `roposal-suggestions.md` (missing the leading `p`), and the two untracked files were omitted entirely. Two independent bugs in the same function caused this.

## Goals / Non-Goals

**Goals:**
- Fix the prefix/path truncation bug by replacing `result.stdout.strip().split("\n")` with `result.stdout.splitlines()`.
- Fix the untracked-file omission bug by removing the `--directory` flag, dropping the `endswith("/")` filter, and reporting individual untracked files as `category="untracked_file"` with `severity="info"`.
- Keep the existing large-directory behavior (`untracked_dirs`, `safe_auto_fix`, `.gitignore` command) unchanged.
- Update the `WorkingTreeIssue` docstring and the cleanup-menu summary consumer to include the new category.
- Add focused pytest and bats regression tests that lock both fixes and prove zero byte-level change on a clean tree.
- Preserve the existing `wt_issues` JSON shape and deduplication logic; the new category must be purely additive.

**Non-Goals:**
- Do not rewrite the whole scanner algorithm or move it to a different module.
- Do not change `check_dirty_key_files` in the bash layer (it is logic-independent of this Python bug).
- Do not add `--ignored`/`--modified` extra flags to `git status`, file hashing, incremental detection, or a separate `??` prefix model.
- Do not modify shared state files, iteration state, roadmap, or other OpenSpec changes.
- Do not gate or block the `guide` recommender on `info`-severity untracked files.

## Decisions

- **One-line splitlines fix for root cause 1**: The current code strips the leading whitespace of the ` M` prefix before splitting lines. Switching to `splitlines()` preserves every byte of each line except the line terminator, so the two-character prefix and the path starting at index 3 are both correct. This is the smallest possible change and directly addresses the root cause.
- **Remove `--directory` and the directory-only filter for root cause 2**: `git ls-files --others --exclude-standard --directory` collapses untracked directories into single `dir/` rows and drops individual files. Removing `--directory` returns every untracked file and directory, which lets us treat files as `untracked_file` and still walk directories for size. The `--exclude-standard` flag stays so `.gitignore` and `.git/info/exclude` rules remain honored.
- **Info severity for untracked files**: New untracked files (especially `improvements/*.md`) are often intentional drafts. Reporting them as `info` keeps the cleanup menu visible but does not trigger any gate or change the recommendation on an otherwise clean tree.
- **Keep `untracked_dirs` safe_auto_fix behavior**: Large untracked directories still carry `severity="safe_auto_fix"` and a fix command that appends the directory to `.gitignore`. This is unchanged; only the source list is broadened.
- **Update docstring and cleanup-menu summary**: Adding `untracked_file` to the `WorkingTreeIssue` docstring and adding an untracked count to the menu summary keeps the category contract and UI consistent. The count update is a small additive change in the existing consumer loop.
- **Test strategy**: Two pytest unit modules cover the two root causes in isolation using `git init` temp repos, plus one bats integration test that runs `guide_entry --json` and diff's the output against the pre-fix baseline. This gives unit-level precision and end-to-end regression protection without adding dependencies.

## Risks / Trade-offs

- [Risk] `splitlines()` splits on all universal newlines, while the original code split on `\n` after `strip()`. `git status --short` uses `\n` line endings, so behavior is identical on the repository's supported platforms. → Mitigation: tests run on Linux and the output is `text=True`, so `\r\n` is already normalized by Python.
- [Risk] Removing `--directory` will return one entry per untracked file inside a large directory, then `os.walk` is still used for size. This is a small extra cost for directories, but the timeout is short and the list is limited by the repository. → Mitigation: keep the existing 5-second timeout and rely on `os.walk` with OSError handling; no extra caching is introduced to stay within the line-count budget.
- [Risk] Adding `untracked_file` to the `wt_issues` list changes the count shown in the cleanup menu label even when no gate is triggered. → Mitigation: the cleanup-menu summary is updated to include untracked files, so the displayed total matches the breakdown.
- [Risk] Consumers that parse `wt_issues` JSON may not recognize `untracked_file`. → Mitigation: the new category is `info`-severity only and the spec includes a backward-compatibility scenario requiring existing consumers to skip or display raw unknown categories without failure. The JSON schema is not changed.
- [Risk] Hidden directories (`entry.startswith(".")`) were previously skipped; after the change they will be skipped by the `.git/info/exclude` and `.gitignore` rules via `--exclude-standard`, but a bare `.hidden/` dir might be returned. → Mitigation: keep the `entry.startswith(".")` guard for files and directories, because hidden items should remain unreported.

## Migration Plan

N/A — this is an additive bug fix. No data migration is required; `.rddf/state/` files and existing OpenSpec changes are untouched. Consumer projects will see the corrected scanner output automatically.

## Open Questions

None.
