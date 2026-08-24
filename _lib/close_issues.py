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
    """Read ``roadmap-meta.yaml`` for ``issue_refs`` + ``gh_repo``.

    **ADR-0027 §6 / fix-adr-0027-close-hook-dead-code**: try the active
    path first (pre-archive layout: ``openspec/changes/<name>/``). If
    not found, fall back to the post-archive layout. ``openspec
    archive`` moves files to ``archive/<YYYY-MM-DD>-<name>/`` where
    the date is the archive day. We glob the archive dir for any
    ``<date>-<name>`` entry — the change_name suffix is the stable
    identifier since dates are dynamic.

    Returns ``([], "chisuhua/rdd-workflow")`` when neither path exists
    (safe no-op for changes without a roadmap-meta.yaml).
    """
    if yaml is None:
        return [], "chisuhua/rdd-workflow"
    base = Path(project_root) / "openspec" / "changes"

    # Candidate paths in priority order: active > post-archive (date-prefixed)
    candidates = [
        base / change_name / "roadmap-meta.yaml",
    ]
    # Find any archive/<date>-<name>/roadmap-meta.yaml whose suffix matches
    archive_base = base / "archive"
    if archive_base.is_dir():
        for child in archive_base.iterdir():
            if child.is_dir() and child.name.endswith(f"-{change_name}"):
                candidates.append(child / "roadmap-meta.yaml")

    for meta_path in candidates:
        if not meta_path.is_file():
            continue
        try:
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        refs = data.get("issue_refs") or []
        if not isinstance(refs, list):
            refs = []
        gh_repo = data.get("gh_repo") or "chisuhua/rdd-workflow"
        return [int(r) for r in refs if str(r).isdigit()], gh_repo

    return [], "chisuhua/rdd-workflow"


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
    """Mark the corresponding local issue files with the close outcome.

    **fix-adr-0027-close-hook-dead-code**: matches a local issue file
    to ``refs`` by scanning its ``submitted_url`` for ``/issues/<n>``
    (not by ``dedup_hash``, which is 8-hex and never collides with the
    integer issue number).
    """
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
            # Matches by submitted_url containing /issues/<n> (G2 fix, primary),
            # with a dedup_hash-equality fallback for legacy local files that
            # pre-date submitted_url (submitted_url: null).
            if (
                f"/issues/{ref}" not in text
                and f"dedup_hash: \"{ref}\"" not in text
                and f"dedup_hash: {ref}" not in text
            ):
                continue
            if ref in closed_set or ref in skipped_set:
                _append_close_marker(path, text, ref)
            break


def _append_close_marker(path: Path, text: str, ref: int) -> None:
    """Mark a local issue file with the close outcome (idempotent).

    **fix-adr-0027-close-hook-dead-code**: inject ``closed_at`` +
    ``closed_ref`` into the YAML frontmatter right after the
    ``submitted_url`` line, whether the URL is null or a real value.
    Keeps the marker inside the frontmatter so ``_is_old_closed`` can
    prune it later. Files without a frontmatter get a trailing HTML
    comment as a fallback.
    """
    if "closed_at:" in text:
        return
    timestamp = datetime.now(timezone.utc).isoformat()
    marker = f'closed_at: "{timestamp}"\nclosed_ref: {ref}'
    if "submitted_url:" in text:
        lines = text.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.lstrip().startswith("submitted_url:"):
                lines.insert(i + 1, marker + "\n")
                break
        new_text = "".join(lines)
    else:
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
