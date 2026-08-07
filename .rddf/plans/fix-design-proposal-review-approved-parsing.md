# fix-design-proposal-review-approved-parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three call sites that silently see zero approved proposals because they parse only the (usually empty) `## 已批准提案` section. Extract a single helper that reads both `## 已批准提案` and `## 已实施` sections, deduplicated, and rewire all three call sites to use it.

**Architecture:** A pure read-only helper (`_lib/parse_approved.py`) does the parsing. Real implementation lives at `_lib/parse_approved.py`; a one-line shim at `skills/_lib/parse_approved.py` keeps the existing `from skills._lib.X import …` import pattern working for `propose_change.py` (matches the `skills/_lib/iteration/__init__.py` shim convention). The helper is dual-mode: importable function `parse_approved_proposals(path) -> list[str]` and a `__main__` CLI guard that prints names one per line, so bash call sites use the same `python3 "$(resolve_rdd_lib_dir)/parse_approved.py" "$FILE"` pattern that `_lib/validate_delta_targets.py` already established. All three call sites use the Oracle C1 env-var pattern (no bash string interpolation; the existing AGENTS.md Round A `roadmap_exists` lesson applies).

**Tech Stack:** Python 3.11+ stdlib (`re`, `pathlib`), bash 4+. Tests: pytest (unit) + bats-core (integration).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/parse_approved.py` | Real implementation. `parse_approved_proposals(path: str) -> list[str]` plus a `__main__` CLI guard for bash invocation. |
| `skills/_lib/parse_approved.py` | One-line shim re-exporting `_lib.parse_approved` so existing `from skills._lib.X import …` imports keep working (mirrors `skills/_lib/iteration/__init__.py`). |
| `skills/guide-design/scripts/design_proposal_review.sh` | Replace inline `python3 -c` heredoc with a call to the helper via `python3 "$(resolve_rdd_lib_dir)/parse_approved.py" "$APPROVED_FILE"`. |
| `skills/guide/scripts/scan-state.sh` | Replace inline approved-detection heredoc with the helper invocation; `HAS_APPROVED` becomes `"yes"` iff the helper prints at least one line. |
| `skills/propose/scripts/propose_change.py` | Replace the `re.split(r"## 已实施", content)[0]` block at lines ~430-444 with a call to `parse_approved_proposals`. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_parse_approved.py` | pytest coverage for 5 cases (missing file, empty file, only approved section, only implemented section, both sections dedup) plus a CLI-guard case. |
| `tests/integration/test_approved_parsing_fix.bats` | bats coverage for all three call sites end-to-end against the real `proposal-approved.md`. |

---

### Task 1: Helper implementation + unit tests (TDD cycle)

**Files:**
- Create: `_lib/parse_approved.py`
- Create: `skills/_lib/parse_approved.py` (shim)
- Create: `tests/unit/test_parse_approved.py`

- [ ] **Step 1: Write the failing tests in `tests/unit/test_parse_approved.py`**

```python
"""Unit tests for parse_approved_proposals."""
from __future__ import annotations

from pathlib import Path

import pytest

from _lib.parse_approved import parse_approved_proposals


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "proposal-approved.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    result = parse_approved_proposals(str(tmp_path / "does-not-exist.md"))
    assert result == []


def test_empty_file_returns_empty(tmp_path: Path) -> None:
    p = _write(tmp_path, "")
    assert parse_approved_proposals(str(p)) == []


def test_only_approved_section(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "## 已批准提案\n\n"
        "| [alpha](improvements/alpha.md) | P1 | 2026-08-01 | arch |\n"
        "| [beta](improvements/beta.md) | P2 | 2026-08-02 | arch |\n"
        "\n## 已实施\n",
    )
    assert parse_approved_proposals(str(p)) == ["alpha", "beta"]


def test_only_implemented_section(tmp_path: Path) -> None:
    # The real-world case: everything lives in ## 已实施
    p = _write(
        tmp_path,
        "## 已批准提案\n\n## 已实施\n\n"
        "| [gamma](improvements/gamma.md) | P0 | 2026-08-07 | arch |\n"
        "| [delta](improvements/delta.md) | P1 | 2026-08-06 | arch |\n",
    )
    assert parse_approved_proposals(str(p)) == ["gamma", "delta"]


def test_both_sections_dedup_keep_order(tmp_path: Path) -> None:
    # gamma appears in BOTH sections; should appear once, in first-appearance order
    p = _write(
        tmp_path,
        "## 已批准提案\n\n"
        "| [alpha](improvements/alpha.md) | P1 | 2026-08-01 | arch |\n"
        "\n## 已实施\n\n"
        "| [alpha](improvements/alpha.md) | P1 | 2026-08-02 | arch |\n"
        "| [beta](improvements/beta.md) | P2 | 2026-08-03 | arch |\n",
    )
    assert parse_approved_proposals(str(p)) == ["alpha", "beta"]


def test_real_repo_proposal_approved(tmp_path: Path) -> None:
    # Sanity check against the actual proposal-approved.md at repo root.
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "proposal-approved.md"
    if not target.exists():
        pytest.skip("proposal-approved.md not present in this checkout")
    names = parse_approved_proposals(str(target))
    # Must include entries that previously returned 0 (all entries were in ## 已实施)
    assert "fix-design-proposal-review-approved-parsing" in names
    # And the helper must return more than zero entries (the original bug)
    assert len(names) > 0


def test_cli_guard_prints_one_name_per_line(tmp_path: Path) -> None:
    # Run the file as a script and verify the __main__ branch.
    import subprocess
    import sys

    p = _write(
        tmp_path,
        "## 已实施\n\n"
        "| [gamma](improvements/gamma.md) | P0 | 2026-08-07 | arch |\n"
        "| [delta](improvements/delta.md) | P1 | 2026-08-06 | arch |\n",
    )
    repo_root = Path(__file__).resolve().parents[2]
    helper = repo_root / "_lib" / "parse_approved.py"
    out = subprocess.run(
        [sys.executable, str(helper), str(p)],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.splitlines() == ["gamma", "delta"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m pytest tests/unit/test_parse_approved.py -v`
Expected: `ModuleNotFoundError: No module named '_lib.parse_approved'` for every test.

- [ ] **Step 3: Implement `_lib/parse_approved.py`**

```python
"""Centralized parser for proposal-approved.md.

Reads BOTH the `## 已批准提案` and `## 已实施` sections and returns
approved proposal names, deduplicated, in file-appearance order.

Design choice: full-file regex matching of the row pattern
`| [name](improvements/<file>.md) | ... |`. The `已批准提案` section holds
approved-but-not-implemented entries; `已实施` holds approved-and-implemented
entries. Historical proposals were archived directly after approval, so
`已批准提案` is often empty in practice — parsers that only read the region
before `## 已实施` silently see zero approved entries (this was the bug).

This helper is the single source of truth for approved-name extraction. It
complements `detect-suggestions-approved-inconsistency` (which fixed the
data-view consistency between suggestions/approved, not the parsing logic
itself).

CLI mode (for bash invocation):

    python3 _lib/parse_approved.py <path-to-proposal-approved.md>

prints each name on its own line, in file-appearance order, deduplicated.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Match a markdown table row like `| [name](improvements/<file>.md) | ...`.
# Only used inside proposal-approved.md (and similar tables), so the
# `improvements/` anchor is enough to avoid false positives in body prose.
_ROW_RE = re.compile(r"\|\s*\[([^\]]+)\]\(\s*improvements/[^)]+\)")


def parse_approved_proposals(path: str) -> list[str]:
    """Return approved proposal names from both sections of proposal-approved.md.

    Args:
        path: Filesystem path to proposal-approved.md.

    Returns:
        Proposal names in file-appearance order, deduplicated. Empty list
        when the file is missing, unreadable, or has no matching rows.
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    seen: set[str] = set()
    names: list[str] = []
    for match in _ROW_RE.finditer(content):
        name = match.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: parse_approved.py <path-to-proposal-approved.md>", file=sys.stderr)
        sys.exit(2)
    for name in parse_approved_proposals(sys.argv[1]):
        print(name)
```

- [ ] **Step 4: Create the shim `skills/_lib/parse_approved.py`**

```python
"""Shim re-exporting _lib.parse_approved so `from skills._lib.X import …`
keeps working for callers in skills/propose/scripts (matches the
`skills/_lib/iteration/__init__.py` shim convention)."""
from _lib.parse_approved import *  # noqa: F401,F403
from _lib.parse_approved import parse_approved_proposals  # noqa: F401
```

- [ ] **Step 5: Run the unit tests and verify they pass**

Run: `python3 -m pytest tests/unit/test_parse_approved.py -v`
Expected: 7 passed.

---

### Task 2: Rewire `propose_change.py` (Python call site)

**Files:**
- Modify: `skills/propose/scripts/propose_change.py:425-448` (replace the inline `re.split(r"## 已实施", content)[0]` block with a helper call)
- Verify: `python3 -c "from skills.propose.scripts.propose_change import _parse_approved; print(_parse_approved())"` against the real `proposal-approved.md`

- [ ] **Step 1: Add the import**

In `skills/propose/scripts/propose_change.py`, alongside the existing
`from skills._lib import …` lines near the top, add:

```python
from skills._lib.parse_approved import parse_approved_proposals
```

- [ ] **Step 2: Replace the inline parsing block**

Find the block (currently lines ~430-444):

```python
    approved_file = os.path.join(project_root, "proposal-approved.md")
    if not os.path.exists(approved_file):
        return []
    with open(approved_file) as f:
        content = f.read()
    section = re.split(r'## 已实施', content)[0]
    rows = re.findall(r'\[\s*([^\]]+)\]\s*\(\s*improvements/([^)]+)\s*\)', section)
    created = []
```

Replace with:

```python
    approved_file = os.path.join(project_root, "proposal-approved.md")
    rows = [(name, "") for name in parse_approved_proposals(approved_file)]
    created = []
```

(The `("", "")` second element preserves the original 2-tuple shape consumed
further down by `create_skeleton_change(...)`.)

- [ ] **Step 3: Smoke-check the rewired function against the real file**

Run (from repo root):

```bash
python3 -c "
from skills.propose.scripts import propose_change
print(len(propose_change._batch_create_approved_skeletons('.', dry_run=True)))
"
```

Expected: an integer > 0 (in this repo: 122+ previously-zero entries are now
visible). If your CLI exposes a different name, substitute the actual symbol;
the contract is: must return more than 0 entries and must include the
P0 entry `fix-design-proposal-review-approved-parsing`.

(If the symbol is private and you cannot call it directly, run
`openspec list --changes` and confirm no false-positive proposal creation
prompt appears — i.e. the function does not try to re-create the existing
change. This is the user-visible regression check.)

- [ ] **Step 4: Run the unit tests for the touched file (regression check)**

Run: `python3 -m pytest tests/unit/ -q -x -k "propose or approved"`
Expected: passes.

---

### Task 3: Rewire `design_proposal_review.sh` (bash call site, site #1)

**Files:**
- Modify: `skills/guide-design/scripts/design_proposal_review.sh:74-86`

- [ ] **Step 1: Read the current block**

Verify the current shape (Oracle C1 heredoc) at lines 74-86 looks like:

```bash
  local APPROVED_NAMES=""
  if [ -f "$APPROVED_FILE" ]; then
    APPROVED_NAMES=$(PY_APPROVED_FILE="$APPROVED_FILE" python3 -c '
import os, re, sys
path = os.environ["PY_APPROVED_FILE"]
with open(path) as f:
    content = f.read()
section = re.split(r"## 已实施", content)[0]
for m in re.finditer(r"\|\s*\[([^\]]+)\]\([^)]+\)", section):
    print(m.group(1))
' 2>/dev/null || true)
  fi
```

- [ ] **Step 2: Replace with a helper invocation**

Replace the entire block with:

```bash
  local APPROVED_NAMES=""
  if [ -f "$APPROVED_FILE" ]; then
    # Oracle C1 safe: file path via env var; helper does its own parsing.
    APPROVED_NAMES=$(PY_APPROVED_FILE="$APPROVED_FILE" PY_RDD_LIB="$(resolve_rdd_lib_dir)" python3 '
import os, sys
sys.path.insert(0, os.environ["PY_RDD_LIB"])
from parse_approved import parse_approved_proposals
for name in parse_approved_proposals(os.environ["PY_APPROVED_FILE"]):
    print(name)
' 2>/dev/null || true)
  fi
```

If the script does not already source `skills/_lib/skill_root.sh` to make
`resolve_rdd_lib_dir` available, add the source line at the top of the file
(under the `set -e`/`set -u` block):

```bash
source "${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/skill_root.sh" \
  || source "$HOME/.agents/skills/_lib/skill_root.sh" \
  || true
```

- [ ] **Step 3: Smoke-check the rewired script against the real file**

Run (from repo root):

```bash
bash skills/guide-design/scripts/design_proposal_review.sh 2>&1 \
  | grep -c "fix-design-proposal-review-approved-parsing"
```

Expected: 0 (the change is already in `## 已批准提案` but approved AND
handled — the listing should not flag it as pending; alternatively grep for
your own check condition; the assertion is that the previously mis-listed
entries are gone).

The precise regression assertion for this repo is:

```bash
bash skills/guide-design/scripts/design_proposal_review.sh 2>&1 \
  | grep -E "RDDF-0001-fix-rddf-session-import-path|fix-rddf-session-owner-cross-call|ship-delete-branch-safety"
```

Expected: empty output. (Those three were mis-flagged as pending review on
2026-08-07 before this fix.)

- [ ] **Step 4: Run the focused bats suite for guide-design (regression check)**

Run: `bats tests/integration/test_design_proposal_review_no_false_pending.bats`
Expected: passes. (If this file does not yet exist, that is expected at this
point — Task 4 creates it. Run `bats tests/integration/` to confirm no
regression in the existing suite.)

---

### Task 4: Rewire `scan-state.sh` (bash call site, site #2)

**Files:**
- Modify: `skills/guide/scripts/scan-state.sh:265-290` (replace the inline approved-detection heredoc with a helper invocation; `HAS_APPROVED` becomes "yes" iff the helper prints at least one line)

- [ ] **Step 1: Read the current block**

Confirm the current shape at lines 265-290 contains a `python3 -c` heredoc
that does `re.split(r"## 已实施", content)` and checks for table rows.

- [ ] **Step 2: Replace the heredoc with a helper invocation**

Replace the inline parsing with:

```bash
  local APPROVED_COUNT
  APPROVED_COUNT=$(PY_PROJECT_ROOT="$PROJECT_ROOT" PY_RDD_LIB="$(resolve_rdd_lib_dir)" python3 '
import os, sys
sys.path.insert(0, os.environ["PY_RDD_LIB"])
from parse_approved import parse_approved_proposals
approved = os.path.join(os.environ["PY_PROJECT_ROOT"], "proposal-approved.md")
print(len(parse_approved_proposals(approved)))
' 2>/dev/null || echo 0)

  if [ "${APPROVED_COUNT:-0}" -gt 0 ]; then
    HAS_APPROVED="yes"
  else
    HAS_APPROVED="no"
  fi
```

Ensure `resolve_rdd_lib_dir` is available: if `scan-state.sh` does not
already source `skills/_lib/skill_root.sh`, add the standard source line
near the top (same pattern as Task 3 Step 2).

- [ ] **Step 3: Smoke-check the rewired dashboard count**

Run:

```bash
bash skills/guide/scripts/scan-state.sh 2>&1 \
  | grep -E "approved|HAS_APPROVED|approved_count"
```

Expected: a count > 0 (this repo's dashboard previously reported 0;
the fix should make it report 122+).

- [ ] **Step 4: Run the focused bats suite for scan-state (regression check)**

Run: `bats tests/integration/test_scan_state_approved_count.bats`
Expected: passes. (If this file does not yet exist, that is expected at
this point — Task 5 creates it.)

---

### Task 5: Add bats integration tests + grep audit + full regression

**Files:**
- Create: `tests/integration/test_approved_parsing_fix.bats` (covers all three call sites end-to-end)
- Verify: `grep -rn 're\.split.*## 已实施' skills/` returns no matches in the three rewired sites

- [ ] **Step 1: Create `tests/integration/test_approved_parsing_fix.bats`**

```bats
#!/usr/bin/env bats
#
# Integration tests for the three rewired call sites. Each test runs the
# real call site against the real proposal-approved.md and asserts the
# fixed behavior (no false positives, real counts visible).

load test_helper

setup() {
    PROJECT_ROOT="$(pwd)"
    RDDF_LIB_DIR="$(cd "${HOME}/.agents/skills/_lib" 2>/dev/null && pwd || pwd)/_lib"
}

@test "design_proposal_review.sh no longer lists approved-implemented entries as pending" {
    run bash "${PROJECT_ROOT}/skills/guide-design/scripts/design_proposal_review.sh"
    # Three entries approved 2026-07-29 and listed as pending before the fix.
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q "RDDF-0001-fix-rddf-session-import-path"
    ! echo "$output" | grep -q "fix-rddf-session-owner-cross-call"
    ! echo "$output" | grep -q "ship-delete-branch-safety"
}

@test "scan-state.sh reports a positive approved count" {
    run bash "${PROJECT_ROOT}/skills/guide/scripts/scan-state.sh"
    [ "$status" -eq 0 ]
    # The dashboard line should contain a positive approved count.
    # In this repo the real number is 122+. Assert "> 0" loosely.
    echo "$output" | grep -qiE "approved:[[:space:]]*[1-9][0-9]*"
}

@test "propose_change.py recognizes approved entries from both sections" {
    run python3 - <<'PY'
import sys
sys.path.insert(0, ".")
from skills.propose.scripts import propose_change
# Direct call to the rewired function: must return > 0 entries from both
# sections, including at least the P0 entry that triggered this change.
names = [r[0] for r in propose_change._batch_create_approved_skeletons(".", dry_run=True)]
assert "fix-design-proposal-review-approved-parsing" in names, names
assert len(names) > 0, names
PY
    [ "$status" -eq 0 ]
}

@test "parse_approved helper is dual-mode (function + __main__ CLI)" {
    run python3 "${RDDF_LIB_DIR}/parse_approved.py" "${PROJECT_ROOT}/proposal-approved.md"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
    # First line should be a non-empty proposal name.
    [[ "$output" == *[!\ ]* ]]
}
```

(The exact private symbol name `_batch_create_approved_skeletons` may differ
from the implementation; substitute the actual exported function that the
`_create_skeleton_changes_for_approved` block uses, or test via a higher-
level observable: run `python3 -c "from skills.propose.scripts.propose_change
import _create_skeleton_changes_for_approved; print(len(_create_skeleton_changes_for_approved('.')))"`
and assert > 0.)

- [ ] **Step 2: Audit `skills/` for remaining inline parsers of the same pattern**

Run:

```bash
grep -rn 're\.split.*## 已实施' skills/
grep -rn 'split.*"## 已实施"' skills/
```

Expected: no matches. If a fourth call site appears (e.g. inside a new
script), rewire it to the helper in this same task before continuing.

- [ ] **Step 3: Run `./test.sh --quick` and verify green**

Run: `./test.sh --quick`
Expected: passes (~45s). Confirm:
- All new unit tests in `tests/unit/test_parse_approved.py` pass.
- The new bats test `tests/integration/test_approved_parsing_fix.bats` passes.
- No previously-green test turned red.

- [ ] **Step 4: Run the full regression gate (archive prerequisite)**

Run: `./test.sh --full --regression`
Expected: passes, with no NEW failures vs. `tests/KNOWN_FAILURES.txt`.
Record the result in the PR description (or commit message body for
the archive commit).

- [ ] **Step 5: Commit the work in the worktree (one aggregate commit)**

After all tasks pass, in the worktree directory:

```bash
git add -A
git commit -m "fix(approved-parsing): centralize proposal-approved parsing and rewire 3 call sites

- Add _lib/parse_approved.py::parse_approved_proposals (read-only helper,
  parses both ## 已批准提案 and ## 已实施 sections, dedup, file order)
- Shim skills/_lib/parse_approved.py re-exports the helper for the
  existing from skills._lib.X import pattern (matches the iteration
  shim convention)
- Rewire skills/guide-design/scripts/design_proposal_review.sh,
  skills/guide/scripts/scan-state.sh, skills/propose/scripts/propose_change.py
- Tests: tests/unit/test_parse_approved.py (pytest) + bats integration
  tests/integration/test_approved_parsing_fix.bats"
```

- [ ] **Step 6: Defer further commits to archive phase**

Per AGENTS.md Worktree Commit Flow: aggregate commit above is the only
commit on the branch. All archive-time bookkeeping (auto-commit, merge,
branch deletion) is handled by `guide-ship` Phase 3.