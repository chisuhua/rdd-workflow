#!/usr/bin/env python3
"""Auto-handle auto-reported rdd-workflow issues (L2 triage + proposal).

Discovers ``auto-reported`` open issues on a GitHub repo, applies a 3-gate
filter (label allowlist / repo allowlist / daily cap), then for each new
issue:

  1. Scaffolds a proposal via ``from_issue.write_scaffold``
     (``.rddf/improvements/<slug>-i<N>.md``)
  2. Registers a row in ``improvement-suggestions.md``
  3. Comments back on the issue with the proposal path + next steps
  4. Adds the ``triage-in-progress`` label

Designed to be run standalone (cron/CI) or from the GitHub Action
``.github/workflows/issue-auto-handler.yml``.

Oracle C1 safe: all subprocess arguments are static strings; issue
title/body travel through Python function args, never shell interpolation.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "skills" / "add-improve" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from from_issue import check_dedup, write_scaffold  # noqa: E402  (sys.path must be set first)

_STATE_SUBPATH = Path(".rddf") / "state" / ".issue-auto-handler.json"
_SUGGESTIONS_NAME = "improvement-suggestions.md"

_DEFAULT_LABEL = "auto-reported"
_DEFAULT_DAILY_MAX = 10
_LABEL_TRIAGED = "triage-in-progress"
_GH_TIMEOUT = 60


@dataclass
class GateResult:
    passed: bool
    reason: str = ""


@dataclass
class RunResult:
    processed: List[int] = field(default_factory=list)
    skipped: List[Dict[str, Any]] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)
    daily_remaining: int = 0


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _run_gh(args: List[str]) -> str:
    """Run a gh subcommand, returning stdout. Raises on non-zero exit."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        timeout=_GH_TIMEOUT,
        check=False,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or f"gh {args[0]} failed (rc={result.returncode})"
        raise RuntimeError(err)
    return result.stdout


def _load_state(project_root: Path) -> Dict[str, Any]:
    """Load run-state; resets daily counters when the date rolls over."""
    state_file = project_root / _STATE_SUBPATH
    if not state_file.is_file():
        return {"date": _today(), "processed": [], "skipped": []}
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}
    if data.get("date") != _today():
        data = {"date": _today(), "processed": [], "skipped": []}
    data.setdefault("processed", [])
    data.setdefault("skipped", [])
    return data


def _save_state(project_root: Path, data: Dict[str, Any]) -> None:
    state_file = project_root / _STATE_SUBPATH
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _is_issue_already_handled(issue_num: int, project_root: Path) -> bool:
    """Dedup against existing proposal files / roadmap-meta refs."""
    return bool(check_dedup(issue_num, project_root))


def _register_suggestion(project_root: Path, proposal_name: str, issue_num: int, gh_repo: str) -> None:
    """Append a row to improvement-suggestions.md if not already present."""
    suggestions_file = project_root / _SUGGESTIONS_NAME
    if not suggestions_file.is_file():
        return
    link = f"[{proposal_name}](.rddf/improvements/{proposal_name}.md)"
    if link in suggestions_file.read_text(encoding="utf-8"):
        return
    row = (
        f"| {link} | P1 | auto-handler from-issue ({gh_repo}#{issue_num}) "
        f"| {_today()} | proposed (auto-handler) |\n"
    )
    with suggestions_file.open("a", encoding="utf-8") as fh:
        fh.write(row)


def _post_comment(issue_num: int, gh_repo: str, proposal_name: str) -> None:
    body = (
        "🤖 **Auto-handled by rdd-workflow issue-auto-handler**\n\n"
        f"- Proposal scaffold: `.rddf/improvements/{proposal_name}.md`\n"
        "- Status: `proposed` — requires human review before implementation\n"
        "- Next: run `rdd-planner` to review + approve, then `rdd-builder` to execute\n\n"
        f"_Source issue: {gh_repo}#{issue_num} (auto-reported)_"
    )
    _run_gh(["issue", "comment", str(issue_num), "--repo", gh_repo, "--body", body])


def _add_triage_label(issue_num: int, gh_repo: str) -> None:
    _run_gh(["issue", "edit", str(issue_num), "--repo", gh_repo, "--add-label", _LABEL_TRIAGED])


def _fetch_open_reported(repo: str, label: str) -> List[Dict[str, Any]]:
    """List open issues with the given label, oldest first."""
    raw = _run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--label",
            label,
            "--state",
            "open",
            "--json",
            "number,title,body,labels,url,createdAt",
            "--limit",
            "100",
        ]
    )
    issues = json.loads(raw)
    return sorted(issues, key=lambda i: i["number"])


def _gate_allowlist(repo: str, allowlist: str) -> GateResult:
    """G2: repo allowlist — only process explicitly-listed repos."""
    if not allowlist:
        return GateResult(False, "allowlist empty")
    allowed = {item.strip() for item in allowlist.split(",") if item.strip()}
    if repo in allowed:
        return GateResult(True)
    return GateResult(False, f"repo {repo} not in allowlist")


def _gate_daily_cap(processed_today: int, daily_max: int) -> GateResult:
    """G3: daily cap — stop processing once the cap is hit."""
    if processed_today < daily_max:
        return GateResult(True)
    return GateResult(False, f"daily cap {daily_max} reached")


def _handle_issue(issue: Dict[str, Any], gh_repo: str, project_root: Path) -> Path:
    """Create proposal + register + comment + label. Returns proposal file."""
    issue_num = int(issue["number"])
    title = issue.get("title", f"issue-{issue_num}")
    body = issue.get("body") or ""

    proposal_file = write_scaffold(
        project_root=project_root,
        issue_num=issue_num,
        gh_repo=gh_repo,
        title=title,
        body=body,
    )
    proposal_name = proposal_file.stem
    _register_suggestion(project_root, proposal_name, issue_num, gh_repo)
    _post_comment(issue_num, gh_repo, proposal_name)
    _add_triage_label(issue_num, gh_repo)
    return proposal_file


def run(
    *,
    repo: str,
    project_root: Path,
    label: str = _DEFAULT_LABEL,
    allowlist: str = "",
    daily_max: int = _DEFAULT_DAILY_MAX,
    dry_run: bool = False,
) -> RunResult:
    """Execute the auto-handler pipeline, returning results."""
    result = RunResult()
    state = _load_state(project_root)

    gate2 = _gate_allowlist(repo, allowlist)
    if not gate2.passed:
        result.failed.append({"issue": "*", "reason": f"G2-repo-allowlist: {gate2.reason}"})
        return result

    issues = _fetch_open_reported(repo, label)
    for issue in issues:
        num = int(issue["number"])

        gate3 = _gate_daily_cap(len(state["processed"]), daily_max)
        if not gate3.passed:
            result.skipped.append({"issue": num, "reason": gate3.reason})
            continue

        if num in state["processed"]:
            result.skipped.append({"issue": num, "reason": "already processed today"})
            continue

        if _is_issue_already_handled(num, project_root):
            result.skipped.append({"issue": num, "reason": "proposal already exists"})
            state["skipped"].append(num)
            continue

        if dry_run:
            result.processed.append(num)
            state["processed"].append(num)
            continue

        try:
            proposal_file = _handle_issue(issue, repo, project_root)
            result.processed.append(num)
            state["processed"].append(num)
            print(f"✅ #{num} → {proposal_file.relative_to(project_root)}")
        except (RuntimeError, OSError, ValueError) as exc:
            result.failed.append({"issue": num, "reason": str(exc)})
            print(f"❌ #{num} failed: {exc}", file=sys.stderr)
            continue

    result.daily_remaining = max(0, daily_max - len(state["processed"]))
    if not dry_run:
        _save_state(project_root, state)
    return result


def _emit_json(result: RunResult) -> None:
    print(json.dumps({
        "processed": result.processed,
        "skipped": result.skipped,
        "failed": result.failed,
        "daily_remaining": result.daily_remaining,
    }, ensure_ascii=False, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="issue-auto-handler",
        description="Auto-triage + auto-proposal for auto-reported rdd-workflow issues.",
    )
    parser.add_argument("--repo", required=True, help="owner/repo to scan")
    parser.add_argument(
        "--project-root",
        default=str(_REPO_ROOT),
        help="rdd-workflow checkout root (default: repo root)",
    )
    parser.add_argument("--label", default=_DEFAULT_LABEL, help="label filter (default: auto-reported)")
    parser.add_argument(
        "--allowlist",
        default=os.environ.get("ISSUE_HANDLER_ALLOWLIST", ""),
        help="comma-separated repo allowlist (default: env ISSUE_HANDLER_ALLOWLIST)",
    )
    parser.add_argument(
        "--daily-max",
        type=int,
        default=int(os.environ.get("ISSUE_HANDLER_DAILY_MAX", str(_DEFAULT_DAILY_MAX))),
        help="max issues processed per day (default: env / 10)",
    )
    parser.add_argument("--dry-run", action="store_true", help="discover + gate only, no writes")
    parser.add_argument("--json", dest="json_out", action="store_true", help="emit JSON summary")
    args = parser.parse_args(argv)

    result = run(
        repo=args.repo,
        project_root=Path(args.project_root),
        label=args.label,
        allowlist=args.allowlist,
        daily_max=args.daily_max,
        dry_run=args.dry_run,
    )

    if args.json_out:
        _emit_json(result)
    else:
        print(
            f"processed={len(result.processed)} skipped={len(result.skipped)} "
            f"failed={len(result.failed)} daily_remaining={result.daily_remaining}"
        )

    return 1 if result.failed else 0


if __name__ == "__main__":
    sys.exit(main())