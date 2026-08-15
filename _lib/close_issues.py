"""Close hook for ADR-0027: close linked GitHub issues on change archive.

Called by ``_lib/archive.sh`` (worktree mode) and
``skills/guide-ship/scripts/ship_archive.sh`` (lightweight mode) after a
successful ``openspec archive``. Reads ``issue_refs`` from
``openspec/changes/<name>/roadmap-meta.yaml``, probes write permission
on the target repo, then closes each issue with a comment linking to the
fixed change. Idempotent (skips already-closed issues) and failure-tolerant
(the archive main flow is never blocked by a close-hook failure).
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a hard dep
    yaml = None  # type: ignore[assignment]


_GH_TIMEOUT_SECONDS = 15
_RETENTION_DAYS_DEFAULT = 30


@dataclass
class CloseResult:
    closed: List[int]
    skipped: List[int]
    manual_links: List[tuple]  # (issue_num, url) when no push permission
    errors: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


# ── Public API ────────────────────────────────────────────────────────────


def close_issues_for_change(
    change_name: str,
    project_root: str = ".",
    new_version: str = "next",
) -> CloseResult:
    """Close every issue linked from the change's ``roadmap-meta.yaml``.

    Steps:
        1. Parse ``openspec/changes/<name>/roadmap-meta.yaml`` for ``issue_refs``.
        2. If empty, return an empty result (no-op).
        3. Probe ``can_close_in_repo(gh_repo)`` — degrade to manual-close hint
           if the current ``gh`` auth lacks push permission.
        4. For each ref: skip if already CLOSED, otherwise close + comment.
        5. Update local issue files' ``submitted_url`` field to record closure.
        6. Prune old closed issues per ``retention_days`` config (default 30).
    """
    result = CloseResult(closed=[], skipped=[], manual_links=[], errors=[])

    if os.environ.get("RDDF_REPORT_CLOSE_ON_ARCHIVE", "yes").lower() in ("0", "false", "no", "off"):
        return result

    refs, gh_repo = _load_issue_refs(change_name, project_root)
    if not refs:
        return result

    if not _can_close_in_repo(gh_repo):
        for ref in refs:
            result.manual_links.append((ref, f"https://github.com/{gh_repo}/issues/{ref}"))
        return result

    short_sha = _git_short_sha(project_root)
    for ref in refs:
        try:
            state = _get_issue_state(ref, gh_repo)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            result.errors.append(f"state check #{ref}: {e}")
            continue
        if state == "CLOSED":
            result.skipped.append(ref)
            continue
        try:
            _close_issue(ref, gh_repo, change_name, new_version, short_sha)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            result.errors.append(f"close #{ref}: {e}")
            continue
        result.closed.append(ref)

    _update_local_issue_files(refs, project_root, result)
    _prune_old_issues(project_root, retention_days=_get_retention_days())
    return result


def prune_old_issues(project_root: str = ".", retention_days: int = _RETENTION_DAYS_DEFAULT) -> int:
    """Delete local issue files where ``closed_at`` is older than ``retention_days``.

    Returns the number of files removed. Files without ``closed_at`` (i.e.
    not yet submitted/closed) are NEVER deleted — the reporter is the only
    source of truth for unsubmitted issues and we must not lose user data.
    """
    issues_dir = Path(project_root) / ".rddf" / "issues"
    if not issues_dir.is_dir():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86400
    removed = 0
    for path in issues_dir.glob("*.md"):
        if _is_old_closed(path, cutoff):
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def can_close_in_repo(gh_repo: str) -> bool:
    """Public probe — re-export of the one in issue_reporter for convenience."""
    from issue_reporter import can_close_in_repo as _impl
    return _impl(gh_repo)


# ── Internals ─────────────────────────────────────────────────────────────


def _load_issue_refs(change_name: str, project_root: str) -> tuple:
    """Read ``openspec/changes/<name>/roadmap-meta.yaml`` for issue_refs + gh_repo."""
    if yaml is None:
        return [], "chisuhua/rdd-workflow"
    meta_path = Path(project_root) / "openspec" / "changes" / change_name / "roadmap-meta.yaml"
    if not meta_path.is_file():
        return [], "chisuhua/rdd-workflow"
    try:
        data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return [], "chisuhua/rdd-workflow"
    refs = data.get("issue_refs") or []
    if not isinstance(refs, list):
        refs = []
    gh_repo = data.get("gh_repo") or "chisuhua/rdd-workflow"
    return [int(r) for r in refs if str(r).isdigit()], gh_repo


def _can_close_in_repo(gh_repo: str) -> bool:
    return can_close_in_repo(gh_repo)


def _git_short_sha(project_root: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=project_root,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def _get_issue_state(issue_num: int, gh_repo: str) -> str:
    """Return ``"OPEN"``, ``"CLOSED"``, or ``""`` (unknown / error)."""
    result = subprocess.run(
        [
            "gh", "issue", "view", str(issue_num),
            "--repo", gh_repo,
            "--json", "state", "-q", ".state",
        ],
        capture_output=True, text=True, timeout=_GH_TIMEOUT_SECONDS,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _close_issue(issue_num: int, gh_repo: str, change_name: str, new_version: str, short_sha: str) -> None:
    repo_name = gh_repo.split("/", 1)[1] if "/" in gh_repo else gh_repo
    comment = (
        f"✅ Fixed in {repo_name} v{new_version} via archive {short_sha}.\n\n"
        f"See: openspec/changes/{change_name}/\n"
    )
    subprocess.run(
        [
            "gh", "issue", "close", str(issue_num),
            "--repo", gh_repo,
            "--comment", comment,
        ],
        capture_output=True, text=True, timeout=_GH_TIMEOUT_SECONDS,
        check=True,
    )


def _update_local_issue_files(refs: List[int], project_root: str, result: CloseResult) -> None:
    """Mark the corresponding local issue files with the close outcome."""
    issues_dir = Path(project_root) / ".rddf" / "issues"
    if not issues_dir.is_dir():
        return
    closed_set = set(result.closed)
    skipped_set = set(result.skipped)
    for path in issues_dir.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for ref in refs:
            if f"dedup_hash: \"{ref}\"" not in text and f"dedup_hash: {ref}" not in text:
                continue
            if ref in closed_set or ref in skipped_set:
                _append_close_marker(path, text, ref)
            break


def _append_close_marker(path: Path, text: str, ref: int) -> None:
    """Append a ``closed_at`` field to the issue file's frontmatter (idempotent)."""
    if "closed_at:" in text:
        return
    timestamp = datetime.now(timezone.utc).isoformat()
    new_text = text.replace(
        "submitted_url: null",
        f'submitted_url: null\nclosed_at: "{timestamp}"\nclosed_ref: {ref}',
    )
    if new_text == text:
        new_text = text + f'\n<!-- closed_at: "{timestamp}" ref={ref} -->\n'
    try:
        path.write_text(new_text, encoding="utf-8")
    except OSError:
        pass


def _is_old_closed(path: Path, cutoff_ts: float) -> bool:
    """True if the file has ``closed_at`` older than cutoff."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "closed_at:" not in text:
        return False
    for line in text.splitlines():
        if line.startswith("closed_at:"):
            iso = line.split(":", 1)[1].strip().strip('"')
            try:
                ts = datetime.fromisoformat(iso).timestamp()
            except ValueError:
                return False
            return ts < cutoff_ts
    return False


def _prune_old_issues(project_root: str, retention_days: int) -> int:
    return prune_old_issues(project_root, retention_days=retention_days)


def _get_retention_days() -> int:
    raw = os.environ.get("RDDF_REPORT_RETENTION_DAYS", "").strip()
    if raw.isdigit():
        return int(raw)
    return _RETENTION_DAYS_DEFAULT
