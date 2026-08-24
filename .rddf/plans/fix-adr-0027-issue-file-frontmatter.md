# fix-adr-0027-issue-file-frontmatter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Add the 6 missing Reporter fields (python_version/git_version/os_platform/project_hash/rddf_session_id/skill_invoked) to `_render_issue_body` per ADR-0027 §4. Currently L1 issue files are 16 lines; target is the full frontmatter + Reporter section + Stack trace + Repro.

**Architecture:** Extend `IssueResult` dataclass with new fields (skill_invoked, rddf_session_id, project_root, stack_trace). Add a private helper `_collect_reporter_metadata()` that probes `sys.version`, `git --version`, `platform.platform()`, computes `sha256(project_root)[:8]`, reads `RDDF_SESSION_ID`. Wire `skill_invoked` through `detect_issue()`'s payload. Update `_render_issue_body` to emit YAML frontmatter (extended), Reporter section, Stack trace (already there), Repro section.

**Tech Stack:** Python 3.11+, pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/issue_reporter.py` | Extend `IssueResult`; add `_collect_reporter_metadata()`; rewrite `_render_issue_body()` |
| `_lib/post_flow_analysis.py` | Pass `skill_invoked="post-flow-analysis"` to `detect_issue` |
| `_lib/cli/report_issue_cmd.py` | Pass `skill_invoked="manual"` (default) and forward `RDDF_SESSION_ID` if set |
| `_lib/cli/issue_cmd.py` | Pass `skill_invoked="manual"` |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_issue_reporter_frontmatter.py` | **NEW** — 4 unit tests: full reporter fields present, stack sanitized, project_hash deterministic, rddf_session_id None fallback |

---

### Task 1: Extend `IssueResult` + add `_collect_reporter_metadata()`

**Files:**
- Modify: `_lib/issue_reporter.py:47-56` (IssueResult dataclass)
- Modify: `_lib/issue_reporter.py:69-96` (detect_issue)
- Add to `_lib/issue_reporter.py`: `_collect_reporter_metadata()` helper

- [ ] **Step 1: Write failing tests in `tests/unit/test_issue_reporter_frontmatter.py`**

```python
"""Tests for ADR-0027 §4 issue file frontmatter completeness."""
from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest


def test_all_reporter_fields_present(tmp_path: Path, monkeypatch) -> None:
    """IssueResult + _render_issue_body must populate all 6 ADR-0027 §4 Reporter fields."""
    from issue_reporter import detect_issue, write_issue_file, IssueResult  # type: ignore[import-not-found]

    monkeypatch.delenv("RDDF_SESSION_ID", raising=False)
    payload = {
        "description": "test issue",
        "stack": ["frame1", "frame2"],
        "metadata": {"phase": "guide-ship", "exit_code": 137},
    }
    result = detect_issue("phase-crash", payload)
    # Set skill_invoked manually (not yet wired in detect_issue)
    result.skill_invoked = "post-flow-analysis"
    result.project_root = str(tmp_path)

    file_path = write_issue_file(result, str(tmp_path))
    text = file_path.read_text(encoding="utf-8")

    # Required frontmatter fields
    for field in ("category", "detected_at", "rdd_workflow_version", "dedup_hash",
                  "submitted", "submitted_url", "exit_code"):
        assert f"{field}:" in text, f"missing frontmatter field: {field}\n{text}"

    # Required Reporter fields (ADR §4)
    for field in ("python_version", "git_version", "os_platform",
                  "project_hash", "rddf_session_id", "skill_invoked"):
        assert f"{field}:" in text, f"missing Reporter field: {field}\n{text}"

    # Sections present
    assert "## Description" in text
    assert "## Reporter" in text
    assert "## Stack trace" in text
    assert "## Repro" in text


def test_stack_trace_sanitized_no_home_path(tmp_path: Path, monkeypatch) -> None:
    """Stack trace must be sanitized — no /home/<user>/ leaks."""
    from issue_reporter import detect_issue, write_issue_file  # type: ignore[import-not-found]

    home_leak = f"/home/{os.environ.get('USER', 'someone')}/private/path"
    payload = {
        "description": "issue with leaked path",
        "stack": [f"Traceback at {home_leak}:42"],
    }
    result = detect_issue("flow-bug", payload)
    result.skill_invoked = "manual"
    result.project_root = str(tmp_path)
    file_path = write_issue_file(result, str(tmp_path))
    text = file_path.read_text(encoding="utf-8")
    assert "/home/" not in text, f"home path leaked: {text}"


def test_rddf_session_id_none_when_env_unset(tmp_path: Path, monkeypatch) -> None:
    """Without RDDF_SESSION_ID env, must emit 'none' in frontmatter."""
    monkeypatch.delenv("RDDF_SESSION_ID", raising=False)
    from issue_reporter import detect_issue, write_issue_file  # type: ignore[import-not-found]
    result = detect_issue("phase-crash", {"description": "x"})
    result.skill_invoked = "manual"
    result.project_root = str(tmp_path)
    file_path = write_issue_file(result, str(tmp_path))
    text = file_path.read_text(encoding="utf-8")
    # The rddf_session_id line must appear (either with value or with `none`)
    assert "rddf_session_id:" in text
    # When unset, the value should be `none`
    assert 'rddf_session_id: "none"' in text or "rddf_session_id: none" in text


def test_project_hash_deterministic_for_same_project_root(tmp_path: Path) -> None:
    """project_hash = sha256(project_root)[:8] — stable for same root."""
    from issue_reporter import detect_issue, write_issue_file, IssueResult  # type: ignore[import-not-found]
    expected = hashlib.sha256(str(tmp_path).encode()).hexdigest()[:8]

    result1 = detect_issue("flow-bug", {"description": "first"})
    result1.skill_invoked = "manual"
    result1.project_root = str(tmp_path)
    file_path1 = write_issue_file(result1, str(tmp_path))

    result2 = detect_issue("flow-bug", {"description": "second"})
    result2.skill_invoked = "manual"
    result2.project_root = str(tmp_path)
    file_path2 = write_issue_file(result2, str(tmp_path))

    text1 = file_path1.read_text(encoding="utf-8")
    text2 = file_path2.read_text(encoding="utf-8")
    assert f'project_hash: "{expected}"' in text1
    assert f'project_hash: "{expected}"' in text2
```

- [ ] **Step 2: Run tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_issue_reporter_frontmatter.py -v`
Expected: 4 failures (fields/sections missing).

- [ ] **Step 3: Extend `IssueResult` dataclass**

In `_lib/issue_reporter.py`, replace the `IssueResult` dataclass (lines 47-56) with:

```python
@dataclass
class IssueResult:
    """Outcome of :func:`detect_issue`, ready for :func:`write_issue_file`."""

    category: str
    sanitized_description: str
    sanitized_stack: List[str] = field(default_factory=list)
    had_sensitive_data: bool = False
    dedup_hash: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rdd_workflow_version: str = "2.0.9"
    # ADR-0027 §4 Reporter fields (filled by detect_issue via _collect_reporter_metadata)
    skill_invoked: str = "manual"
    project_root: str = ""
    python_version: str = ""
    git_version: str = ""
    os_platform: str = ""
    project_hash: str = ""
    rddf_session_id: str = "none"
    # Caller-provided metadata (e.g., {"phase": "guide-ship", "exit_code": 137})
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 4: Add `_collect_reporter_metadata()` helper**

Insert after the `IssueResult` dataclass (before `detect_issue`):

```python
def _collect_reporter_metadata(project_root: str = "") -> dict:
    """Probe runtime environment for ADR-0027 §4 Reporter section.

    Returns a dict with keys: python_version, git_version, os_platform,
    project_hash, rddf_session_id. All values are strings; project_hash
    is the sha256 of the absolute project_root path, truncated to 8 chars.

    Each probe is best-effort: failures return empty string or "unknown"
    so a minimal environment still produces a valid Reporter section.
    """
    py_ver = sys.version.split()[0] if sys.version else ""
    try:
        git_ver = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=3
        ).stdout.strip() or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        git_ver = "unknown"
    os_plat = platform.platform() or "unknown"
    proj_hash = ""
    if project_root:
        proj_hash = hashlib.sha256(str(project_root).encode("utf-8")).hexdigest()[:8]
    rddf_sid = os.environ.get("RDDF_SESSION_ID", "none") or "none"
    return {
        "python_version": py_ver,
        "git_version": git_ver,
        "os_platform": os_plat,
        "project_hash": proj_hash,
        "rddf_session_id": rddf_sid,
    }
```

Add the imports at the top of the file (after line 39 `from issue_dedup`):

```python
import hashlib
import platform
```

- [ ] **Step 5: Update `detect_issue` to populate Reporter fields**

Replace the body of `detect_issue` (lines 69-96) with:

```python
def detect_issue(category: str, payload: dict) -> IssueResult:
    """Sanitize a payload dict and produce a ready-to-write IssueResult.

    Args:
        category: One of the ADR-0027 §1 categories (flow-bug, gate-failure, …).
        payload: ``{"description": str, "stack": list[str], "metadata": dict (optional),
                    "skill_invoked": str (optional), "project_root": str (optional)}``.
    """
    description = payload.get("description", "")
    stack = payload.get("stack", []) or []
    skill_invoked = payload.get("skill_invoked", "manual")
    project_root = payload.get("project_root", "")

    desc_result = sanitize(description)
    sanitized_stack = [sanitize(frame).sanitized_text for frame in stack[:5]]

    dedup_hash = compute_dedup_hash(category, description, stack[:3])

    reporter = _collect_reporter_metadata(project_root)

    return IssueResult(
        category=category,
        sanitized_description=desc_result.sanitized_text,
        sanitized_stack=sanitized_stack,
        had_sensitive_data=desc_result.had_sensitive_data or any(
            sanitize(frame).had_sensitive_data for frame in stack[:5]
        ),
        dedup_hash=dedup_hash,
        skill_invoked=skill_invoked,
        project_root=project_root,
        python_version=reporter["python_version"],
        git_version=reporter["git_version"],
        os_platform=reporter["os_platform"],
        project_hash=reporter["project_hash"],
        rddf_session_id=reporter["rddf_session_id"],
        metadata=payload.get("metadata") or {},
    )
```

- [ ] **Step 6: Rewrite `_render_issue_body` with full frontmatter + Reporter + Repro sections**

Replace `_render_issue_body` (lines 117-144) with:

```python
def _render_issue_body(result: IssueResult) -> str:
    """Render the full Markdown body per ADR-0027 §4.

    Sections:
      1. YAML frontmatter (14 fields: 6 core + 6 Reporter + 2 metadata)
      2. ## Description
      3. ## Reporter (6 fields: env fingerprint)
      4. ## Stack trace / details (if any)
      5. ## Repro (reproduction hint + invocation metadata)
      6. ## Reporter commit (legacy single-line version marker)
    """
    frontmatter = {
        "category": result.category,
        "detected_at": result.detected_at,
        "rdd_workflow_version": result.rdd_workflow_version,
        "dedup_hash": result.dedup_hash,
        "submitted": False,
        "submitted_url": None,
        "skill_invoked": result.skill_invoked,
        "rddf_session_id": result.rddf_session_id,
        "project_hash": result.project_hash,
        "python_version": result.python_version,
        "git_version": result.git_version,
        "os_platform": result.os_platform,
    }
    # Caller-provided metadata (e.g., exit_code, phase) merged into frontmatter
    for k, v in (result.metadata or {}).items():
        if k not in frontmatter:
            frontmatter[k] = v

    fm_lines = ["---"]
    for k, v in frontmatter.items():
        if v is None:
            fm_lines.append(f"{k}: null")
        elif isinstance(v, str):
            fm_lines.append(f'{k}: "{v}"')
        else:
            fm_lines.append(f"{k}: {json.dumps(v)}")
    fm_lines.append("---\n")

    body = "\n".join(fm_lines)
    body += f"\n## Description\n\n{result.sanitized_description}\n"

    body += "\n## Reporter\n\n"
    body += f"- python_version: `{result.python_version}`\n"
    body += f"- git_version: `{result.git_version}`\n"
    body += f"- os_platform: `{result.os_platform}`\n"
    body += f"- project_hash: `{result.project_hash}`\n"
    body += f"- rddf_session_id: `{result.rddf_session_id}`\n"
    body += f"- skill_invoked: `{result.skill_invoked}`\n"

    if result.sanitized_stack:
        body += "\n## Stack trace / details\n\n"
        for frame in result.sanitized_stack:
            body += f"- `{frame}`\n"

    body += "\n## Repro\n\n"
    body += f"Skill: `{result.skill_invoked}` · "
    body += f"Session: `{result.rddf_session_id}`\n"
    if result.project_root:
        body += f"Project: `{result.project_root}`\n"
    if result.metadata:
        for k, v in result.metadata.items():
            body += f"- {k}: `{v}`\n"

    body += "\n## Reporter commit\n\n"
    body += f"rdd-workflow v{result.rdd_workflow_version}\n"
    return body
```

- [ ] **Step 7: Run tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_issue_reporter_frontmatter.py -v`
Expected: 4 passed.

- [ ] **Step 8: Defer commit**

---

### Task 2: Wire `skill_invoked` + `project_root` through callers

**Files:**
- Modify: `_lib/post_flow_analysis.py` (call sites of `detect_issue`)
- Modify: `_lib/cli/report_issue_cmd.py` (call site of `detect_issue`)
- Modify: `_lib/cli/issue_cmd.py` (if any detect_issue call)

- [ ] **Step 1: Update `_lib/post_flow_analysis.py`**

Find each call to `detect_issue(` and ensure `payload` includes `"skill_invoked": "post-flow-analysis"` and `"project_root": <absolute project root>`. If you can't find a clean call site, add a thin helper.

Concretely: search `_lib/post_flow_analysis.py` for `detect_issue(` and modify each call to add the new keys. The most common call site is in `report_classification` or `analyze_and_report`.

- [ ] **Step 2: Update `_lib/cli/report_issue_cmd.py`**

In `cmd_report_issue` (around line 29), modify the `payload` dict to include:
```python
payload = {
    "description":,
    "stack": [],
    "skill_invoked": "manual",
    "project_root": project_root,
    "metadata": {...},
}
```

- [ ] **Step 3: Run regression tests**

Run: `python3 -m pytest tests/unit/test_cli_reporter.py tests/unit/test_issue_reporter_optin.py tests/unit/test_single_choke_point.py tests/unit/test_issue_reporter_frontmatter.py -v 2>&1 | tail -15`
Expected: all pass.

- [ ] **Step 4: Defer commit**

---

### Task 3: Run full unit test suite

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all pass OR same failure set as `tests/KNOWN_FAILURES.txt`.

- [ ] **Step 2: If new failures appear, fix them**

- [ ] **Step 3: Defer commit**

---

### Task 4: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/fix-adr-0027-issue-file-frontmatter/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add _lib/issue_reporter.py _lib/post_flow_analysis.py _lib/cli/report_issue_cmd.py _lib/cli/issue_cmd.py \
  tests/unit/test_issue_reporter_frontmatter.py \
  openspec/changes/fix-adr-0027-issue-file-frontmatter/tasks.md \
  .rddf/plans/fix-adr-0027-issue-file-frontmatter.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] `python3 -m pytest tests/unit/test_issue_reporter_frontmatter.py -v` — 4 passed
- [ ] All 6 AC met (AC-1 through AC-6)
- [ ] Manual: `python3 -c "from skills._lib.cli.report_issue_cmd import cmd_report_issue; cmd_report_issue(['--exit-code', '137', 'demo'])"` produces issue file with all 6 Reporter fields
- [ ] `grep -E "(/home/|/Users/)" .rddf/issues/*.md` — no home paths leak
- [ ] `openspec validate fix-adr-0027-issue-file-frontmatter` → valid

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Changes to dedup_hash algorithm
- ❌ Changes to retention strategy
- ❌ Changes to `sanitizer.py` (already extended)
- ❌ New external dependencies
- ❌ prisma/git history/network reporter fields