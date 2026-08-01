# fix-wt-scanner-strip-bug-and-untracked-coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two independent bugs in `_detect_working_tree_issues()` (`skills/_lib/workflow_synthesizer.py`) so the `guide` recommender (a) preserves `git status --short` two-character prefixes (no more truncated `roposal-suggestions.md`), and (b) reports individual untracked files (`improvements/*.md`) as `category="untracked_file"` with `severity="info"` instead of dropping them.

**Architecture:** Two one-line source changes in the existing scanner: replace `result.stdout.strip().split("\n")` with `result.stdout.splitlines()` so the ` M` prefix and the path slice stay aligned; drop `--directory` from `git ls-files --others --exclude-standard` and remove the `endswith("/")` filter so files flow into a new `untracked_file` branch while large directories still flow into the existing `untracked_dirs` branch via `os.walk` size aggregation. Update the `WorkingTreeIssue` category docstring and the cleanup-menu summary consumer to include the new category. Two focused pytest modules (one per root cause) using `git init` temp repos, plus one bats integration test that snapshots clean-tree `guide_entry --json` output and asserts `untracked_file` issues have `severity="info"`. No new dependencies; no schema migration; existing categories (`deleted`, `modified`, `staged`, `untracked_dirs`) unchanged.

**Tech Stack:** Python 3.11+ (`subprocess`, `os.walk`, `pathlib`), pytest 7+ (unit), bats 1.10+ (integration), git 2.25+.

**OpenSpec change artifacts** (canonical): `openspec/changes/fix-wt-scanner-strip-bug-and-untracked-coverage/{proposal,design,tasks}.md` + `specs/wt-scanner-strip-fix/spec.md` + `specs/untracked-file-detection/spec.md`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/workflow_synthesizer.py` | MODIFY line 725 (`splitlines()` fix); MODIFY line 124 (`WorkingTreeIssue` docstring add `untracked_file`); MODIFY lines 519-521 (cleanup-menu summary add `untracked_count`); REPLACE lines 771-797 (untracked branch: drop `--directory`, emit per-file `untracked_file` issues plus per-directory `untracked_dirs` issues) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_wt_scanner_strip_bug.py` | NEW: 3 pytest cases — ` M` → `modified` with full path, `M ` → `staged`, working-tree-only path not truncated |
| `tests/unit/test_wt_scanner_untracked.py` | NEW: 4 pytest cases — single untracked file → `untracked_file`/`info`, large untracked dir → `untracked_dirs`/`safe_auto_fix`, hidden dir skipped, gitignored dir skipped |
| `tests/integration/test_guide_entry_wt_issues.bats` | NEW: 2 bats cases — clean-tree `guide_entry --json` byte-identical to fixture, untracked `improvements/foo.md` produces `untracked_file`/`info` issue |
| `tests/integration/fixtures/guide_entry_clean.json` | NEW: snapshot of clean-tree `guide_entry --json` baseline used by the byte-identical assertion |

---

## Pre-flight

- [x] **Confirm baseline tests pass before any change**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_workflow_synthesizer.py -q --tb=short
```

Expected: existing synthesizer tests pass; record pass count.

- [x] **Locate the two bug sites and the docstring / consumer sites**

```bash
grep -n 'result.stdout.strip().split' skills/_lib/workflow_synthesizer.py
grep -n 'git ls-files --others' skills/_lib/workflow_synthesizer.py
grep -n 'category: ' skills/_lib/workflow_synthesizer.py
grep -n 'staged_count' skills/_lib/workflow_synthesizer.py
```

Expected: 4 anchor lines (725, ls-files invocation, docstring, staged_count) printed.

---

### Task 1: Fix working-tree prefix truncation bug

**Files:**
- Create: `tests/unit/test_wt_scanner_strip_bug.py`
- Modify: `skills/_lib/workflow_synthesizer.py:725`

- [x] **Step 1.1: Write the failing pytest cases for the prefix bug**

Create `tests/unit/test_wt_scanner_strip_bug.py` with the 3 cases from tasks.md §1.1 (`test_working_tree_only_modification_is_modified`, `test_staged_modification_is_staged`, `test_path_is_not_truncated_for_working_tree_only`), sharing the `_git_init` and `_track_file` helpers:

```python
# tests/unit/test_wt_scanner_strip_bug.py
import os
import subprocess
import tempfile
from pathlib import Path
from skills._lib.workflow_synthesizer import _detect_working_tree_issues


def _git_init(tmpdir):
    subprocess.run(["git", "init", "-q", str(tmpdir)], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "config", "user.name", "t"], check=True)
    (tmpdir / "init").write_text("init\n")
    subprocess.run(["git", "-C", str(tmpdir), "add", "init"], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "commit", "-q", "-m", "init"], check=True)


def _track_file(tmpdir, relative_path):
    path = tmpdir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("base\n")
    subprocess.run(["git", "-C", str(tmpdir), "add", relative_path], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "commit", "-q", "-m", f"track {relative_path}"], check=True)
    return path


def test_working_tree_only_modification_is_modified():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        f = _track_file(tmpdir, "foo.md")
        f.write_text("changed\n")
        issues = _detect_working_tree_issues(str(tmpdir))
        assert len(issues) == 1
        assert issues[0].category == "modified"
        assert issues[0].path == "foo.md"
        assert issues[0].severity == "needs_review"


def test_staged_modification_is_staged():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        f = _track_file(tmpdir, "foo.md")
        f.write_text("changed\n")
        subprocess.run(["git", "-C", str(tmpdir), "add", "foo.md"], check=True)
        issues = _detect_working_tree_issues(str(tmpdir))
        assert len(issues) == 1
        assert issues[0].category == "staged"
        assert issues[0].path == "foo.md"
        assert issues[0].severity == "needs_review"


def test_path_is_not_truncated_for_working_tree_only():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        f = _track_file(tmpdir, "improvements/proposal.md")
        f.write_text("changed\n")
        issues = _detect_working_tree_issues(str(tmpdir))
        assert len(issues) == 1
        assert issues[0].path == "improvements/proposal.md"
        assert issues[0].path[0] == "i"
```

- [x] **Step 1.2: Run the strip-bug tests to verify they fail before the fix**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py -q --tb=short
```

Expected before the fix: 1 PASS (`M ` → `staged` already works) and 2 FAIL because ` M` is misclassified as `staged` and the path slice is shifted by one character (e.g. `roposal-suggestions.md` instead of `proposal-suggestions.md`).

- [x] **Step 1.3: Apply the one-line `splitlines()` fix at line 725**

In `skills/_lib/workflow_synthesizer.py`, replace:

```python
lines = result.stdout.strip().split("\n")
```

with:

```python
lines = result.stdout.splitlines()
```

- [x] **Step 1.4: Re-run the strip-bug tests and confirm all 3 pass**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py -q --tb=short
```

Expected: 3 PASS.

- [x] **Step 1.5: Verify the fix is in place**

```bash
sed -n '725p' skills/_lib/workflow_synthesizer.py
```

Expected: line contains `.splitlines()`.

- [x] **Step 1.6: Commit the strip-bug fix**

```bash
cd /workspace/project/rdd-workflow
git add tests/unit/test_wt_scanner_strip_bug.py skills/_lib/workflow_synthesizer.py
git commit -m "fix(scanner): preserve git status --short prefix with splitlines()"
```

---

### Task 2: Fix untracked file detection

**Files:**
- Create: `tests/unit/test_wt_scanner_untracked.py`
- Modify: `skills/_lib/workflow_synthesizer.py:124` (docstring), `:519-521` (cleanup-menu summary), `:771-797` (untracked branch rewrite)

- [x] **Step 2.1: Write the failing pytest cases for untracked-file detection**

Create `tests/unit/test_wt_scanner_untracked.py` with the 4 cases from tasks.md §2.1 (`test_untracked_file_is_reported_info`, `test_large_untracked_directory_is_safe_auto_fix`, `test_hidden_directory_is_not_reported`, `test_gitignored_directory_is_not_reported`), sharing the `_git_init` helper:

```python
# tests/unit/test_wt_scanner_untracked.py
import os
import subprocess
import tempfile
from pathlib import Path
from skills._lib.workflow_synthesizer import _detect_working_tree_issues


def _git_init(tmpdir):
    subprocess.run(["git", "init", "-q", str(tmpdir)], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "config", "user.name", "t"], check=True)
    (tmpdir / "init").write_text("init\n")
    subprocess.run(["git", "-C", str(tmpdir), "add", "init"], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "commit", "-q", "-m", "init"], check=True)


def test_untracked_file_is_reported_info():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        (tmpdir / "improvements").mkdir()
        (tmpdir / "improvements" / "foo.md").write_text("new\n" * 100)
        issues = _detect_working_tree_issues(str(tmpdir))
        assert len(issues) == 1
        assert issues[0].category == "untracked_file"
        assert issues[0].path == "improvements/foo.md"
        assert issues[0].severity == "info"


def test_large_untracked_directory_is_safe_auto_fix():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        build_dir = tmpdir / "build"
        build_dir.mkdir()
        (build_dir / "big.bin").write_bytes(b"0" * (50 * 1024 * 1024))
        issues = _detect_working_tree_issues(str(tmpdir))
        assert len(issues) == 1
        assert issues[0].category == "untracked_dirs"
        assert issues[0].path == "build/"
        assert issues[0].severity == "safe_auto_fix"
        assert issues[0].fix_command == 'echo "build/" >> .gitignore'


def test_hidden_directory_is_not_reported():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        (tmpdir / ".venv").mkdir()
        (tmpdir / ".venv" / "python").write_text("bin\n")
        issues = _detect_working_tree_issues(str(tmpdir))
        assert not any(i.path.startswith(".venv") for i in issues)


def test_gitignored_directory_is_not_reported():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        _git_init(tmpdir)
        (tmpdir / ".gitignore").write_text("node_modules/\n")
        (tmpdir / "node_modules").mkdir()
        (tmpdir / "node_modules" / "pkg").write_text("pkg\n")
        issues = _detect_working_tree_issues(str(tmpdir))
        assert not any(i.path.startswith("node_modules") for i in issues)
```

- [x] **Step 2.2: Run the untracked tests to verify they fail before the fix**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_wt_scanner_untracked.py -q --tb=short
```

Expected before the fix: 1-2 PASS (large-dir and hidden-dir / gitignored-dir cases already work because `--directory` collapses and `entry.startswith(".")` filters), and failures on `test_untracked_file_is_reported_info` (file path returned as `improvements/` or omitted entirely).

- [x] **Step 2.3: Update the `WorkingTreeIssue` category docstring at line 124**

In `skills/_lib/workflow_synthesizer.py`, replace:

```python
category: ``"deleted"`` | ``"modified"`` | ``"staged"`` |
    ``"untracked_dirs"``
```

with:

```python
category: ``"deleted"`` | ``"modified"`` | ``"staged"`` |
    ``"untracked_file"`` | ``"untracked_dirs"``
```

- [x] **Step 2.4: Rewrite the untracked branch at lines 771-797**

In `skills/_lib/workflow_synthesizer.py`, replace the existing block with:

```python
try:
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, timeout=5, cwd=project_root,
    )
    if untracked.returncode == 0:
        entries = [
            entry for entry in untracked.stdout.splitlines()
            if entry and not entry.startswith(".")
        ]
        top_level_dirs = {
            entry.split("/", 1)[0] + "/"
            for entry in entries if "/" in entry
        }
        large_dirs = set()
        for directory in sorted(top_level_dirs):
            full_dir = os.path.join(project_root, directory)
            total = 0
            try:
                for dirpath, _, filenames in os.walk(full_dir):
                    for filename in filenames:
                        try:
                            total += os.path.getsize(os.path.join(dirpath, filename))
                        except OSError:
                            pass
            except OSError:
                continue
            size_mb = total / (1024 * 1024)
            if size_mb > 10:
                large_dirs.add(directory)
                issues.append(WorkingTreeIssue(
                    "untracked_dirs", directory,
                    f"大目录 ({size_mb:.0f}MB)，建议加入 .gitignore",
                    severity="safe_auto_fix",
                    auto_fixable=True,
                    fix_command=f'echo "{directory}" >> .gitignore',
                ))

        for entry in entries:
            if any(entry.startswith(directory) for directory in large_dirs):
                continue
            full = os.path.join(project_root, entry)
            if os.path.isfile(full):
                issues.append(WorkingTreeIssue(
                    "untracked_file", entry,
                    "未跟踪的新文件 (考虑 git add 或登记到 proposal-suggestions.md)",
                    severity="info",
                ))
except (subprocess.TimeoutExpired, OSError):
    pass
```

- [x] **Step 2.5: Verify the rewrite is in place**

```bash
sed -n '771,830p' skills/_lib/workflow_synthesizer.py
```

Expected: exactly one `git ls-files --others --exclude-standard` invocation (no `--directory` flag), top-level directory aggregation, and suppression of per-file issues beneath every directory in `large_dirs`.

- [x] **Step 2.6: Add the untracked count to the cleanup-menu summary at lines 519-521**

In `skills/_lib/workflow_synthesizer.py`, after the existing `staged_count = ...` line, insert:

```python
untracked_count = sum(1 for i in wt_issues if i.category == "untracked_file")
```

After the `if staged_count:` block, append:

```python
if untracked_count:
    parts.append(f"{untracked_count} untracked")
```

- [x] **Step 2.7: Verify the cleanup-menu summary update is in place**

```bash
grep -n 'untracked_count' skills/_lib/workflow_synthesizer.py
```

Expected: 2 lines containing `untracked_count`.

- [x] **Step 2.8: Re-run the untracked tests and confirm all 4 pass**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_wt_scanner_untracked.py -q --tb=short
```

Expected: 4 PASS.

- [x] **Step 2.9: Commit the untracked detection fix**

```bash
cd /workspace/project/rdd-workflow
git add tests/unit/test_wt_scanner_untracked.py skills/_lib/workflow_synthesizer.py
git commit -m "fix(scanner): report untracked files as info-only and keep large dir detection"
```

---

### Task 3: Add end-to-end regression test

**Files:**
- Create: `tests/integration/test_guide_entry_wt_issues.bats`
- Create: `tests/integration/fixtures/guide_entry_clean.json`

- [ ] **Step 3.1: Write the bats integration test (failing on missing fixture)**

Create `tests/integration/test_guide_entry_wt_issues.bats` with the 2 cases from tasks.md §3.1 (`guide_entry --json: clean tree produces identical output`, `guide_entry --json: untracked improvements file is info-only`):

```bash
#!/usr/bin/env bats
# End-to-end regression for working-tree scanner strip/omission bugs.

load ../test_helper

@test "guide_entry --json: clean tree produces identical output" {
  run bash -c 'cd "$REPO_ROOT" && SKILL_DIR=skills/guide source skills/guide/scripts/guide_entry.sh && guide_entry --json'
  [ "$status" -eq 0 ]
  # Snapshot is captured before the fix; after the fix the output must be byte-identical on a clean tree.
  expected=$(cat "$REPO_ROOT/tests/integration/fixtures/guide_entry_clean.json")
  [ "$output" = "$expected" ]
}

@test "guide_entry --json: untracked improvements file is info-only" {
  repo=$(mktemp -d)
  git init -q "$repo"
  git -C "$repo" config user.email "t@t"
  git -C "$repo" config user.name "t"
  touch "$repo/init" && git -C "$repo" add init && git -C "$repo" commit -q -m init
  mkdir -p "$repo/improvements"
  echo "new" > "$repo/improvements/foo.md"
  run bash -c "cd \"$repo\" && SKILL_DIR=skills/guide source \"$REPO_ROOT/skills/guide/scripts/guide_entry.sh\" && guide_entry --json"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c "import sys, json; d=json.load(sys.stdin); assert any(i.get('category')=='untracked_file' and i.get('severity')=='info' for i in d['wt_issues'])"
  rm -rf "$repo"
}
```

- [ ] **Step 3.2: Verify the bats file fails on the missing fixture (red)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_guide_entry_wt_issues.bats
```

Expected before the snapshot exists: 1 FAIL on the clean-tree case (fixture missing) and the untracked case may also fail until Tasks 1-2 are in place. This step only proves the test file is wired correctly and reaches the fixture read.

- [ ] **Step 3.3: Create the baseline snapshot for the clean-tree test**

```bash
cd /workspace/project/rdd-workflow
mkdir -p tests/integration/fixtures
SKILL_DIR=skills/guide bash -c 'source skills/guide/scripts/guide_entry.sh && guide_entry --json' > tests/integration/fixtures/guide_entry_clean.json
```

- [ ] **Step 3.4: Verify the fixture exists and is non-empty**

```bash
test -s /workspace/project/rdd-workflow/tests/integration/fixtures/guide_entry_clean.json && echo OK
```

Expected: prints `OK`.

- [ ] **Step 3.5: Re-run the bats integration test and confirm both cases pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_guide_entry_wt_issues.bats
```

Expected: 2 PASS.

- [ ] **Step 3.6: Commit the end-to-end regression test**

```bash
cd /workspace/project/rdd-workflow
git add tests/integration/test_guide_entry_wt_issues.bats tests/integration/fixtures/guide_entry_clean.json
git commit -m "test(integration): guide_entry wt_issues regression for strip/untracked bugs"
```

---

### Task 4: Acceptance validation

**Files:**
- Modify: none (read-only verification)

- [ ] **Step 4.1: Run the new unit tests together (strip + untracked)**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py tests/unit/test_wt_scanner_untracked.py -q --tb=short
```

Expected: 7 PASS (3 strip + 4 untracked).

- [ ] **Step 4.2: Run the existing workflow-synthesizer unit tests for regression**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_workflow_synthesizer.py -q --tb=short
```

Expected: all PASS — confirms no regression in the scanner's pre-existing categories (`deleted`, `modified`, `staged`, `untracked_dirs`).

- [ ] **Step 4.3: Run the full Python test suite**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/ -q --tb=short
```

Expected: all PASS.

- [ ] **Step 4.4: Run the bats integration suite**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/
```

Expected: all PASS — including the new `test_guide_entry_wt_issues.bats`.

- [ ] **Step 4.5: Run the npm bats smoke suite**

```bash
cd /workspace/project/rdd-workflow
npm test
```

Expected: exit 0.

- [ ] **Step 4.6: Validate the OpenSpec change in strict mode**

```bash
cd /workspace/project/rdd-workflow
openspec validate fix-wt-scanner-strip-bug-and-untracked-coverage --strict
```

Expected: PASS.

- [ ] **Step 4.7: Confirm the change status is complete**

```bash
cd /workspace/project/rdd-workflow
openspec status --change fix-wt-scanner-strip-bug-and-untracked-coverage --json | jq '.isComplete'
```

Expected: `true`.

---

### Validation matrix

| Criterion | Command | Expected result |
|-----------|---------|-----------------|
| Strip bug unit tests | `python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py -q` | 3 PASS |
| Untracked unit tests | `python3 -m pytest tests/unit/test_wt_scanner_untracked.py -q` | 4 PASS |
| Existing synthesizer regression | `python3 -m pytest tests/unit/test_workflow_synthesizer.py -q` | PASS |
| Full Python suite | `python3 -m pytest tests/ -q --tb=short` | all PASS |
| Bats integration suite | `bats tests/integration/` | all PASS |
| npm bats suite | `npm test` | exit 0 |
| OpenSpec strict validation | `openspec validate fix-wt-scanner-strip-bug-and-untracked-coverage --strict` | PASS |
| OpenSpec status complete | `openspec status --change fix-wt-scanner-strip-bug-and-untracked-coverage --json \| jq '.isComplete'` | `true` |