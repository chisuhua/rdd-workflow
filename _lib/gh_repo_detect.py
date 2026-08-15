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