# fix-adr-0027-cli-optin-gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plug the CLI bypass of ADR-0027 §3 triple opt-in gate by (1) adding a public `should_auto_submit_gh_submission()` function in `_lib/issue_reporter.py`, (2) using it in both CLI paths (`rddf report-issue` and `rddf issue submit`), (3) renaming `--exit` to `--exit-code` and defaulting `--no-submit=true` so phase-exit hooks never auto-submit, and (4) updating 4 SKILL.md files to match.

**Architecture:** Extract `_should_auto_submit()` from `_lib/post_flow_analysis.py` (private) to `_lib/issue_reporter.py::should_auto_submit_gh_submission()` (public). Re-export from `post_flow_analysis.py` for backward compatibility. Both CLI paths and the script plane then share a single choke point. `--no-submit` flag inverts to default-true, preventing accidental L2 submission.

**Tech Stack:** Python 3.11+, pytest, bash

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/issue_reporter.py` | Add public `should_auto_submit_gh_submission(category) -> bool`; docstring warns this is the single choke point for opt-in |
| `_lib/post_flow_analysis.py` | Import `should_auto_submit_gh_submission` from `issue_reporter`; keep private alias `_should_auto_submit` as one-liner for backward compat |
| `_lib/cli/report_issue_cmd.py` | Rename `--exit` to `--exit-code` (default 0); default `--no-submit` to **true** (inverted); add CI downgrade check; route through `should_auto_submit_gh_submission` |
| `_lib/cli/issue_cmd.py` | In `_issue_submit`, gate the `submit_issue_via_gh` call through `should_auto_submit_gh_submission`; explicit `exit 2` on gate reject |
| `skills/gate-arch/SKILL.md` | Phase Exit: replace `--exit` with `--exit-code` |
| `skills/guide-plan/SKILL.md` | Phase Exit: replace `--exit` with `--exit-code` |
| `skills/guide-design/SKILL.md` | Phase Exit: replace `--exit` with `--exit-code` |
| `skills/guide-ship/SKILL.md` | Phase Exit: replace `--exit` with `--exit-code` |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_issue_reporter_optin.py` | **NEW** — 3 tests covering `should_auto_submit_gh_submission` triple gate |
| `tests/unit/test_report_issue_cli.py` | **NEW** — 1 test: argparse accepts `--exit-code` |
| `tests/unit/test_single_choke_point.py` | **NEW** — regression: forbid `cli/` paths from calling `submit_issue_via_gh` directly |

---

### Task 1: Extract `should_auto_submit_gh_submission` to public API

**Files:**
- Modify: `_lib/issue_reporter.py:240-249` (after `is_ci_environment`)
- Modify: `_lib/post_flow_analysis.py:342-356` (one-line re-export)
- Test: `tests/unit/test_issue_reporter_optin.py` (NEW)

- [ ] **Step 1: Write failing tests in `tests/unit/test_issue_reporter_optin.py`**

Create the file with three tests covering all three opt-in paths:

```python
"""Tests for ADR-0027 §3 triple opt-in gate — the single choke point for L2 gh submission."""
from __future__ import annotations

import os
import pytest

from issue_reporter import should_auto_submit_gh_submission  # type: ignore[import-not-found]


@pytest.fixture(autouse=True)
def _clean_optin_env(monkeypatch):
    """Ensure opt-in env vars are deterministic per test."""
    for k in ("RDDF_REPORT_ENABLED", "RDDF_REPORT_AUTO_SUBMIT", "RDDF_REPORT_SUBMIT_CATEGORIES",
              "CI", "GITHUB_ACTIONS", "JENKINS_URL"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_opt_in_disabled_writes_local_only():
    """Without RDDF_REPORT_ENABLED=yes, must NOT auto-submit — L1 only."""
    assert should_auto_submit_gh_submission("flow-bug") is False


def test_opt_in_enabled_category_not_in_list_rejects_with_false():
    """RDDF_REPORT_ENABLED=yes + category not in RDDF_REPORT_SUBMIT_CATEGORIES → False."""
    os.environ["RDDF_REPORT_ENABLED"] = "yes"
    os.environ["RDDF_REPORT_AUTO_SUBMIT"] = "yes"
    os.environ["RDDF_REPORT_SUBMIT_CATEGORIES"] = "flow-bug,phase-crash"
    assert should_auto_submit_gh_submission("manual") is False


def test_ci_environment_auto_downgrades():
    """Even with all env vars set, CI=true must downgrade to L1."""
    os.environ["RDDF_REPORT_ENABLED"] = "yes"
    os.environ["RDDF_REPORT_AUTO_SUBMIT"] = "yes"
    os.environ["RDDF_REPORT_SUBMIT_CATEGORIES"] = "flow-bug,gate-failure,phase-crash"
    os.environ["CI"] = "true"
    assert should_auto_submit_gh_submission("flow-bug") is False
```

- [ ] **Step 2: Run tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_issue_reporter_optin.py -v`
Expected: 3 errors with `ImportError: cannot import name 'should_auto_submit_gh_submission'`

- [ ] **Step 3: Add `should_auto_submit_gh_submission` to `_lib/issue_reporter.py`**

Insert after `is_ci_environment` (around line 249) and before `can_close_in_repo`:

```python
# ── 5.5 should_auto_submit_gh_submission (single choke point) ─────────────


def should_auto_submit_gh_submission(category: str) -> bool:
    """Triple-gate opt-in: master + auto_submit + per-category + not CI.

    **ADR-0027 §3 single choke point.** Every path that ultimately calls
    ``gh issue create`` MUST gate through this function. Do NOT reimplement
    the three checks inline; add new gates here instead.

    Returns True only when ALL of the following hold:
      1. ``RDDF_REPORT_ENABLED`` ∈ {yes, true, 1}
      2. ``RDDF_REPORT_AUTO_SUBMIT`` ∈ {yes, true, 1}
      3. category ∈ ``RDDF_REPORT_SUBMIT_CATEGORIES`` (comma-separated)
      4. NOT in CI environment (CI/GITHUB_ACTIONS/JENKINS_URL/etc.)
    """
    if os.environ.get("RDDF_REPORT_ENABLED", "no").lower() not in ("yes", "true", "1"):
        return False
    if os.environ.get("RDDF_REPORT_AUTO_SUBMIT", "no").lower() not in ("yes", "true", "1"):
        return False
    if is_ci_environment():
        return False
    categories_raw = os.environ.get("RDDF_REPORT_SUBMIT_CATEGORIES", "")
    if categories_raw:
        allowed = {c.strip() for c in categories_raw.split(",") if c.strip()}
        if category not in allowed:
            return False
    return True
```

- [ ] **Step 4: Update `_lib/post_flow_analysis.py` to import from new location**

Replace the entire body of `_should_auto_submit` (lines 342-356) with:

```python
def _should_auto_submit(category: str) -> bool:
    """Three-gate opt-in: master + auto_submit + per-category + not CI.

    Thin re-export of :func:`issue_reporter.should_auto_submit_gh_submission`
    (single choke point per ADR-0027 §3). Kept as a private alias for backward
    compatibility with the existing call site at line 327.
    """
    from issue_reporter import should_auto_submit_gh_submission
    return should_auto_submit_gh_submission(category)
```

- [ ] **Step 5: Run tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_issue_reporter_optin.py -v`
Expected: 3 passed.

- [ ] **Step 6: Verify no regression in post_flow_analysis**

Run: `python3 -m pytest tests/unit/test_post_flow_analysis.py -v 2>&1 | tail -20`
Expected: existing tests pass (the import was already used at line 327).

- [ ] **Step 7: Defer commit**

No commit yet — continue to next task. Final commit happens in `guide-ship` Phase 2.7.

---

### Task 2: Update `rddf report-issue` argparse (--exit-code + default --no-submit=true)

**Files:**
- Modify: `_lib/cli/report_issue_cmd.py:29-62` (entire `cmd_report_issue` function)
- Test: `tests/unit/test_report_issue_cli.py` (NEW)

- [ ] **Step 1: Write failing test in `tests/unit/test_report_issue_cli.py`**

```python
"""Tests for rddf report-issue CLI argparse + behavior."""
from __future__ import annotations

import os
import sys

import pytest


def test_exit_code_flag_accepted(monkeypatch):
    """argparse must accept --exit-code (not the legacy --exit)."""
    monkeypatch.setattr(sys, "argv", ["rddf", "report-issue", "--exit-code", "137", "desc"])
    # Direct invocation: must not raise SystemExit(2) from argparse
    from skills._lib.cli.report_issue_cmd import cmd_report_issue  # type: ignore[import-not-found]
    monkeypatch.setenv("RDDF_PROJECT_ROOT", "/tmp/nonexistent-root-for-test")
    # argparse may exit 0 (write local file) or 2 (argparse error) — anything but `argparse error`
    import argparse
    try:
        result = cmd_report_issue(["--exit-code", "137", "desc"])
        assert result == 0
    except SystemExit as e:
        assert e.code != 2, f"argparse rejected --exit-code: code={e.code}"
```

- [ ] **Step 2: Run test to verify it fails (RED)**

Run: `python3 -m pytest tests/unit/test_report_issue_cli.py -v`
Expected: FAIL — argparse error on `--exit-code 137 desc` (no such argument).

- [ ] **Step 3: Update `_lib/cli/report_issue_cmd.py`**

Replace the entire `cmd_report_issue` function (lines 29-62) with:

```python
def cmd_report_issue(args: list[str]) -> int:
    """Submit a manual issue report (Agent plane, bypasses classifier).

    By default, **never auto-submits to GitHub** (--no-submit is the default;
    pass --submit to opt in). Phase-exit hooks in SKILL.md rely on this
    default to avoid accidental L2 submission when AI agents invoke this
    command.
    """
    parser = argparse.ArgumentParser(prog="rddf report-issue")
    parser.add_argument("description", help="One-line description of the issue")
    parser.add_argument(
        "--category", default="manual",
        choices=["flow-bug", "gate-failure", "phase-crash", "manual"],
        help="Issue category (default: manual)",
    )
    parser.add_argument("--phase", default="", help="Originating phase (optional metadata)")
    parser.add_argument(
        "--exit-code", type=int, default=0,
        help="Exit code of the originating phase (metadata only, default 0)",
    )
    parser.add_argument(
        "--no-submit", action="store_true", default=True,
        help="[DEFAULT] Write local file only, skip gh submission",
    )
    parser.add_argument(
        "--submit", dest="no_submit", action="store_false",
        help="Opt in to gh submission (overrides --no-submit default). "
             "Honors triple opt-in gate (RDDF_REPORT_ENABLED + AUTO_SUBMIT + category).",
    )
    parsed = parser.parse_args(args)

    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    payload = {
        "description": parsed.description,
        "stack": [],
        "metadata": {
            "phase": parsed.phase,
            "exit_code": parsed.exit_code,
        } if parsed.phase or parsed.exit_code else {},
    }
    result = detect_issue(parsed.category, payload)
    file_path = write_issue_file(result, project_root=project_root)
    print(f"✅ wrote {file_path}")

    if not parsed.no_submit:
        from issue_reporter import should_auto_submit_gh_submission, is_ci_environment
        if is_ci_environment():
            print("ℹ️  local-only (CI auto-downgrade, --submit ignored)")
            return 0
        if not should_auto_submit_gh_submission(parsed.category):
            print("❌ gh submit rejected: triple opt-in not satisfied "
                  "(need RDDF_REPORT_ENABLED=yes AND RDDF_REPORT_AUTO_SUBMIT=yes "
                  "AND category ∈ RDDF_REPORT_SUBMIT_CATEGORIES AND NOT CI).")
            return 2
        gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
        submit = submit_issue_via_gh(file_path, parsed.category, gh_repo)
        if submit.success:
            print(f"✅ submitted: {submit.submitted_url}")
        else:
            print(f"ℹ️  local-only (gh submit skipped): {submit.error}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes (GREEN)**

Run: `python3 -m pytest tests/unit/test_report_issue_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Verify behavior manually**

Run: `cd $WT_PATH && python3 -c "from skills._lib.cli.report_issue_cmd import cmd_report_issue; cmd_report_issue(['--exit-code', '137', 'phase-crash demo'])"` (use a tmpdir as RDDF_PROJECT_ROOT)
Expected: writes local issue file, exits 0, prints `✅ wrote /path/to/file.md`. No `gh` call (default --no-submit).

- [ ] **Step 6: Defer commit**

---

### Task 3: Gate `rddf issue submit` through triple opt-in

**Files:**
- Modify: `_lib/cli/issue_cmd.py:50-70` (entire `_issue_submit` function)

- [ ] **Step 1: Replace `_issue_submit` with gated version**

Replace the body of `_issue_submit` (lines 50-70) with:

```python
def _issue_submit(args: list[str]) -> int:
    if not args:
        print("Usage: rddf issue submit <file>")
        return 2
    file_path = Path(args[0])
    if not file_path.is_file():
        print(f"❌ file not found: {file_path}")
        return 1

    category = _extract_category_from_filename(file_path.name)
    if not category:
        print(f"⚠️  cannot infer category from filename {file_path.name!r}; using 'manual'")
        category = "manual"

    from issue_reporter import should_auto_submit_gh_submission, is_ci_environment
    if is_ci_environment():
        print("ℹ️  local-only (CI auto-downgrade; --submit ignored).")
        return 0
    if not should_auto_submit_gh_submission(category):
        print("❌ gh submit rejected: triple opt-in not satisfied "
              "(set RDDF_REPORT_ENABLED=yes AND RDDF_REPORT_AUTO_SUBMIT=yes "
              "AND ensure category is in RDDF_REPORT_SUBMIT_CATEGORIES).")
        return 2

    gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
    result = submit_issue_via_gh(file_path, category, gh_repo)
    if result.success:
        print(f"✅ submitted: {result.submitted_url}")
        return 0
    print(f"❌ submit failed: {result.error}")
    return 1
```

- [ ] **Step 2: Manual behavior check**

Run: `cd $WT_PATH && python3 -c "from skills._lib.cli.issue_cmd import _issue_submit; import sys; sys.exit(_issue_submit(['/tmp/nonexistent']))"`
Expected: exits with code 1 (file not found — pre-gate check).

Run: `echo '# stub' > /tmp/test-issue.md && cd $WT_PATH && python3 -c "from skills._lib.cli.issue_cmd import _issue_submit; import sys; sys.exit(_issue_submit(['/tmp/test-issue.md']))"`
Expected: exits with code 2 (gate rejected — no opt-in env vars).

- [ ] **Step 3: Defer commit**

---

### Task 4: Update 4 SKILL.md Phase Exit sections to use `--exit-code`

**Files:**
- Modify: `skills/gate-arch/SKILL.md` (Phase Exit section, find `--exit`)
- Modify: `skills/guide-plan/SKILL.md` (Phase Exit section)
- Modify: `skills/guide-design/SKILL.md` (Phase Exit section)
- Modify: `skills/guide-ship/SKILL.md` (Phase Exit section)

- [ ] **Step 1: Locate `--exit` references in each file**

Run: `grep -rn "\\-\\-exit " skills/{gate-arch,guide-plan,guide-design,guide-ship}/SKILL.md`
Expected: ~3-6 hits per file (the Phase Exit section repeats the flag in scenarios/examples).

- [ ] **Step 2: Replace each occurrence with `--exit-code`**

For each file, perform a targeted replacement:
- `--exit <code>` → `--exit-code <code>`
- `--exit-code 137` (etc., as used in scenario examples) → keep as is
- Leave `--exit 1` style bash-flag arguments (where `--exit` is followed by digits in script invocations, NOT Python argparse) untouched — verify each case.

Pattern: only replace `--exit ` (with trailing space + arg) where the next token is a digit. Use `Edit` tool with surrounding context for each replacement.

- [ ] **Step 3: Verify zero `--exit <digit>` remains in argparse contexts**

Run: `grep -rn "rddf report-issue --exit [0-9]" skills/`
Expected: no matches.

- [ ] **Step 4: Defer commit**

---

### Task 5: Add single-choke-point regression test

**Files:**
- Create: `tests/unit/test_single_choke_point.py`

- [ ] **Step 1: Write the regression test**

```python
"""Regression: forbid CLI paths from calling submit_issue_via_gh directly.

Per ADR-0027 §3, all L2 gh submission paths MUST go through
``should_auto_submit_gh_submission`` in ``_lib/issue_reporter.py``. Any
``_lib/cli/`` module that calls ``submit_issue_via_gh`` directly is a bypass
of the triple opt-in gate.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_CLI_DIR = Path(__file__).resolve().parent.parent.parent / "_lib" / "cli"

# Pattern: from issue_reporter import ... submit_issue_via_gh ...
_BYPASS_PATTERN = re.compile(
    r"from\s+issue_reporter\s+import[^\n]*submit_issue_via_gh",
    re.MULTILINE,
)


@pytest.mark.parametrize("cli_file", sorted(_CLI_DIR.glob("*.py")))
def test_no_direct_submit_issue_via_gh_import_in_cli(cli_file: Path) -> None:
    """Every CLI module must import should_auto_submit_gh_submission, NOT submit_issue_via_gh directly."""
    if cli_file.name == "__init__.py":
        pytest.skip("package init")
    text = cli_file.read_text(encoding="utf-8")
    matches = _BYPASS_PATTERN.findall(text)
    assert not matches, (
        f"{cli_file.name} bypasses triple opt-in gate: directly imports submit_issue_via_gh. "
        f"Use should_auto_submit_gh_submission() from issue_reporter instead.\n"
        f"Found: {matches}"
    )
```

- [ ] **Step 2: Run test (must pass on initial run)**

Run: `python3 -m pytest tests/unit/test_single_choke_point.py -v`
Expected: PASS for all files (Tasks 2-3 already use `should_auto_submit_gh_submission`).

- [ ] **Step 3: Defer commit**

---

### Task 6: Run full unit test suite

**Files:** (no new files)

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all pass OR same failure set as `tests/KNOWN_FAILURES.txt` (no NEW failures).

- [ ] **Step 2: If new failures appear, fix them**

For each new failure NOT in baseline: investigate root cause, fix minimally, re-run.

- [ ] **Step 3: Defer commit (final commit is at archive phase)**

---

### Task 7: Update `openspec/changes/fix-adr-0027-cli-optin-gate/tasks.md` checkboxes

**Files:**
- Modify: `openspec/changes/fix-adr-0027-cli-optin-gate/tasks.md` (in master repo, NOT worktree)

> **Note**: `tasks.md` is in the master repo at `openspec/changes/<name>/tasks.md`. After all tasks complete, mark them `[x]`. The worktree's `tasks.md` may be identical (since the change artifacts were already committed at HEAD).

- [ ] **Step 1: Mark each completed task as `[x]` in `tasks.md`**

Edit `openspec/changes/fix-adr-0027-cli-optin-gate/tasks.md`:

- [ ] Read `proposal.md` fully...
- [ ] Identify all `**不**` items...
- [ ] Write failing test(s)...
- [ ] Verify tests fail (red)...
- [ ] Task 1: 把 --exit <code> 改为 --exit-code <code>...
- [ ] Task 2: 增加 --no-submit...
- [ ] Task 3: (no items specified)
- [ ] Verify all new tests pass (green)
- [ ] Run full unit test suite...
- [ ] Run integration tests...
- [ ] Verify no regressions...
- [ ] Update relevant docstrings/inline comments...
- [ ] Update CHANGELOG if user-facing behavior changed
- [ ] Verify `openspec validate <change>` passes
- [ ] Commit changes with conventional commit message

- [ ] **Step 2: Defer commit (final commit is at archive phase)**

---

### Task 8: Stage changes for archive

**Files:**
- Modify: worktree files (production code + tests + SKILL.md updates)

- [ ] **Step 1: Verify all changes in worktree**

Run: `cd $WT_PATH && git status --short`
Expected: list of modified + new files (no accidental edits).

- [ ] **Step 2: Defer commit**

The worktree commit happens in `guide-ship` Phase 2.7 — one conventional commit containing all changes.

---

## Acceptance Verification Checklist

After all tasks complete, verify:

- [ ] `python3 -m pytest tests/unit/ -q --tb=short` — all pass (or known-failures only)
- [ ] `python3 -c "from skills._lib.cli.report_issue_cmd import cmd_report_issue; cmd_report_issue(['--exit-code', '137', 'phase-crash demo'])"` exits 0 (default `--no-submit`)
- [ ] `python3 -c "from skills._lib.cli.issue_cmd import _issue_submit; import sys; sys.exit(_issue_submit(['/tmp/stub.md']))"` exits 2 (gate rejected)
- [ ] `grep -rn "rddf report-issue --exit [0-9]" skills/` returns empty
- [ ] `python3 -m pytest tests/unit/test_issue_reporter_optin.py tests/unit/test_report_issue_cli.py tests/unit/test_single_choke_point.py -v` — all 5 tests pass

## Out of Scope (DO NOT IMPLEMENT)

Per `proposal.md` "**不**" list:

- ❌ New sanitizer rules (`_lib/loop/sanitizer.py:69-71` already has home/Users/sensitive_names)
- ❌ Changes to L1 local issue file path/format (handled by `fix-adr-0027-issue-file-frontmatter`)
- ❌ Changes to `gh` invocation in `submit_issue_via_gh` (already env-var pattern, Oracle C1 compliant)
- ❌ New external dependencies
- ❌ Refactor of `_should_auto_submit` *body* (only the location moves; logic identical)