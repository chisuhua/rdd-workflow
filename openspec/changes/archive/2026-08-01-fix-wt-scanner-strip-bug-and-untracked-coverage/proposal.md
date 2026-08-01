## Why

The rdd-workflow `guide` recommender's working-tree scanner (`_detect_working_tree_issues` in `skills/_lib/workflow_synthesizer.py`) misclassifies working-tree-only changes as staged and truncates the leading path character, while silently omitting normal untracked files such as new `improvements/*.md`. In session 2026-08-01, a dirty master tree with ` M proposal-suggestions.md` and two `?? improvements/*.md` files was reported as a single `staged` issue with path `roposal-suggestions.md`, leaving the untracked files invisible to the cleanup menu.

The root cause is twofold: (1) `result.stdout.strip().split("\n")` strips the leading space from the two-character `git status --short` prefix, so ` M` becomes `M ` and shifts the path slice; (2) the untracked branch uses `git ls-files --others --exclude-standard --directory` and filters for entries ending with `/`, so individual untracked files are dropped.

## What Changes

- `skills/_lib/workflow_synthesizer.py:725`: replace `result.stdout.strip().split("\n")` with `result.stdout.splitlines()` so the two-character status prefix and the path are preserved.
- `skills/_lib/workflow_synthesizer.py:771-797`: remove the `--directory` flag from `git ls-files`, drop the `endswith("/")` filter, and report individual untracked files as `category="untracked_file"` with `severity="info"`; keep the >10MB directory path as `category="untracked_dirs"` with `severity="safe_auto_fix"`.
- `skills/_lib/workflow_synthesizer.py:124` and `:519-521`: update the `WorkingTreeIssue` category docstring to include `"untracked_file"` and add an untracked count to the cleanup-menu summary so the issue total matches the displayed breakdown.
- Add `tests/unit/test_wt_scanner_strip_bug.py` with three cases covering ` M`, `M `, and `??` input handling after the splitlines fix.
- Add `tests/unit/test_wt_scanner_untracked.py` with four cases covering a single untracked file, a large untracked directory, a hidden directory, and a gitignored directory.
- Add `tests/integration/test_guide_entry_wt_issues.bats` to assert that `guide_entry --json` output is byte-identical on a clean tree before and after the fix and that the new `untracked_file` issues have `severity="info"`.

## Capabilities

### New Capabilities

- `wt-scanner-strip-fix`: The `_detect_working_tree_issues` scanner preserves `git status --short` two-character prefixes by using `splitlines()`, so working-tree-only modifications (` M`) are reported as `category="modified"` with full paths and staged modifications (`M `) are reported as `category="staged"` without truncation.
- `untracked-file-detection`: The scanner reports individual untracked files (e.g. `improvements/*.md`) as `category="untracked_file"` with `severity="info"`, while continuing to report large untracked directories as `category="untracked_dirs"` with `severity="safe_auto_fix"`.

### Modified Capabilities

(none — this change is additive and fixes misclassification; no existing spec-level behavior is changed beyond making the scanner output match the documented contract.)

## Impact

- Fixes two independent bugs in a single function without altering other `git status` consumers or the `wt_issues` JSON schema shape.
- Adds one new `untracked_file` category value and keeps all existing categories (`deleted`, `modified`, `staged`, `untracked_dirs`) unchanged.
- The `info` severity keeps untracked files from triggering gates or changing the recommendation menu on a clean tree; regression tests enforce byte-identical `guide_entry --json` output when no real issues exist.
- Total code change is targeted at ~20 lines; no scanner refactor, file hashing, or `.rddf/state` schema changes.
