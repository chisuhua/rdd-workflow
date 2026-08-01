## 1. Fix working-tree prefix truncation bug

- [x] 1.1 Create the failing unit test `tests/unit/test_wt_scanner_strip_bug.py` covering the three strip-bug cases.

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

    Verification: `python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py -q --tb=short` (expected before the fix: 1 PASS and 2 FAIL because ` M` is misclassified/truncated; expected after task 1.2: 3 PASS)

- [x] 1.2 Apply the one-line fix in `skills/_lib/workflow_synthesizer.py:725`.

    Replace:

    ```python
    lines = result.stdout.strip().split("\n")
    ```

    with:

    ```python
    lines = result.stdout.splitlines()
    ```

    Verification: `sed -n '725p' skills/_lib/workflow_synthesizer.py` outputs a line containing `.splitlines()`

- [x] 1.3 Run the strip-bug tests again and confirm all three pass.

    Verification: `python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py -q --tb=short` (expected: 3 PASS)

- [x] 1.4 Commit the strip-bug fix.

    ```bash
    git add tests/unit/test_wt_scanner_strip_bug.py skills/_lib/workflow_synthesizer.py
    git commit -m "fix(scanner): preserve git status --short prefix with splitlines()"
    ```

## 2. Fix untracked file detection

- [x] 2.1 Create the failing unit test `tests/unit/test_wt_scanner_untracked.py` covering the four untracked cases.

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

    Verification: `python3 -m pytest tests/unit/test_wt_scanner_untracked.py -q --tb=short` (expected: 1-2 PASS, failures on untracked_file detection)

- [x] 2.2 Update the `WorkingTreeIssue` category docstring in `skills/_lib/workflow_synthesizer.py:124`.

    Replace:

    ```python
    category: ``"deleted"`` | ``"modified"`` | ``"staged"`` |
        ``"untracked_dirs"``
    ```

    with:

    ```python
    category: ``"deleted"`` | ``"modified"`` | ``"staged"`` |
        ``"untracked_file"`` | ``"untracked_dirs"``
    ```

    Verification: `grep -n '"untracked_file"' skills/_lib/workflow_synthesizer.py` returns the docstring line

- [x] 2.3 Rewrite the untracked block in `skills/_lib/workflow_synthesizer.py:771-797` to report files and keep large-directory behavior.

    Replace the block with:

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

    Verification: `sed -n '771,830p' skills/_lib/workflow_synthesizer.py` contains one `git ls-files --others --exclude-standard` call (no `--directory`), top-level directory aggregation, and suppression of per-file issues beneath every directory in `large_dirs`.

- [x] 2.4 Add an untracked count to the cleanup-menu summary in `skills/_lib/workflow_synthesizer.py:519-521`.

    After the existing `staged_count = ...` line, insert:

    ```python
    untracked_count = sum(1 for i in wt_issues if i.category == "untracked_file")
    ```

    and after the `if staged_count:` block, append:

    ```python
    if untracked_count:
        parts.append(f"{untracked_count} untracked")
    ```

    Verification: `grep -n 'untracked_count' skills/_lib/workflow_synthesizer.py` returns two lines

- [x] 2.5 Run the untracked tests again and confirm all four pass.

    Verification: `python3 -m pytest tests/unit/test_wt_scanner_untracked.py -q --tb=short` (expected: 4 PASS)

- [x] 2.6 Commit the untracked detection fix.

    ```bash
    git add tests/unit/test_wt_scanner_untracked.py skills/_lib/workflow_synthesizer.py
    git commit -m "fix(scanner): report untracked files as info-only and keep large dir detection"
    ```

## 3. Add end-to-end regression test

- [x] 3.1 Create the failing integration test `tests/integration/test_guide_entry_wt_issues.bats`.

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

    Verification: `bats tests/integration/test_guide_entry_wt_issues.bats` (expected: 1 FAIL on clean-tree snapshot until fixture is created, then both pass after fix)

- [x] 3.2 Create the baseline snapshot for the clean-tree test.

    ```bash
    mkdir -p tests/integration/fixtures
    SKILL_DIR=skills/guide bash -c 'source skills/guide/scripts/guide_entry.sh && guide_entry --json' > tests/integration/fixtures/guide_entry_clean.json
    ```

    Verification: `test -f tests/integration/fixtures/guide_entry_clean.json` is true and the file is non-empty

- [x] 3.3 Run the integration test again and confirm both cases pass.

    Verification: `bats tests/integration/test_guide_entry_wt_issues.bats` (expected: 2 PASS)

- [x] 3.4 Commit the end-to-end regression test.

    ```bash
    git add tests/integration/test_guide_entry_wt_issues.bats tests/integration/fixtures/guide_entry_clean.json
    git commit -m "test(integration): guide_entry wt_issues regression for strip/untracked bugs"
    ```

## 4. Acceptance validation

- [x] 4.1 Run the new unit tests together.

    Verification: `python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py tests/unit/test_wt_scanner_untracked.py -q --tb=short` (expected: 7 PASS)

- [x] 4.2 Run the existing workflow synthesizer unit tests to confirm no regressions.

    Verification: `python3 -m pytest tests/unit/test_workflow_synthesizer.py -q --tb=short` (expected: PASS)

- [ ] 4.3 Run the full Python test suite.

    Verification: `python3 -m pytest tests/ -q --tb=short` (expected: all PASS)

- [ ] 4.4 Run the bats integration suite.

    Verification: `bats tests/integration/` (expected: all PASS)

- [ ] 4.5 Run the npm bats smoke suite.

    Verification: `npm test` (expected: exit 0)

- [ ] 4.6 Validate the OpenSpec change in strict mode.

    Verification: `openspec validate fix-wt-scanner-strip-bug-and-untracked-coverage --strict` (expected: PASS)

- [ ] 4.7 Confirm the change status is complete.

    Verification: `openspec status --change fix-wt-scanner-strip-bug-and-untracked-coverage --json | jq '.isComplete'` (expected: `true`)

### Validation matrix

| Criterion | Command | Expected result |
|-----------|---------|---------------|
| Strip bug unit tests | `python3 -m pytest tests/unit/test_wt_scanner_strip_bug.py -q` | 3 PASS |
| Untracked unit tests | `python3 -m pytest tests/unit/test_wt_scanner_untracked.py -q` | 4 PASS |
| Existing synthesizer regression | `python3 -m pytest tests/unit/test_workflow_synthesizer.py -q` | PASS |
| Full Python suite | `python3 -m pytest tests/ -q --tb=short` | all PASS |
| Bats integration suite | `bats tests/integration/` | all PASS |
| npm bats suite | `npm test` | exit 0 |
| OpenSpec strict validation | `openspec validate fix-wt-scanner-strip-bug-and-untracked-coverage --strict` | PASS |
| OpenSpec status complete | `openspec status --change fix-wt-scanner-strip-bug-and-untracked-coverage --json \| jq '.isComplete'` | `true` |
