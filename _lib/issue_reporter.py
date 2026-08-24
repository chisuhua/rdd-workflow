"""Issue reporter core for ADR-0027.

5 public functions implementing the Detect → Buffer → Report loop:

- ``detect_issue`` sanitizes a payload via ``_lib/loop/sanitizer``
- ``write_issue_file`` persists a Markdown file under ``.rddf/issues/`` with
  a dedup-hash filename (see ``_lib/issue_dedup.py``)
- ``submit_issue_via_gh`` runs the L2 ``gh issue create`` path with a
  pre-submit dedup check (``gh issue list --search <hash>``)
- ``is_ci_environment`` detects 6 common CI markers and downgrades L2 → L1
- ``can_close_in_repo`` probes ``gh api repos/{owner}/{repo} --jq .permissions.push``
  to decide whether the reporter (or a fork owner) has write access

**Boundary (ADR-0027 §1.0)**: rdd-doctor is a static scanner for project-level
config/schema issues. Its findings are fixed in the third-party project —
this module MUST NOT be called from rdd-doctor. Doctor findings stay local;
reporter only fires for actual rdd-workflow bugs discovered at runtime
(post-flow-analysis or manual ``rddf report-issue``).

All subprocess calls are guarded by ``FileNotFoundError`` / ``TimeoutExpired``
so the reporter degrades gracefully on minimal environments (no ``gh``,
no network).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

# Import via canonical path (NOT the shim) per AGENTS.md
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from loop.sanitizer import sanitize  # type: ignore[import-not-found]
from issue_dedup import compute_dedup_hash  # type: ignore[import-not-found]


# ── Public dataclass ──────────────────────────────────────────────────────


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


@dataclass
class SubmitResult:
    success: bool
    submitted_url: Optional[str] = None
    error: Optional[str] = None


# ── 1. detect_issue ───────────────────────────────────────────────────────


def detect_issue(category: str, payload: dict) -> IssueResult:
    """Sanitize a payload dict and produce a ready-to-write IssueResult.

    Args:
        category: One of the ADR-0027 §1 categories (flow-bug, gate-failure, …).
        payload: ``{"description": str, "stack": list[str], "metadata": dict (optional)}``.
    """
    description = payload.get("description", "")
    stack = payload.get("stack", []) or []

    desc_result = sanitize(description)
    sanitized_stack = [sanitize(frame).sanitized_text for frame in stack[:5]]

    dedup_hash = compute_dedup_hash(
        category,
        description,
        stack[:3],
    )

    return IssueResult(
        category=category,
        sanitized_description=desc_result.sanitized_text,
        sanitized_stack=sanitized_stack,
        had_sensitive_data=desc_result.had_sensitive_data or any(
            sanitize(frame).had_sensitive_data for frame in stack[:5]
        ),
        dedup_hash=dedup_hash,
    )


# ── 2. write_issue_file ──────────────────────────────────────────────────


def write_issue_file(result: IssueResult, project_root: str) -> Path:
    """Persist the IssueResult to ``.rddf/issues/<category>-<hash>.md``.

    Idempotent: identical payloads produce identical filenames. Existing files
    are overwritten (the reporter is the only writer and it is the source of
    truth for the local buffer).
    """
    issues_dir = Path(project_root) / ".rddf" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    file_path = issues_dir / f"{result.category}-{result.dedup_hash}.md"
    body = _render_issue_body(result)
    file_path.write_text(body, encoding="utf-8")
    return file_path


def _render_issue_body(result: IssueResult) -> str:
    """Render the Markdown body (frontmatter + Reporter + details)."""
    frontmatter = {
        "category": result.category,
        "detected_at": result.detected_at,
        "rdd_workflow_version": result.rdd_workflow_version,
        "dedup_hash": result.dedup_hash,
        "submitted": False,
        "submitted_url": None,
    }
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
    if result.sanitized_stack:
        body += "\n## Stack trace / details\n\n"
        for frame in result.sanitized_stack:
            body += f"- `{frame}`\n"
    body += "\n## Reporter commit\n\n"
    body += f"rdd-workflow v{result.rdd_workflow_version}\n"
    return body


# ── 3. submit_issue_via_gh ───────────────────────────────────────────────


def submit_issue_via_gh(issue_file: Path, category: str, gh_repo: str) -> SubmitResult:
    """Run ``gh issue create`` with the auto-reported label set.

    Pre-check: queries ``gh issue list --search <dedup_hash>`` to avoid
    creating duplicate issues. If a matching open issue already exists,
    returns success with the existing URL (no new issue created).

    Degrades to L1 (returns success=False) when ``gh`` is missing or the
    subprocess fails — the local file is the durable record.
    """
    dedup_hash = _read_dedup_hash_from_file(issue_file)
    if dedup_hash:
        existing = _find_existing_issue(dedup_hash, gh_repo)
        if existing:
            return SubmitResult(success=True, submitted_url=existing)

    cmd = [
        "gh", "issue", "create",
        "--repo", gh_repo,
        "--label", f"auto-reported,{category},needs-triage",
        "--title", _extract_title(issue_file),
        "--body-file", str(issue_file),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return SubmitResult(success=False, error=str(e))

    if result.returncode == 0:
        url = result.stdout.strip().splitlines()[-1] if result.stdout else None
        return SubmitResult(success=True, submitted_url=url)

    return SubmitResult(success=False, error=result.stderr.strip())


def _read_dedup_hash_from_file(issue_file: Path) -> str:
    """Extract the ``dedup_hash`` from the issue file's frontmatter."""
    try:
        text = issue_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.startswith("dedup_hash:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def _find_existing_issue(dedup_hash: str, gh_repo: str) -> Optional[str]:
    """Query gh for an existing issue with this dedup_hash. Returns URL or None."""
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--repo", gh_repo,
                "--search", dedup_hash,
                "--state", "all",
                "--json", "url",
                "--limit", "1",
            ],
            capture_output=True, text=True, timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        items = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return None
    return items[0]["url"] if items else None


def _extract_title(issue_file: Path) -> str:
    """Extract the first non-frontmatter line as the issue title."""
    text = issue_file.read_text(encoding="utf-8")
    in_fm = False
    for line in text.splitlines():
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if in_fm:
            continue
        if line.strip():
            stripped = line.strip().lstrip("# ").strip()
            return stripped[:80]
    return "Issue from rdd-workflow reporter"


# ── 4. is_ci_environment ────────────────────────────────────────────────


_CI_MARKERS = ("CI", "GITHUB_ACTIONS", "JENKINS_URL", "BUILDKITE", "CIRCLECI", "GITLAB_CI")


def is_ci_environment() -> bool:
    """Return True if any of the 6 common CI markers is set to a truthy value."""
    for marker in _CI_MARKERS:
        if os.environ.get(marker):
            return True
    return False


# ── 5. should_auto_submit_gh_submission (single choke point) ─────────────


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


# ── 6. can_close_in_repo ────────────────────────────────────────────────


def can_close_in_repo(gh_repo: str) -> bool:
    """Probe whether the current ``gh`` auth has write access to ``gh_repo``.

    Used by the close hook to decide between auto-close (dogfooding / fork
    owner) and graceful degradation with a manual-close hint (third-party
    users reporting upstream).
    """
    try:
        result = subprocess.run(
            [
                "gh", "api", f"repos/{gh_repo}",
                "--jq", ".permissions.push",
            ],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"
