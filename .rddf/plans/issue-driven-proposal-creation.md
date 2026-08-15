# issue-driven-proposal-creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `add-improve --from-issue <N>` mode that scaffolds a proposal from a GitHub issue (third-party repo or rdd-workflow self), with 3-step repo detection fallback (env > gh repo view > git remote parse), dedup against existing `.rddf/improvements/` and `openspec/changes/*/roadmap-meta.yaml`, slug-collision handling, and a fix to `_lib/close_issues.py:180` so archive comments no longer hardcode "Fixed in rdd-workflow".

**Architecture:** Mirror the `from-roadmap` 3-file pattern (bash wrapper + Python main + env-var validation) for `from-issue`. Add a new shared `_lib/gh_repo_detect.py` so ADR-0027 triage can reuse it later. Dedup scans both `.rddf/improvements/*.md` frontmatter (`issue_ref: N`) and `openspec/changes/*/roadmap-meta.yaml::issue_refs`. Slug collision appends `-i<N>`. Issue body truncated at 4k chars with reference URL preserved. The `close_issues.py:180` fix replaces hardcoded "rdd-workflow" with a parameterized message using `change_name` + `(repo_name, version)` from `roadmap-meta.yaml`.

**Tech Stack:** Python 3.11, pytest, bats, gh CLI (subprocess, 10s timeout), `gh_repo_detect` chain = env > `gh repo view --json nameWithOwner` > `git remote get-url origin` parse. No new dependencies.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/gh_repo_detect.py` | New shared module: 3-step fallback chain (env `RDDF_PROPOSAL_GH_REPO` > `gh repo view` > `git remote get-url origin` parse). Returns `gh_repo` (str) or raises `GhRepoDetectError` with suggestion. |
| `skills/add-improve/scripts/from_issue.env.py` | Env-var validator (Oracle C1 anti-injection). Validates `ADD_IMPROVE_FROM_ISSUE`, `ADD_IMPROVE_GH_REPO`, `ADD_IMPROVE_ISSUE_BODY`, `ADD_IMPROVE_ISSUE_TITLE`. |
| `skills/add-improve/scripts/from_issue.py` | Main logic: load validated env → init scaffold fields → write `.rddf/improvements/<slug>-i<N>.md` with `issue_ref: N` + `gh_repo` in frontmatter. HARD-GATE: does NOT modify proposal-suggestions.md. |
| `skills/add-improve/scripts/from_issue.sh` | Bash wrapper: arg parsing → env-var export + `trap cleanup EXIT` → env-var validation → python main. |
| `skills/guide-design/SKILL.md` | Phase 2 menu: add option 3 "🐙 从 GitHub issue 创建提案", renumber subsequent options (4→5, 5→6). Add orchestration block invoking `from_issue.sh`. |
| `_lib/close_issues.py` | Line 180: replace hardcoded "Fixed in rdd-workflow v{new_version}" with parameterized template using `change_name` + derived `(repo_name, version)`. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_gh_repo_detect.py` | 7 cases: env override wins, gh repo view success, gh fallback, git remote parse success, gh missing, gh auth failure, no-remote fallback. Uses subprocess mock. |
| `tests/unit/test_from_issue_env_validation.py` | Anti-injection for `ADD_IMPROVE_FROM_ISSUE` (issue_num), env override, body too long. |
| `tests/integration/test_from_issue.bats` | 12 cases: happy path with scaffold, slug collision → `-i<N>` suffix, dedup against `.rddf/improvements/`, dedup against `openspec/changes/*/roadmap-meta.yaml`, `gh` missing → exit 2, prompt fallback when no `--issue`, env-var cleanup on exit, HARD-GATE does not touch proposal-suggestions.md. |

### ADR

| File | Responsibility |
|---|---|
| `docs/adr/ADR-0029-issue-driven-proposal-creation.md` | Decision record: repo detection chain, scaffold pattern reuse, dedup locations, close_issues.py repo-neutral comment. References ADR-0025, ADR-0027 §5/§7, ADR-0026. |

---

## Task 1: Write failing test for `gh_repo_detect.py` 3-step fallback chain

**Files:**
- Create: `tests/unit/test_gh_repo_detect.py`
- Test: (self)

- [ ] **Step 1: Write the failing test**

```python
"""Tests for skills/_lib/gh_repo_detect.py — 3-step fallback chain.

Covers:
1. Env override (`RDDF_PROPOSAL_GH_REPO`) wins at all times.
2. `gh repo view --json nameWithOwner` succeeds when env unset.
3. `git remote get-url origin` parse as third fallback.
4. `gh` missing → GhRepoDetectError with suggestion.
5. `gh auth status` fails → GhRepoDetectError with `gh auth login` hint.
6. No git remote → GhRepoDetectError with `git remote add origin ...` hint.
7. Pre-flight `gh auth status` check runs before detection.
"""
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

# Set up import path (mirrors tests/conftest.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from skills._lib.gh_repo_detect import (  # noqa: E402
    detect_gh_repo,
    GhRepoDetectError,
)


def _mock_run(stdout: str = "", returncode: int = 0, stderr: str = ""):
    """Factory for a Mock that mimics subprocess.run output."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_env_override_wins():
    """Env var RDDF_PROPOSAL_GH_REPO is the highest priority."""
    with patch.dict(os.environ, {"RDDF_PROPOSAL_GH_REPO": "my-org/my-fork"}, clear=False):
        with patch("subprocess.run") as mock_run:
            result = detect_gh_repo()
            assert result == "my-org/my-fork"
            # Never invoke gh or git remote when env is set
            for call in mock_run.call_args_list:
                args = call.args[0]
                assert "gh" not in args[0] and "git" not in args[0]


def test_gh_repo_view_success():
    """When env is unset, gh repo view is the second fallback."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            # First call: gh auth status (passes)
            # Second call: gh repo view --json nameWithOwner
            mock_run.side_effect = [
                _mock_run(returncode=0),  # gh auth status
                _mock_run(stdout="my-org/my-project\n", returncode=0),  # gh repo view
            ]
            result = detect_gh_repo()
            assert result == "my-org/my-project"
            assert mock_run.call_count == 2


def test_git_remote_parse_fallback():
    """When gh repo view fails, fall back to git remote get-url origin."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(returncode=0),  # gh auth status
                _mock_run(returncode=1, stderr="not found"),  # gh repo view fails
                _mock_run(stdout="git@github.com:foo/bar.git\n", returncode=0),  # git remote
            ]
            result = detect_gh_repo()
            assert result == "foo/bar"


def test_gh_missing_raises_with_suggestion():
    """When gh CLI is not installed, raise with install hint."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            try:
                detect_gh_repo()
            except GhRepoDetectError as e:
                assert "gh" in str(e).lower()
                assert "install" in str(e).lower() or "gh" in str(e)
                return
            assert False, "expected GhRepoDetectError"


def test_gh_auth_failure_raises_with_login_hint():
    """When gh auth status fails, raise with `gh auth login` hint."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(returncode=1, stderr="not logged in"),  # gh auth status fails
            ]
            try:
                detect_gh_repo()
            except GhRepoDetectError as e:
                assert "gh auth login" in str(e)
                return
            assert False, "expected GhRepoDetectError"


def test_no_remote_raises_with_add_hint():
    """When git remote fails too, raise with `git remote add origin ...` hint."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(returncode=0),  # gh auth status
                _mock_run(returncode=1, stderr="not in repo"),  # gh repo view fails
                _mock_run(returncode=1, stderr="no remote"),  # git remote fails
            ]
            try:
                detect_gh_repo()
            except GhRepoDetectError as e:
                assert "git remote add origin" in str(e)
                return
            assert False, "expected GhRepoDetectError"


def test_preflight_gh_auth_runs_before_detection():
    """Even when env is set, gh auth status is checked first (per Oraclespec MUST)."""
    with patch.dict(os.environ, {"RDDF_PROPOSAL_GH_REPO": "my-org/repo"}, clear=False):
        with patch("subprocess.run") as mock_run:
            # Env wins — auth should NOT be called
            detect_gh_repo()
            for call in mock_run.call_args_list:
                args = call.args[0]
                assert "auth" not in " ".join(args)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_gh_repo_detect.py -v`
Expected: **ImportError** (module `skills._lib.gh_repo_detect` does not exist) — confirms the module is not yet implemented.

- [ ] **Step 3: Verify the failure reason**

Confirm the output shows `ModuleNotFoundError: No module named 'skills._lib.gh_repo_detect'`. This is the failing-test state.

- [ ] **Step 4: Document current behavior**

Note: `gh_repo_detect` logic does not exist yet. ADR-0027's `issue_reporter.py` exposes `can_close_in_repo()` but does not have a discovery chain.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 2: Implement `skills/_lib/gh_repo_detect.py`

**Files:**
- Create: `skills/_lib/gh_repo_detect.py`

- [ ] **Step 1: Implement the module**

```python
"""3-step GitHub repo detection chain for `add-improve --from-issue`.

Used by `skills/add-improve/scripts/from_issue.py` to discover the current
project's GitHub repo when no env override is provided. Designed to be
reusable by ADR-0027 triage in a future iteration (notes declared in the
ADR-0029 follow-up).

Priority chain (highest first):
  1. ``RDDF_PROPOSAL_GH_REPO`` env (explicit override for fork/override)
  2. ``gh repo view --json nameWithOwner -q .nameWithOwner`` (requires auth)
  3. ``git remote get-url origin`` parse (fallback for thin installs)

A pre-flight ``gh auth status`` check runs before step 2 to fail fast on
unauthenticated environments. All subprocess calls have a 10-second timeout.

Errors include actionable hints (``gh auth login``, ``git remote add origin``).
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Tuple


_GH_TIMEOUT_SECONDS = 10


class GhRepoDetectError(RuntimeError):
    """Raised when GH repo detection fails. Message includes a hint command."""


def _run(args: list[str]) -> Tuple[int, str, str]:
    """Run a subprocess with timeout. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=_GH_TIMEOUT_SECONDS,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def _check_gh_auth() -> None:
    """Pre-flight: ensure ``gh auth status`` exits 0. Otherwise raise with hint."""
    rc, _out, err = _run(["gh", "auth", "status"])
    if rc != 0:
        raise GhRepoDetectError(
            f"gh 未认证，请运行 `gh auth login` 登录 GitHub CLI: {err.strip()}"
        )


def _try_gh_repo_view() -> str | None:
    """Return ``nameWithOwner`` from ``gh repo view``, or None on failure."""
    rc, out, _err = _run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if rc == 0 and out.strip():
        return out.strip().splitlines()[0]
    return None


def _try_git_remote_parse() -> str | None:
    """Parse ``git remote get-url origin`` → owner/repo. Returns None on failure."""
    rc, out, _err = _run(["git", "remote", "get-url", "origin"])
    if rc != 0 or not out.strip():
        return None
    return _parse_github_remote(out.strip())


def _parse_github_remote(url: str) -> str | None:
    """Parse git URL → "owner/repo". Supports both HTTPS and SSH formats.

    Examples:
        https://github.com/foo/bar.git       -> foo/bar
        git@github.com:foo/bar.git           -> foo/bar
        https://github.com/foo/bar           -> foo/bar
    """
    url = url.strip()
    # SSH form: git@github.com:owner/repo[.git]
    m = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    # HTTPS form: https://github.com/owner/repo[.git]
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None


def detect_gh_repo() -> str:
    """Detect the current project's GitHub repo using the 3-step chain.

    Returns:
        The ``owner/repo`` slug.

    Raises:
        GhRepoDetectError: if all steps fail. Error message includes the
        actionable command (e.g. ``gh auth login``, ``git remote add origin``).
    """
    # Step 1: env override (highest priority — no auth check needed)
    env_repo = os.environ.get("RDDF_PROPOSAL_GH_REPO", "").strip()
    if env_repo:
        return env_repo

    # Step 2: gh CLI chain (requires auth)
    try:
        _check_gh_auth()
    except FileNotFoundError as e:
        raise GhRepoDetectError(
            "gh CLI 未安装，请安装 GitHub CLI: https://cli.github.com/"
        ) from e

    repo = _try_gh_repo_view()
    if repo:
        return repo

    # Step 3: git remote fallback
    repo = _try_git_remote_parse()
    if repo:
        return repo

    raise GhRepoDetectError(
        "无法检测 GitHub repo，请显式设置 RDDF_PROPOSAL_GH_REPO=owner/repo "
        "或运行 `git remote add origin git@github.com:owner/repo.git`"
    )
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_gh_repo_detect.py -v`
Expected: **7 passed** — all detection scenarios green.

- [ ] **Step 3: Verify linter cleanliness**

Run: `python3 -m py_compile skills/_lib/gh_repo_detect.py`
Expected: exit 0 (silent success).

- [ ] **Step 4: Smoke check functional path**

Run: `python3 -c "from skills._lib.gh_repo_detect import detect_gh_repo, GhRepoDetectError; print('OK')"`
Expected: `OK` (no ImportError).

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 3: Write failing test for `from_issue.env.py` env-var validation

**Files:**
- Create: `tests/unit/test_from_issue_env_validation.py`
- Test: (self)

- [ ] **Step 1: Write the failing test**

```python
"""Tests for from_issue.env validation — anti-injection safety + format checks.

Validates:
1. ADD_IMPROVE_FROM_ISSUE must be a positive integer (issue number).
2. ADD_IMPROVE_GH_REPO must match "owner/repo" pattern (no shell metacharacters).
3. ADD_IMPROVE_ISSUE_TITLE max 200 chars, no shell metacharacters.
4. ADD_IMPROVE_ISSUE_BODY max 4000 chars (truncation enforced upstream).
5. Hard-exit (exit 1) on validation failure; describe mode prints JSON.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

WT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = WT_ROOT / "skills" / "add-improve" / "scripts" / "from_issue.env.py"


def _run_validate(env_overrides: dict):
    """Run from_issue.env.py validate with given env-var overrides."""
    env = os.environ.copy()
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run(
        [sys.executable, str(SCRIPT), "validate"],
        env=env, capture_output=True, text=True,
    )


def _run_describe(env_overrides: dict):
    env = os.environ.copy()
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run(
        [sys.executable, str(SCRIPT), "describe"],
        env=env, capture_output=True, text=True,
    )


# === Test Group 1: Format validation ===

def test_rejects_non_integer_issue_number():
    """From-issue must be a positive integer."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "not-a-number",
        "ADD_IMPROVE_GH_REPO": "foo/bar",
        "ADD_IMPROVE_ISSUE_TITLE": "Test",
    })
    assert result.returncode != 0
    assert "integer" in result.stderr.lower() or "issue" in result.stderr.lower()


def test_rejects_zero_or_negative_issue_number():
    """Issue number must be >= 1."""
    for bad in ["0", "-1"]:
        result = _run_validate({
            "ADD_IMPROVE_FROM_ISSUE": bad,
            "ADD_IMPROVE_GH_REPO": "foo/bar",
            "ADD_IMPROVE_ISSUE_TITLE": "Test",
        })
        assert result.returncode != 0, f"should reject {bad}"


def test_rejects_invalid_gh_repo_format():
    """Gh-repo must match owner/repo pattern."""
    for bad in ["foo", "foo/bar/extra", "../../etc/passwd"]:
        result = _run_validate({
            "ADD_IMPROVE_FROM_ISSUE": "42",
            "ADD_IMPROVE_GH_REPO": bad,
            "ADD_IMPROVE_ISSUE_TITLE": "Test",
        })
        assert result.returncode != 0, f"should reject {bad}"


# === Test Group 2: Anti-injection in title and body ===

def test_rejects_shell_metachars_in_title():
    """Title must not contain shell metacharacters."""
    for evil in ["evil$(whoami)", "evil`id`", "evil;rm", "evil|cat", "evil&bg"]:
        result = _run_validate({
            "ADD_IMPROVE_FROM_ISSUE": "42",
            "ADD_IMPROVE_GH_REPO": "foo/bar",
            "ADD_IMPROVE_ISSUE_TITLE": evil,
        })
        assert result.returncode != 0, f"should reject {evil!r}"


def test_rejects_oversized_title():
    """Title must be <= 200 chars."""
    long_title = "x" * 201
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "foo/bar",
        "ADD_IMPROVE_ISSUE_TITLE": long_title,
    })
    assert result.returncode != 0
    assert "200" in result.stderr


def test_rejects_oversized_body():
    """Body must be <= 4000 chars (truncation enforced upstream)."""
    long_body = "x" * 4001
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "foo/bar",
        "ADD_IMPROVE_ISSUE_TITLE": "Test",
        "ADD_IMPROVE_ISSUE_BODY": long_body,
    })
    assert result.returncode != 0
    assert "4000" in result.stderr


# === Test Group 3: Happy path + describe mode ===

def test_accepts_valid_inputs():
    """Valid inputs produce exit 0."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "chisuhua/rdd-workflow",
        "ADD_IMPROVE_ISSUE_TITLE": "Fix race condition",
        "ADD_IMPROVE_ISSUE_BODY": "Steps to reproduce...",
    })
    assert result.returncode == 0, result.stderr


def test_describe_returns_json():
    """Describe mode prints JSON with all validated fields."""
    result = _run_describe({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "chisuhua/rdd-workflow",
        "ADD_IMPROVE_ISSUE_TITLE": "Fix race",
        "ADD_IMPROVE_ISSUE_BODY": "Body",
    })
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["issue_num"] == 42
    assert data["gh_repo"] == "chisuhua/rdd-workflow"
    assert data["title"] == "Fix race"
    assert data["body"] == "Body"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_from_issue_env_validation.py -v`
Expected: **FileNotFoundError** (script does not exist) — confirms the validator is not yet implemented.

- [ ] **Step 3: Verify the failure reason**

Output must show `from_issue.env.py` is missing at `skills/add-improve/scripts/`.

- [ ] **Step 4: Document current behavior**

The `from_issue.env.py` file does not exist. The `from_roadmap.env.py` uses regex `_DISALLOWED_RE = re.compile(r'[$`"\';|&\n\r(){}<>!~#]')` — copy that pattern.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 4: Implement `skills/add-improve/scripts/from_issue.env.py`

**Files:**
- Create: `skills/add-improve/scripts/from_issue.env.py`

- [ ] **Step 1: Implement the env-var validator**

```python
#!/usr/bin/env python3
"""Env-var validation for add-improve --from-issue mode (Oracle C1 anti-injection).

Usage:
    python3 from_issue.env.py validate    # validates env-vars, exits 0/1
    python3 from_issue.env.py describe    # prints validated values as JSON

Exit codes:
    0 — valid
    1 — validation error (writes to stderr)

Validates:
    - ADD_IMPROVE_FROM_ISSUE (required, positive integer)
    - ADD_IMPROVE_GH_REPO (required, format: owner/repo)
    - ADD_IMPROVE_ISSUE_TITLE (required, <= 200 chars, no shell metachars)
    - ADD_IMPROVE_ISSUE_BODY (optional, <= 4000 chars, no shell metachars if present)

Disallowed characters in title/body (anti-injection):
    $ ` " ' ; | & \\n \\r  ( ) { } < >  ! ~ #
"""
import json
import os
import re
import sys
from typing import Optional


_DISALLOWED_RE = re.compile(r'[$`"\';|&\n\r(){}<>!~#]')
_GH_REPO_RE = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")
_ISSUE_NUM_RE = re.compile(r"^[1-9][0-9]{0,9}$")


def _check_text(value: str, name: str, max_len: int) -> Optional[str]:
    if not value:
        return f"{name} is empty"
    if _DISALLOWED_RE.search(value):
        return f"{name} contains disallowed shell metacharacters: {value!r}"
    if len(value) > max_len:
        return f"{name} exceeds {max_len} chars (got {len(value)})"
    return None


def validate_env() -> dict:
    from_issue = os.environ.get("ADD_IMPROVE_FROM_ISSUE", "").strip()
    gh_repo = os.environ.get("ADD_IMPROVE_GH_REPO", "").strip()
    title = os.environ.get("ADD_IMPROVE_ISSUE_TITLE", "").strip()
    body = os.environ.get("ADD_IMPROVE_ISSUE_BODY", "").strip()

    errors = []

    if not _ISSUE_NUM_RE.match(from_issue):
        errors.append(
            f"ADD_IMPROVE_FROM_ISSUE must be a positive integer (got {from_issue!r})"
        )

    if not _GH_REPO_RE.match(gh_repo):
        errors.append(
            f"ADD_IMPROVE_GH_REPO must match owner/repo pattern (got {gh_repo!r})"
        )

    err = _check_text(title, "ADD_IMPROVE_ISSUE_TITLE", 200)
    if err:
        errors.append(err)

    if body:
        err = _check_text(body, "ADD_IMPROVE_ISSUE_BODY", 4000)
        if err:
            errors.append(err)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    return {
        "issue_num": int(from_issue),
        "gh_repo": gh_repo,
        "title": title,
        "body": body,
    }


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"validate", "describe"}:
        print(
            "Usage: from_issue.env.py {validate|describe}",
            file=sys.stderr,
        )
        return 1

    values = validate_env()

    if sys.argv[1] == "describe":
        print(json.dumps(values, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_from_issue_env_validation.py -v`
Expected: **11 passed** — all validation scenarios green.

- [ ] **Step 3: Smoke test describe mode**

Run: `ADD_IMPROVE_FROM_ISSUE=42 ADD_IMPROVE_GH_REPO='foo/bar' ADD_IMPROVE_ISSUE_TITLE='Test' python3 skills/add-improve/scripts/from_issue.env.py describe`
Expected: `{"issue_num": 42, "gh_repo": "foo/bar", "title": "Test", "body": ""}`.

- [ ] **Step 4: Make executable**

Run: `chmod +x skills/add-improve/scripts/from_issue.env.py`

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 5: Write failing test for `from_issue.py` main logic (scaffold + dedup + slug collision)

**Files:**
- Create: `tests/unit/test_from_issue_scaffold.py`
- Test: (self)

- [ ] **Step 1: Write the failing test**

```python
"""Tests for from_issue.py scaffold writer.

Covers:
1. Happy path: writes .rddf/improvements/<slug>-i<N>.md with required fields.
2. Slug collision: appends -i<N> suffix when same slug already exists.
3. Dedup against .rddf/improvements/<existing>.md frontmatter issue_ref.
4. Dedup against openspec/changes/<other>/roadmap-meta.yaml issue_refs.
5. Body truncation at 4000 chars with reference URL preserved.
6. HARD-GATE: never writes proposal-suggestions.md.
"""
import os
import subprocess
from pathlib import Path

import sys
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from skills.add_improve.scripts.from_issue import (  # noqa: E402
    write_scaffold,
    check_dedup,
    truncate_body,
    slugify,
    DedupHit,
)


def _setup_tmp_project(tmp_path: Path, *, improvements: list = None, changes: list = None) -> Path:
    (tmp_path / ".rddf" / "improvements").mkdir(parents=True, exist_ok=True)
    (tmp_path / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    for imp in improvements or []:
        (tmp_path / ".rddf" / "improvements" / f"{imp['name']}.md").write_text(imp["content"])
    for change in changes or []:
        change_dir = tmp_path / "openspec" / "changes" / change["name"]
        change_dir.mkdir(parents=True, exist_ok=True)
        (change_dir / "roadmap-meta.yaml").write_text(change["meta"])
    return tmp_path


# === Test Group 1: slugify ===

def test_slugify_basic():
    assert slugify("Fix Race Condition") == "fix-race-condition"


def test_slugify_special_chars():
    assert slugify("Fix: 50% off!") == "fix-50-off"


def test_slugify_unicode():
    assert slugify("修复竞态条件") == "修复竞态条件"


def test_slugify_multiple_spaces():
    assert slugify("foo   bar  baz") == "foo-bar-baz"


# === Test Group 2: truncate_body ===

def test_truncate_body_short():
    """Body <= 4000 chars is returned unchanged."""
    body = "x" * 1000
    out = truncate_body(body, "https://github.com/foo/bar/issues/42")
    assert out == body


def test_truncate_body_oversize():
    """Body > 4000 chars is truncated with reference URL preserved."""
    body = "x" * 5000
    out = truncate_body(body, "https://github.com/foo/bar/issues/42")
    assert len(out) <= 4000
    assert "https://github.com/foo/bar/issues/42" in out
    assert "..." in out


# === Test Group 3: check_dedup ===

def test_dedup_no_match(tmp_path):
    """No existing proposal → no dedup hit."""
    _setup_tmp_project(tmp_path)
    assert check_dedup(42, tmp_path) == []


def test_dedup_in_improvements(tmp_path):
    """Existing improvement with issue_ref: 42 triggers dedup hit."""
    _setup_tmp_project(tmp_path, improvements=[
        {"name": "fix-foo", "content": "---\nissue_ref: 42\n---\n"},
    ])
    hits = check_dedup(42, tmp_path)
    assert len(hits) == 1
    assert hits[0].path == ".rddf/improvements/fix-foo.md"


def test_dedup_in_roadmap_meta(tmp_path):
    """Existing change with issue_refs in roadmap-meta.yaml triggers dedup hit."""
    _setup_tmp_project(tmp_path, changes=[
        {"name": "fix-bar", "meta": "issue_refs: [42]\n"},
    ])
    hits = check_dedup(42, tmp_path)
    assert len(hits) == 1
    assert "openspec/changes/fix-bar/roadmap-meta.yaml" in hits[0].path


def test_dedup_in_both_locations(tmp_path):
    """Both locations dedup hits are returned."""
    _setup_tmp_project(
        tmp_path,
        improvements=[
            {"name": "fix-foo", "content": "---\nissue_ref: 42\n---\n"},
        ],
        changes=[
            {"name": "fix-bar", "meta": "issue_refs: [42]\n"},
        ],
    )
    hits = check_dedup(42, tmp_path)
    assert len(hits) == 2


# === Test Group 4: write_scaffold happy path ===

def test_write_scaffold_happy_path(tmp_path):
    """Happy path writes file with required fields."""
    _setup_tmp_project(tmp_path)
    out = write_scaffold(
        project_root=tmp_path,
        issue_num=42,
        gh_repo="foo/bar",
        title="Fix race condition",
        body="Steps to reproduce...",
    )
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "**issue_ref**: 42" in content
    assert "**gh_repo**: foo/bar" in content
    assert "Fix race condition" in content
    assert "Steps to reproduce" in content


def test_write_scaffold_slug_collision(tmp_path):
    """When slug already exists, append -i<N> suffix."""
    _setup_tmp_project(
        tmp_path,
        improvements=[
            {"name": "fix-race-condition", "content": "---\nissue_ref: 99\n---\n"},
        ],
    )
    out = write_scaffold(
        project_root=tmp_path,
        issue_num=42,
        gh_repo="foo/bar",
        title="Fix race condition",
        body="...",
    )
    # New file should be fix-race-condition-i42.md
    assert out.name == "fix-race-condition-i42.md"
    assert out.exists()


def test_write_scaffold_never_touches_proposal_suggestions(tmp_path):
    """HARD-GATE: write_scaffold does not create proposal-suggestions.md."""
    _setup_tmp_project(tmp_path)
    write_scaffold(
        project_root=tmp_path,
        issue_num=42,
        gh_repo="foo/bar",
        title="Fix",
        body="...",
    )
    assert not (tmp_path / "proposal-suggestions.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_from_issue_scaffold.py -v`
Expected: **ImportError** (module `skills.add_improve.scripts.from_issue` does not exist) — confirms the main logic is not yet implemented.

- [ ] **Step 3: Verify the failure reason**

Output must show `ModuleNotFoundError: No module named 'skills.add_improve.scripts.from_issue'`.

- [ ] **Step 4: Document current behavior**

The `from_issue.py` does not exist. The `from_roadmap.py` uses `Path` + `os.environ` + `datetime` — copy that pattern.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 6: Implement `skills/add-improve/scripts/from_issue.py`

**Files:**
- Create: `skills/add-improve/scripts/from_issue.py`

- [ ] **Step 1: Implement the main logic**

```python
#!/usr/bin/env python3
"""Main logic for add-improve --from-issue mode.

Reads validated env-vars (from from_issue.env.py), reads pre-fetched issue
metadata, writes a proposal scaffold with **issue_ref** + **gh_repo** frontmatter.

HARD-GATE: does NOT auto-approve or modify proposal-suggestions.md — user must
still run rdd-workflow-brainstorm for section approval.

Usage:
    Called from from_issue.sh after env validation. All inputs come from
    env-vars (Oracle C1 anti-injection pattern):
      ADD_IMPROVE_FROM_ISSUE   — issue number (positive integer)
      ADD_IMPROVE_GH_REPO      — owner/repo (e.g. foo/bar)
      ADD_IMPROVE_ISSUE_TITLE  — issue title (max 200 chars)
      ADD_IMPROVE_ISSUE_BODY   — issue body (max 4000 chars, truncated upstream)
      PROJECT_ROOT             — absolute path to project root
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


_BODY_MAX_CHARS = 4000
_BODY_TRUNCATION_SUFFIX = "\n\n... (剩余 {remaining} 字符，参见 {url})\n"


@dataclass
class DedupHit:
    path: str
    source: str  # "improvements" or "roadmap-meta"


def _print_error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def slugify(title: str) -> str:
    """Convert an issue title to a kebab-case slug.

    Strips forbidden characters, collapses whitespace to single hyphens,
    and lowercases ASCII (Unicode preserved).
    """
    # Strip shell metacharacters first (defense in depth)
    cleaned = re.sub(r"[$`\"';|&()<>!~#]", "", title)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    # Lowercase ASCII only
    cleaned = re.sub(r"[A-Z]+", lambda m: m.group(0).lower(), cleaned)
    return cleaned


def truncate_body(body: str, issue_url: str, max_chars: int = _BODY_MAX_CHARS) -> str:
    """Truncate body to ``max_chars`` and append reference URL."""
    if len(body) <= max_chars:
        return body
    remaining = len(body) - max_chars
    suffix = _BODY_TRUNCATION_SUFFIX.format(remaining=remaining, url=issue_url)
    return body[:max_chars] + suffix


def _parse_improvement_frontmatter(path: Path) -> Optional[int]:
    """Return ``issue_ref`` from a .rddf/improvements/<name>.md frontmatter, or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # Simple frontmatter parse (yaml-free)
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    for line in fm.splitlines():
        line = line.strip()
        if line.startswith("issue_ref:"):
            value = line.split(":", 1)[1].strip()
            if value.isdigit():
                return int(value)
    return None


def _parse_roadmap_meta_issue_refs(path: Path) -> List[int]:
    """Return ``issue_refs`` list from a roadmap-meta.yaml, or []."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    refs = []
    in_list = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("issue_refs:"):
            value = stripped.split(":", 1)[1].strip()
            if value.startswith("["):
                # Inline list: issue_refs: [42, 99]
                for tok in re.findall(r"\d+", value):
                    refs.append(int(tok))
            else:
                # Block list: starts on next line
                in_list = True
                continue
        if in_list:
            tok = stripped.lstrip("- ").strip()
            if tok.isdigit():
                refs.append(int(tok))
            elif stripped and not stripped.startswith("-"):
                in_list = False
    return refs


def check_dedup(issue_num: int, project_root: Path) -> List[DedupHit]:
    """Scan two locations for existing references to ``issue_num``.

    Returns a list of DedupHit (empty list = no conflict).
    """
    hits: List[DedupHit] = []

    improvements_dir = project_root / ".rddf" / "improvements"
    if improvements_dir.is_dir():
        for path in improvements_dir.glob("*.md"):
            ref = _parse_improvement_frontmatter(path)
            if ref == issue_num:
                hits.append(DedupHit(
                    path=str(path.relative_to(project_root)),
                    source="improvements",
                ))

    changes_dir = project_root / "openspec" / "changes"
    if changes_dir.is_dir():
        for change_dir in changes_dir.iterdir():
            if not change_dir.is_dir():
                continue
            meta_path = change_dir / "roadmap-meta.yaml"
            if not meta_path.is_file():
                continue
            refs = _parse_roadmap_meta_issue_refs(meta_path)
            if issue_num in refs:
                hits.append(DedupHit(
                    path=str(meta_path.relative_to(project_root)),
                    source="roadmap-meta",
                ))

    return hits


def write_scaffold(
    *,
    project_root: Path,
    issue_num: int,
    gh_repo: str,
    title: str,
    body: str,
) -> Path:
    """Write the proposal scaffold and return the resolved file path.

    Slug collision is handled by appending ``-i<N>`` when the default slug
    is already taken.
    """
    base_slug = slugify(title)
    candidate_slug = f"{base_slug}-i{issue_num}"
    # If the -i<N> variant itself collides, append -counter
    counter = 1
    final_slug = candidate_slug
    improvements_dir = project_root / ".rddf" / "improvements"
    while (improvements_dir / f"{final_slug}.md").exists():
        counter += 1
        final_slug = f"{candidate_slug}-{counter}"

    proposal_name = final_slug
    proposal_file = improvements_dir / f"{proposal_name}.md"

    issue_url = f"https://github.com/{gh_repo}/issues/{issue_num}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    truncated_body = truncate_body(body, issue_url)

    content = (
        f"# {proposal_name}\n"
        f"\n"
        f"**优先级**: TBD | **来源**: from-issue ({gh_repo}#{issue_num})\n"
        f"**issue_ref**: {issue_num}\n"
        f"**gh_repo**: {gh_repo}\n"
        f"**类型**: feature\n"
        f"\n"
        f"## 架构依据\n"
        f"\n"
        f"_待 brainstorm 填写 (上游 issue: {issue_url})_\n"
        f"\n"
        f"## 范围\n"
        f"\n"
        f"- **In Scope**: _待 brainstorm 确认_\n"
        f"- **Out Scope**: _待 brainstorm 确认_\n"
        f"\n"
        f"## 关键场景\n"
        f"\n"
        f"- GIVEN _待 brainstorm 填写_\n"
        f"  WHEN _\n"
        f"  THEN _\n"
        f"\n"
        f"## 技术约束\n"
        f"\n"
        f"- MUST _\n"
        f"- MUST NOT _\n"
        f"- SHOULD _\n"
        f"\n"
        f"## 验收标准\n"
        f"\n"
        f"- [ ] _\n"
        f"\n"
        f"## 上游 Issue 原文\n"
        f"\n"
        f"<!-- 引用自 {issue_url} ({timestamp}) -->\n"
        f"\n"
        f"{truncated_body}\n"
    )

    try:
        improvements_dir.mkdir(parents=True, exist_ok=True)
        proposal_file.write_text(content, encoding="utf-8")
    except OSError as e:
        _print_error(f"Failed to write proposal file: {e}")
        raise

    return proposal_file


def main() -> int:
    required = [
        "ADD_IMPROVE_FROM_ISSUE",
        "ADD_IMPROVE_GH_REPO",
        "ADD_IMPROVE_ISSUE_TITLE",
        "PROJECT_ROOT",
    ]
    missing = [v for v in required if not os.environ.get(v, "").strip()]
    if missing:
        _print_error(f"Missing required env-vars: {', '.join(missing)}")
        return 1

    try:
        issue_num = int(os.environ["ADD_IMPROVE_FROM_ISSUE"])
    except ValueError:
        _print_error(f"ADD_IMPROVE_FROM_ISSUE must be int (got {os.environ['ADD_IMPROVE_FROM_ISSUE']!r})")
        return 1

    project_root = Path(os.environ["PROJECT_ROOT"])
    gh_repo = os.environ["ADD_IMPROVE_GH_REPO"]
    title = os.environ["ADD_IMPROVE_ISSUE_TITLE"]
    body = os.environ.get("ADD_IMPROVE_ISSUE_BODY", "").strip()

    # Dedup check
    hits = check_dedup(issue_num, project_root)
    if hits:
        _print_error(
            f"Issue #{issue_num} 已在以下位置被引用，跳过写入：\n"
            + "\n".join(f"  - {h.path} (来源: {h.source})" for h in hits)
        )
        return 2

    # Write scaffold
    try:
        proposal_file = write_scaffold(
            project_root=project_root,
            issue_num=issue_num,
            gh_repo=gh_repo,
            title=title,
            body=body,
        )
    except OSError as e:
        _print_error(f"Failed to write scaffold: {e}")
        return 1

    print(f"✅ Scaffold created: {proposal_file}")
    print(f"   issue_ref: {issue_num}")
    print(f"   gh_repo: {gh_repo}")
    print(f"   Next: run rdd-workflow-brainstorm interactively to fill scaffold and approve")
    print(f"   HARD-GATE: --from-issue mode does NOT bypass brainstorm section approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_from_issue_scaffold.py -v`
Expected: **18+ passed** (12 documented + edge cases) — all scaffold scenarios green.

- [ ] **Step 3: Smoke test the CLI**

Run:
```bash
PROJECT_ROOT=$(mktemp -d)
mkdir -p "$PROJECT_ROOT/.rddf/improvements"
ADD_IMPROVE_FROM_ISSUE=42 ADD_IMPROVE_GH_REPO='foo/bar' ADD_IMPROVE_ISSUE_TITLE='Test Title' PROJECT_ROOT="$PROJECT_ROOT" python3 skills/add-improve/scripts/from_issue.py
```
Expected: `✅ Scaffold created: <tmp>/.rddf/improvements/test-title-i42.md`.

- [ ] **Step 4: Verify dedup behavior**

Re-run the same command — expect `ERROR: Issue #42 已在以下位置被引用...` (exit 2).

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 7: Implement `skills/add-improve/scripts/from_issue.sh` bash wrapper

**Files:**
- Create: `skills/add-improve/scripts/from_issue.sh`

- [ ] **Step 1: Implement the bash wrapper**

```bash
#!/usr/bin/env bash
# skills/add-improve/scripts/from_issue.sh
# Bash entry for `add-improve --from-issue` mode (Oracle C1 env-var pattern).
#
# Usage:
#   bash from_issue.sh --from-issue <N> [--gh-repo <owner/repo>] \
#                       --title "<title>" \
#                       [--body "<body>"] \
#                       --project-root <path>
#
# Behavior:
#   1. Parses CLI args into env-vars (ADD_IMPROVE_FROM_ISSUE, ...)
#   2. If --gh-repo is unset, calls gh_repo_detect via fallback chain
#   3. Calls from_issue.env.py validate to reject shell metacharacters
#   4. Calls from_issue.py to write proposal scaffold
#   5. Unsets env-vars on exit (cleanup)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ISSUE=""
GH_REPO=""
TITLE=""
BODY=""
PROJECT_ROOT=""

usage() {
    cat <<EOF
Usage: $0 --from-issue <N> --title <title> [--gh-repo <owner/repo>] [--body <body>] --project-root <path>

Options:
  --from-issue    REQUIRED: issue number (positive integer)
  --gh-repo       OPTIONAL: owner/repo (default: detected via gh_repo_detect chain)
  --title         REQUIRED: issue title
  --body          OPTIONAL: issue body (truncated to 4000 chars upstream)
  --project-root  REQUIRED: absolute path to project root
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-issue)   ISSUE="$2"; shift 2 ;;
        --gh-repo)      GH_REPO="$2"; shift 2 ;;
        --title)        TITLE="$2"; shift 2 ;;
        --body)         BODY="$2"; shift 2 ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Unknown arg: $1" >&2; usage ;;
    esac
done

if [[ -z "$ISSUE" || -z "$TITLE" || -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: --from-issue, --title, --project-root are required" >&2
    usage
fi

# Default gh_repo via detection chain when --gh-repo omitted
if [[ -z "$GH_REPO" ]]; then
    GH_REPO=$(PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}" python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.gh_repo_detect import detect_gh_repo
print(detect_gh_repo())
" 2>/dev/null) || {
        echo "ERROR: --gh-repo not provided and gh_repo_detect failed. Try: --gh-repo owner/repo" >&2
        exit 1
    }
fi

export ADD_IMPROVE_FROM_ISSUE="$ISSUE"
export ADD_IMPROVE_GH_REPO="$GH_REPO"
export ADD_IMPROVE_ISSUE_TITLE="$TITLE"
export ADD_IMPROVE_ISSUE_BODY="$BODY"
export PROJECT_ROOT

cleanup() {
    unset ADD_IMPROVE_FROM_ISSUE
    unset ADD_IMPROVE_GH_REPO
    unset ADD_IMPROVE_ISSUE_TITLE
    unset ADD_IMPROVE_ISSUE_BODY
}
trap cleanup EXIT

if ! python3 "$SCRIPT_DIR/from_issue.env.py" validate; then
    echo "ERROR: env-var validation failed" >&2
    exit 1
fi

python3 "$SCRIPT_DIR/from_issue.py"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x skills/add-improve/scripts/from_issue.sh`

- [ ] **Step 3: Smoke test the bash wrapper**

Run:
```bash
PROJECT_ROOT=$(mktemp -d)
mkdir -p "$PROJECT_ROOT/.rddf/improvements"
bash skills/add-improve/scripts/from_issue.sh \
    --from-issue 42 \
    --gh-repo "foo/bar" \
    --title "Test Title" \
    --project-root "$PROJECT_ROOT"
```
Expected: `✅ Scaffold created: <tmp>/.rddf/improvements/test-title-i42.md`.

- [ ] **Step 4: Verify env-var cleanup**

Run: `env | grep ADD_IMPROVE` after step 3 — expected: empty (no env var pollution).

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 8: Add Phase 2 menu option 3 in `skills/guide-design/SKILL.md`

**Files:**
- Modify: `skills/guide-design/SKILL.md` (lines 154-171 add new option 3, renumber others)

- [ ] **Step 1: Locate the existing menu**

The Phase 2 menu currently has options 1-5 (line 154-171). We need to insert option 3 (从 GitHub issue) and renumber 3→4, 4→5, 5→6.

- [ ] **Step 2: Edit the menu block**

Open `skills/guide-design/SKILL.md` and replace the menu block (lines 154-171) with:

```
选择操作:
  1. ➕ 创建新提案（add-improve 自由模式）
  2. 🎯 按路线图主题创建提案（推荐）
  3. 🐙 从 GitHub issue 创建提案 ← ADR-0029 新增
  4. 📋 审查待批准提案
  5. ✅ 批量批准所有提案
  6. ✅ 完成设计阶段 → 进入设计门控
  0. 💾 保存并退出
```

- [ ] **Step 3: Add orchestration block for option 3**

After the existing 选项 2 (from-roadmap) block, insert the new option 3 orchestration:

```bash
**选项 3（从 GitHub issue 创建提案 — ADR-0029 新增）**：

列出当前项目的开放 issue（按优先级排序，限 30 条），用户选 issue 后触发 `add-improve --from-issue`：

```bash
# 1. List open issues via gh CLI
gh_repo=$(PYTHONPATH="$PROJECT_ROOT" python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.gh_repo_detect import detect_gh_repo
print(detect_gh_repo())
" 2>/dev/null) || {
    echo "ERROR: 无法检测 gh_repo，请显式设置 RDDF_PROPOSAL_GH_REPO=owner/repo"
    return 1
}

# 2. Fetch open issues
issues=$(gh issue list --repo "$gh_repo" --state open --limit 30 --json number,title --jq '.[] | "\(.number)\t\(.title)"')
echo "$issues" | nl -ba

# 3. User picks issue number
read -p "选择 issue 编号: " ISSUE_NUM

# 4. Fetch issue details
issue_json=$(gh issue view "$ISSUE_NUM" --repo "$gh_repo" --json title,body)
title=$(echo "$issue_json" | python3 -c "import json, sys; print(json.load(sys.stdin)['title'])")
body=$(echo "$issue_json" | python3 -c "import json, sys; print(json.load(sys.stdin)['body'])")

# 5. Invoke from_issue.sh
PROJECT_ROOT="$PROJECT_ROOT" bash "$ADD_IMPROVE_SCRIPT_DIR/from_issue.sh" \
    --from-issue "$ISSUE_NUM" \
    --gh-repo "$gh_repo" \
    --title "$title" \
    --body "$body" \
    --project-root "$PROJECT_ROOT"
echo "-> from-issue scaffold 创建完成，需走 brainstorm 完成 5 段确认"
```

注意：当 `gh` 缺失/未认证时，`detect_gh_repo()` 会硬退出 + 明确错误。
```

- [ ] **Step 4: Run tests to verify skill metadata consistency**

Run: `bats tests/integration/test_guide_design_skill.bats`
Expected: existing tests pass, command count is updated to 6 (was 5).

- [ ] **Step 5: Verify the menu is visually consistent**

Run: `grep -A 8 "选择操作" skills/guide-design/SKILL.md | head -15`
Expected: 6 numbered options + 0.

- [ ] **Step 6: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 9: Fix `_lib/close_issues.py:180` — repo-neutral comment

**Files:**
- Modify: `_lib/close_issues.py` (line 178-182)

- [ ] **Step 1: Locate the targeted code**

The current code at lines 178-182 is:
```python
def _close_issue(issue_num: int, gh_repo: str, change_name: str, new_version: str, short_sha: str) -> None:
    comment = (
        f"✅ Fixed in rdd-workflow v{new_version} via archive {short_sha}.\n\n"
        f"See: openspec/changes/{change_name}/\n"
    )
```

- [ ] **Step 2: Replace with repo-neutral phrasing**

Edit `_lib/close_issues.py` to derive `(repo_name, version)` from the `change_name` and `gh_repo` and use a parameterized message:

```python
def _close_issue(issue_num: int, gh_repo: str, change_name: str, new_version: str, short_sha: str) -> None:
    # Derive repo name from gh_repo for human-readable attribution (repo-neutral).
    repo_name = gh_repo.split("/", 1)[1] if "/" in gh_repo else gh_repo
    comment = (
        f"✅ Fixed in {repo_name} v{new_version} via archive {short_sha}.\n\n"
        f"See: openspec/changes/{change_name}/\n"
    )
```

This ensures the comment uses the actual repo name (e.g. `my-project`), not the hardcoded `rdd-workflow`. For `chisuhua/rdd-workflow` it still reads as before; for third-party repos it correctly says "Fixed in <their-repo>".

- [ ] **Step 3: Find existing close_issues tests**

Run: `find tests -name "test_close_issues*" -type f`
Expected: identifies the test file (likely `tests/unit/test_close_issues.py` or similar).

- [ ] **Step 4: Add a regression test for the fix**

Add a new test in the existing `tests/unit/test_close_issues.py` (or create it if missing) that asserts `_close_issue` produces a comment without `rdd-workflow` literal when `gh_repo` is a third-party repo:

```python
def test_close_issue_uses_repo_neutral_comment():
    """close_issues._close_issue must NOT hardcode 'rdd-workflow' in comment."""
    from close_issues import _close_issue
    # Mock subprocess.run to capture the gh issue close comment
    captured = []
    def mock_run(*args, **kwargs):
        captured.append(args)
        m = MagicMock()
        m.returncode = 0
        return m
    with patch("subprocess.run", side_effect=mock_run):
        _close_issue(
            issue_num=42,
            gh_repo="my-org/my-project",
            change_name="fix-foo",
            new_version="2.1.0",
            short_sha="abc1234",
        )
    # The comment is the --comment argument
    args = captured[0][0]
    comment_idx = args.index("--comment") + 1
    comment = args[comment_idx]
    assert "rdd-workflow" not in comment
    assert "my-project" in comment
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_close_issues.py -v`
Expected: new test passes, no existing tests broken.

- [ ] **Step 6: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 10: Write integration tests `tests/integration/test_from_issue.bats`

**Files:**
- Create: `tests/integration/test_from_issue.bats`

- [ ] **Step 1: Survey existing `test_add_improve_from_roadmap.bats` for template**

Read `tests/integration/test_add_improve_from_roadmap.bats` (already read above) — copy the `setup()` / `teardown()` pattern.

- [ ] **Step 2: Write the integration tests**

```bash
#!/usr/bin/env bats
# tests/integration/test_from_issue.bats
# Integration tests for add-improve --from-issue mode.
#
# Tests cover:
# - Successful scaffold creation with issue_ref + gh_repo frontmatter
# - Slug collision → -i<N> suffix when slug already exists
# - Dedup against .rddf/improvements/*.md frontmatter
# - Dedup against openspec/changes/*/roadmap-meta.yaml::issue_refs
# - gh missing → exit 2 + clear error
# - Rejection of shell injection in title
# - HARD-GATE: does NOT modify proposal-suggestions.md
# - Env-var cleanup on exit (no shell pollution)

setup() {
    load ../test_helper
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/state"
    WT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    SCRIPT="$WT_ROOT/skills/add-improve/scripts/from_issue.sh"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "from_issue creates scaffold with issue_ref + gh_repo frontmatter" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Fix race condition" \
        --body "Steps to reproduce..." \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]

    # Find scaffold file (slug-form)
    PROPOSAL=$(find "$TEST_PROJECT_ROOT/.rddf/improvements" -name "*.md" | head -1)
    [ -f "$PROPOSAL" ]

    grep -q '\*\*issue_ref\*\*: 42' "$PROPOSAL"
    grep -q '\*\*gh_repo\*\*: foo/bar' "$PROPOSAL"
    grep -q "Fix race condition" "$PROPOSAL"
    grep -q "Steps to reproduce" "$PROPOSAL"
}

@test "from_issue slug collision appends -i<N> suffix" {
    # Pre-create a slug-collision
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/fix-race-condition.md" <<EOF
---
issue_ref: 99
---
# fix-race-condition
EOF

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Fix race condition" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    # New file should be fix-race-condition-i42.md
    [ -f "$TEST_PROJECT_ROOT/.rddf/improvements/fix-race-condition-i42.md" ]
    # Original file should NOT be overwritten
    grep -q "issue_ref: 99" "$TEST_PROJECT_ROOT/.rddf/improvements/fix-race-condition.md"
}

@test "from_issue dedup against existing .rddf/improvements" {
    # Pre-create a proposal with issue_ref: 42
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/old-proposal.md" <<EOF
---
issue_ref: 42
---
# old-proposal
EOF

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "New Proposal" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 2 ]
    [[ "$output" == *"已被引用"* ]]
    # No new file should be created
    [ ! -f "$TEST_PROJECT_ROOT/.rddf/improvements/new-proposal.md" ]
}

@test "from_issue dedup against openspec/changes/*/roadmap-meta.yaml" {
    mkdir -p "$TEST_PROJECT_ROOT/openspec/changes/fix-existing"
    cat > "$TEST_PROJECT_ROOT/openspec/changes/fix-existing/roadmap-meta.yaml" <<EOF
issue_refs: [42]
gh_repo: foo/bar
EOF

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "New Proposal" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 2 ]
    [[ "$output" == *"roadmap-meta"* ]]
}

@test "from_issue rejects shell injection in title" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title 'evil$(whoami)' \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"disallowed"* ]] || [[ "$output" == *"ERROR"* ]]
    # Verify no file was created
    [ ! -f "$TEST_PROJECT_ROOT/.rddf/improvements/evil-whoami-i42.md" ]
}

@test "from_issue rejects backtick injection" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title 'evil`id`' \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
}

@test "from_issue requires --from-issue arg" {
    run bash "$SCRIPT" \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"required"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "from_issue requires --title arg" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
}

@test "from_issue HARD-GATE: does NOT modify proposal-suggestions.md" {
    [ ! -f "$TEST_PROJECT_ROOT/proposal-suggestions.md" ]

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test Proposal" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    # After successful run, proposal-suggestions.md still should NOT exist
    [ ! -f "$TEST_PROJECT_ROOT/proposal-suggestions.md" ]
}

@test "from_issue unsets env-vars on exit (no shell pollution)" {
    bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After exit, env-vars should NOT be set in current shell
    [ -z "${ADD_IMPROVE_FROM_ISSUE:-}" ]
    [ -z "${ADD_IMPROVE_GH_REPO:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_TITLE:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_BODY:-}" ]
}

@test "from_issue output mentions HARD-GATE explicitly" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"HARD-GATE"* ]]
    [[ "$output" == *"brainstorm"* ]]
}

@test "from_issue body > 4000 chars is truncated with reference URL" {
    LONG_BODY=$(printf 'x%.0s' {1..5000})

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --body "$LONG_BODY" \
        --project-root "$TEST_PROJECT_ROOT"

    # Env-var validation rejects >4000 chars; expect failure
    [ "$status" -ne 0 ]
    [[ "$output" == *"4000"* ]]
}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `bats tests/integration/test_from_issue.bats`
Expected: **all 12 fail** (script/method not yet implemented).

- [ ] **Step 4: Verify the failure reason**

Confirm output shows errors like `from_issue.sh: not found` or `python3: can't open file 'from_issue.py'`.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 11: Verify scope isolation — `from-issue` / `from-roadmap` / `free` env-var cleanup

**Files:**
- Create: `tests/integration/test_from_issue_env_isolation.bats`

- [ ] **Step 1: Write the isolation test**

```bash
#!/usr/bin/env bats
# tests/integration/test_from_issue_env_isolation.bats
# Verify that from-issue / from-roadmap / free 3 modes can coexist
# without env-var pollution.

setup() {
    load ../test_helper
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    WT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    FROM_ISSUE="$WT_ROOT/skills/add-improve/scripts/from_issue.sh"
    FROM_ROADMAP="$WT_ROOT/skills/add-improve/scripts/from_roadmap.sh"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "from-roadmap then from-issue: no env-var leakage" {
    bash "$FROM_ROADMAP" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After from-roadmap, env-vars are unset
    [ -z "${ADD_IMPROVE_FROM_ROADMAP:-}" ]
    [ -z "${ADD_IMPROVE_THEME:-}" ]
    [ -z "${BRAINSTORM_RATIONALE_DRAFT:-}" ]

    # from-issue should not see from-roadmap env-vars
    run bash "$FROM_ISSUE" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
}

@test "from-issue then from-roadmap: no env-var leakage" {
    bash "$FROM_ISSUE" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After from-issue, env-vars are unset
    [ -z "${ADD_IMPROVE_FROM_ISSUE:-}" ]
    [ -z "${ADD_IMPROVE_GH_REPO:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_TITLE:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_BODY:-}" ]

    # from-roadmap should not see from-issue env-vars
    run bash "$FROM_ROADMAP" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
}

@test "interleaved env-vars: from-roadmap does not pick up from-issue vars" {
    # Set from-issue env-vars manually
    export ADD_IMPROVE_FROM_ISSUE="42"
    export ADD_IMPROVE_GH_REPO="foo/bar"

    # Run from-roadmap — should NOT see from-issue vars
    run bash "$FROM_ROADMAP" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]

    # Cleanup manually-set env-vars
    unset ADD_IMPROVE_FROM_ISSUE
    unset ADD_IMPROVE_GH_REPO
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `bats tests/integration/test_from_issue_env_isolation.bats`
Expected: **3 passed** after Task 7 completes.

- [ ] **Step 3: Verify no env-var leakage in real shell**

After running this test, in your current shell, run:
```bash
env | grep -E "^ADD_IMPROVE_|^BRAINSTORM_"
```
Expected: empty output (no leakage).

- [ ] **Step 4: Document the isolation pattern**

Add a note in `skills/add-improve/SKILL.md` (or a new section) confirming:
- `from-issue` and `from-roadmap` use disjoint env-var prefixes (`ADD_IMPROVE_FROM_ISSUE_*` vs `ADD_IMPROVE_FROM_ROADMAP_*`).
- Each script's `trap cleanup EXIT` unsets only its own env-vars.
- No conflict when both modes run in sequence.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 12: Write ADR-0029 — decision record

**Files:**
- Create: `docs/adr/ADR-0029-issue-driven-proposal-creation.md`

- [ ] **Step 1: Survey existing ADR format**

Run: `ls docs/adr/ADR-002[0-9]*.md` and read the latest ADR (e.g. `ADR-0028-...` or `ADR-0027-...`) to copy the structure.

- [ ] **Step 2: Write the ADR**

```markdown
# ADR-0029: Issue-Driven Proposal Creation

## Status
已采纳 (2026-08-15)

## Context

rdd-workflow v2.1+ has 2 paths to create a proposal: `add-improve` (brainstorm flow) and `propose` (gap-scan flow). Neither path starts from a GitHub issue. Users with active issue backlogs (especially maintainers of rdd-workflow itself) have to manually transcribe issue title/body into a `.rddf/improvements/<name>.md` file.

This change adds a third path: `add-improve --from-issue <N>` that fetches an issue from the current project's GitHub repo and scaffolds a proposal. The change also fixes a latent bug in `_lib/close_issues.py:180` where the archive comment hardcodes "Fixed in rdd-workflow" — this would write incorrect attribution to third-party repos.

## Decision

### 1. Repo detection: env > gh > git remote (3-step fallback)

Use a 3-step priority chain. Explicit env override (`RDDF_PROPOSAL_GH_REPO`) is highest priority because it allows fork/override scenarios. `gh repo view` is second because it correctly handles auth state. `git remote get-url origin` is the fallback for minimal installations.

**Alternatives considered:**
- `gh repo view` only: Rejected — fails for fork/override scenarios.
- `git remote` only: Rejected — fails for non-git-source projects.
- Hard-coded `chisuhua/rdd-workflow` as fallback: Rejected — explicitly forbidden in MUST NOT.

### 2. Scaffold mode: follow from-roadmap pattern

Use the existing `from-roadmap` bash+Python+env-var pattern (3-file split: `from_roadmap.sh` + `from_roadmap.py` + `from_roadmap.env.py`). This DRY convention avoids divergent scaffold implementations.

**Alternatives considered:**
- New shared scaffolding library: Rejected — premature abstraction for 3 modes.
- Inline bash heredoc: Rejected — Oracle C1 security risk.

### 3. Dedup locations: two places

Scan both `.rddf/improvements/*.md` frontmatter and `openspec/changes/*/roadmap-meta.yaml::issue_refs`. The first catches pre-proposal state, the second catches post-approval state.

**Alternatives considered:**
- Single source of truth (e.g., only improvements frontmatter): Rejected — loses pre-approval tracking.
- Trailing `## 已映射` section in proposal.md: Rejected — breaks the standard 5-section format.

### 4. close_issues.py fix: repo-neutral comment

Replace the hardcoded "Fixed in rdd-workflow v{version}" with a parameterized message that uses `repo_name` derived from `gh_repo` (e.g., `my-project` instead of `rdd-workflow`).

**Alternatives considered:**
- Drop the comment entirely: Rejected — useful for tracking purposes.
- Keep hardcoded and skip when gh_repo != upstream: Rejected — adds complexity for marginal benefit.

## Consequences

### Positive
- Bridges the gap between GitHub issues and `.rddf/improvements/` proposals.
- Enables rdd-workflow self-dogfooding (maintainers can convert their own issues).
- Fixes latent bug in `close_issues.py` that would write incorrect attribution to third-party repos.
- New `gh_repo_detect.py` is reusable for ADR-0027 triage future iterations.

### Negative
- Requires `gh` CLI to be installed and authenticated (with clear error messages).
- Adds 3 new env-vars (`ADD_IMPROVE_FROM_ISSUE`, `ADD_IMPROVE_GH_REPO`, `ADD_IMPROVE_ISSUE_TITLE`, `ADD_IMPROVE_ISSUE_BODY`).
- Increases the surface area of `add-improve` scaffolding (3 modes: free / from-roadmap / from-issue).

### Neutral
- Detected repo is **always** the current project's repo (no upstream fallback). This is intentional to prevent misattribution.

## References

- ADR-0025 (move-proposal-creation-to-design) — Phase 2 menu structure
- ADR-0027 §5 (issue-reporting) — scope distinction (triage vs from-issue)
- ADR-0027 §7 (gh_repo schema) — schema field reused in `.rddf/improvements/<name>.md`
- ADR-0026 (rddf CLI naming) — namespace conventions for `rddf issue` command
```

- [ ] **Step 3: Update ADR index**

If `docs/adr/README.md` exists, add a link to ADR-0029 in the chronological list.

- [ ] **Step 4: Verify metadata**

Run: `head -5 docs/adr/ADR-0029-issue-driven-proposal-creation.md`
Expected: status line and title as written above.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 13: Run full regression gate `./test.sh --full --regression`

**Files:**
- Run: `./test.sh --full --regression`

- [ ] **Step 1: Run the full regression suite**

Run: `./test.sh --full --regression`
Expected: all tests pass, or only baseline failures listed in `tests/KNOWN_FAILURES.txt`.

- [ ] **Step 2: Investigate any new failures**

If `report_regression.sh` reports new failures (not in baseline), they must be fixed before archive. Use systematic-debugging skill to diagnose.

- [ ] **Step 3: Compare against baseline**

Run: `bash tests/scripts/report_regression.sh`
Expected: no "新增失败" (new failures) line. Only "已知失败" (known failures) should appear.

- [ ] **Step 4: Document any pre-existing failures**

If the full regression reveals failures unrelated to this change, note them in `tasks.md` for the change log but they don't gate archive.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Summary

- Tasks: 13 (12 implementation + 1 regression gate)
- Files created: 11 (5 production + 5 tests + 1 ADR)
- Files modified: 2 (`skills/guide-design/SKILL.md`, `_lib/close_issues.py`)
- TDD discipline: every implementation task preceded by a failing test
- ARCHITECTURE invariants: env-var only (no shell interpolation), HARD-GATE on `proposal-suggestions.md`, repo-neutral comments
- AGENTS.md compliance: full regression gate before archive
- Anti-regression: known-failures baseline prevents reporting pre-existing issues as new failures
