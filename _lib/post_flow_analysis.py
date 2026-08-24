"""Post-flow-analysis classifier for ADR-0027 §1.2.

Three-way classification of phase outcomes:

    1. usage-error      — user did something wrong (bad arg, missing flag)
    2. environment-error — missing tool / network / permission / disk
    3. flow-bug         — rdd-workflow itself is buggy (default fail-open)

Excludes exit codes 130/143 (SIGINT/SIGTERM — user cancellation, not a bug).
report_flow_bug writes a local issue file only for flow-bug classifications.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from issue_reporter import detect_issue, write_issue_file, is_ci_environment  # type: ignore[import-not-found]


# ── Constants ────────────────────────────────────────────────────────────

ROOT_CAUSE_USAGE = "usage-error"
ROOT_CAUSE_ENV = "environment-error"
ROOT_CAUSE_FLOW = "flow-bug"

REPORT_CATEGORY_FLOW = "flow-bug"
REPORT_CATEGORY_GATE = "gate-failure"
REPORT_CATEGORY_CRASH = "phase-crash"

USER_HINTS = {
    ROOT_CAUSE_USAGE: "用法错误：检查参数。运行 'rddf <cmd> --help' 或参考 skills/<skill>/SKILL.md。",
    ROOT_CAUSE_ENV: "环境问题：检查工具安装 / 网络 / 权限 / 磁盘空间。本地诊断: 'rddf doctor'。",
    ROOT_CAUSE_FLOW: "已记录到 .rddf/issues/（flow-bug）。",
}

# ── Pattern tables ──────────────────────────────────────────────────────

_USAGE_PATTERNS: list[Tuple[str, re.Pattern]] = [
    (
        "U1",
        re.compile(
            r"usage: .*\[-"
            r"|error: (unrecognized arguments|argument .*(is required|invalid|expected))"
            r"|argparse\.ArgumentError",
            re.I,
        ),
    ),
    ("U4", re.compile(r"(run \S+ first|missing required (argument|flag)|先执行)", re.I)),
]

_ENV_PATTERNS: list[Tuple[str, re.Pattern]] = [
    (
        "E1",
        re.compile(r"command not found|No such file or directory.*\b(gh|git|openspec|bats|python3)\b", re.I),
    ),
    ("E2", re.compile(r"Permission denied")),
    ("E3", re.compile(r"Could not resolve host|Connection (refused|timed out)|network is unreachable", re.I)),
    ("E4", re.compile(r"No space left on device")),
    (
        "E5",
        re.compile(r"(requires|需要).*(version|版本).*(openspec|git|python|bats)", re.I),
    ),
]

_FLOW_FRAMES = re.compile(r'File "([^"]*(?:_lib|skills)/[^"]*\.py)"', re.MULTILINE)
_STDLIB_FRAMES = re.compile(
    r'File "([^"]*(?:/usr/lib/python|/usr/local/lib/python)[^"]*/[^"]+\.py)"',
    re.MULTILINE,
)
_TRACEBACK_START = re.compile(r"Traceback \(most recent call last\):", re.MULTILINE)
_STATE_VIOLATION = re.compile(
    r"(invalid state|unexpected (status|phase)|状态机|state machine)",
    re.I,
)


# ── ADR-0027 §1.2 classifier regex set (evaluation order: F4 > F1 > F2 > F3) ──

_RE_F4_GATE_RAISED = re.compile(
    r"(?:gate raised|_check_\w+.*raised|GateFailure)"
)
_RE_F1_TRACEBACK_IN_LIB = re.compile(
    r"Traceback.*(?:skills/_lib/|_lib/)", re.DOTALL
)
_RE_F2_CONFIG_ERROR = re.compile(r"Config(?:Error| validation failed)")
_RE_F3_INVALID_STATE = re.compile(
    r"(?:invalid state|unexpected (?:status|phase)|状态机|state machine)",
    re.I,
)


def _classify_failure_pattern(stderr: str) -> tuple[str, str, str] | None:
    """Return ``(category, skill_invoked, matched_rule)`` for an F1-F4 match.

    First match wins; gate-raised (F4) beats a generic traceback (F1).
    Returns ``None`` so the caller falls back to default fail-open.
    """
    if _RE_F4_GATE_RAISED.search(stderr):
        return REPORT_CATEGORY_GATE, "gate-system", "F4"
    if _RE_F1_TRACEBACK_IN_LIB.search(stderr):
        return REPORT_CATEGORY_CRASH, "post-flow-analysis", "F1"
    if _RE_F2_CONFIG_ERROR.search(stderr):
        return REPORT_CATEGORY_GATE, "post-flow-analysis", "F2"
    if _RE_F3_INVALID_STATE.search(stderr):
        return REPORT_CATEGORY_FLOW, "post-flow-analysis", "F3"
    return None


# ── Dataclasses ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PhaseOutcome:
    """Raw inputs to the classifier from a single phase execution."""

    phase: str
    exit_code: int
    stderr: str = ""
    stdout_tail: str = ""
    traceback: str = ""


@dataclass(frozen=True)
class Classification:
    """Outcome of :func:`classify_phase_outcome`."""

    root_cause: str
    report_category: Optional[str]
    matched_rule: str
    description: str
    stack: Tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)
    should_report: bool = False
    user_hint: str = ""


# ── Classification ─────────────────────────────────────────────────────


def classify_phase_outcome(phase: str, outcome: PhaseOutcome) -> Classification:
    """Three-way classification with fail-open default to flow-bug."""
    if outcome.exit_code == 0:
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=None,
            matched_rule="OK",
            description="",
            should_report=False,
        )

    if outcome.exit_code in (130, 143):
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=None,
            matched_rule="SIGINT-EXCLUDED",
            description="user cancelled (SIGINT/SIGTERM)",
            should_report=False,
        )

    text = f"{outcome.stderr}\n{outcome.stdout_tail}\n{outcome.traceback}"

    # [1] usage-error (specific patterns first, then CLI fallback, then stdlib-only traceback)
    for rule, pat in _USAGE_PATTERNS:
        m = pat.search(text)
        if m:
            return _classify_usage(rule, m.group(0)[:200], phase, outcome)
    if outcome.exit_code == 2 and _looks_like_cli_invocation(text):
        return _classify_usage("U2/U3", text, phase, outcome)
    if _TRACEBACK_START.search(text) and _STDLIB_FRAMES_ONLY(_extract_stack_frames(text)):
        return _classify_usage(
            "U5-stdlib-traceback",
            "traceback in stdlib/argparse (not rdd-workflow code)",
            phase, outcome,
        )

    # [2] environment-error (PermissionError on project-internal paths → flow-bug)
    for rule, pat in _ENV_PATTERNS:
        m = pat.search(text)
        if m:
            if rule == "E2" and _permission_on_project_path(text, outcome):
                continue  # fall through to flow-bug
            return _classify_env(rule, m.group(0)[:200], phase, outcome)

    # [3] flow-bug
    return _classify_flow(phase, outcome, text)


def _looks_like_cli_invocation(text: str) -> bool:
    """Heuristic: text contains argparse-style output (usage line)."""
    return bool(re.search(r"^usage:\s", text, re.MULTILINE)) or "argparse.ArgumentError" in text


def _permission_on_project_path(text: str, outcome: PhaseOutcome) -> bool:
    """Return True if the 'Permission denied' path is inside the project tree."""
    m = re.search(r"Permission denied[:\s]+([^\s'\"]+)", text)
    if not m:
        return False
    path = m.group(1)
    try:
        return Path(path).resolve().is_relative_to(Path.cwd().resolve())
    except (OSError, ValueError):
        return False


def _classify_usage(rule: str, matched: str, phase: str, outcome: PhaseOutcome) -> Classification:
    return Classification(
        root_cause=ROOT_CAUSE_USAGE,
        report_category=None,
        matched_rule=rule,
        description=matched.strip(),
        metadata={"phase": phase, "exit_code": outcome.exit_code, "matched_rule": rule},
        should_report=False,
        user_hint=USER_HINTS[ROOT_CAUSE_USAGE],
    )


def _classify_env(rule: str, matched: str, phase: str, outcome: PhaseOutcome) -> Classification:
    missing_tool = None
    if rule == "E1":
        full_text = f"{outcome.stderr} {outcome.stdout_tail} {outcome.traceback}"
        m = re.search(r"\b(gh|git|openspec|bats|python3)\b", full_text)
        if m:
            missing_tool = m.group(1)
    return Classification(
        root_cause=ROOT_CAUSE_ENV,
        report_category=None,
        matched_rule=rule,
        description=matched.strip(),
        metadata={
            "phase": phase,
            "exit_code": outcome.exit_code,
            "matched_rule": rule,
            "missing_tool": missing_tool,
        },
        should_report=False,
        user_hint=USER_HINTS[ROOT_CAUSE_ENV],
    )


def _classify_flow(phase: str, outcome: PhaseOutcome, text: str) -> Classification:
    """Fine-grained flow-bug classification with default fail-open."""
    stack_frames = _extract_stack_frames(outcome.traceback or text)

    # ADR-0027 §1.2: F4 gate-raised > F1 traceback > F2 ConfigError > F3 invalid state
    match = _classify_failure_pattern(text)
    if match is not None:
        category, skill_invoked, matched_rule = match
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=category,
            matched_rule=matched_rule,
            description=_truncate(_last_stderr_line(outcome.stderr), 200),
            stack=stack_frames,
            metadata={
                "phase": phase,
                "exit_code": outcome.exit_code,
                "matched_rule": matched_rule,
                "skill_invoked": skill_invoked,
            },
            should_report=True,
            user_hint=USER_HINTS[ROOT_CAUSE_FLOW],
        )

    # Default fail-open
    return Classification(
        root_cause=ROOT_CAUSE_FLOW,
        report_category=REPORT_CATEGORY_FLOW,
        matched_rule="DEFAULT-FAIL-OPEN",
        description=_truncate(_last_stderr_line(outcome.stderr) or "phase failed with no stderr", 200),
        stack=stack_frames,
        metadata={"phase": phase, "exit_code": outcome.exit_code, "matched_rule": "DEFAULT-FAIL-OPEN"},
        should_report=True,
        user_hint=USER_HINTS[ROOT_CAUSE_FLOW],
    )


def _STDLIB_FRAMES_ONLY(stack_frames: Tuple[str, ...]) -> bool:
    """True if every captured frame path is in the Python stdlib (argparse etc.)."""
    return all("/python" in f and "/_lib" not in f and "/skills" not in f for f in stack_frames)


def _extract_stack_frames(text: str) -> Tuple[str, ...]:
    """Pull file paths from any 'File "..."' lines in the traceback."""
    return tuple(m.group(1) for m in _FLOW_FRAMES.finditer(text))[:5]


def _last_stderr_line(stderr: str) -> str:
    for line in reversed(stderr.splitlines()):
        line = line.strip()
        if line:
            return line
    return ""


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


# ── Report orchestration ────────────────────────────────────────────────


def report_flow_bug(
    classification: Classification,
    project_root: str = ".",
    config: Any = None,
) -> Optional[Path]:
    """Write a local issue file for flow-bug classifications only.

    If ``RDDF_REPORT_AUTO_SUBMIT=yes`` and not in CI, also submit to GitHub
    via ``submit_issue_via_gh`` and update the local file with the
    ``submitted_url``. The opt-in chain (master + auto_submit + per-category)
    is checked at the boundary so a misconfigured environment falls
    back to L1-only (no submission) rather than leaking issues.

    Returns the file path on success, or None if classification is not
    reportable (usage-error / environment-error / OK / SIGINT-excluded).
    """
    if not classification.should_report:
        return None
    if classification.report_category is None:
        return None

    result = detect_issue(
        classification.report_category,
        {
            "description": classification.description,
            "stack": list(classification.stack),
            "metadata": classification.metadata,
        },
    )
    file_path = write_issue_file(result, project_root=project_root)

    if _should_auto_submit(classification.report_category):
        from issue_reporter import submit_issue_via_gh  # local import to avoid cycles
        # Priority: config gh_repo > env var RDDF_REPORT_GH_REPO > upstream default
        gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
        if config is not None and isinstance(config, dict):
            config_gh_repo = config.get("reporting", {}).get("gh_repo")
            if config_gh_repo:
                gh_repo = config_gh_repo
        submit_result = submit_issue_via_gh(file_path, classification.report_category, gh_repo)
        if submit_result.success:
            _update_submission_status(file_path, submit_result.submitted_url or "")

    return file_path


def _should_auto_submit(category: str) -> bool:
    """Three-gate opt-in: master + auto_submit + per-category + not CI.

    Thin re-export of :func:`issue_reporter.should_auto_submit_gh_submission`
    (single choke point per ADR-0027 §3). Kept as a private alias for backward
    compatibility with the existing call site at line 327.
    """
    from issue_reporter import should_auto_submit_gh_submission
    return should_auto_submit_gh_submission(category)


def _update_submission_status(file_path: Path, submitted_url: str) -> None:
    """Update the issue file's frontmatter with submission result (idempotent)."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    text = text.replace("submitted: false", "submitted: true", 1)
    if "submitted_url: null" in text:
        text = text.replace(
            "submitted_url: null",
            f'submitted_url: "{submitted_url}"',
            1,
        )
    else:
        text = re.sub(
            r'submitted_url:\s*"[^"]*"',
            f'submitted_url: "{submitted_url}"',
            text,
            count=1,
        )
    try:
        file_path.write_text(text, encoding="utf-8")
    except OSError:
        pass


# ── Convenience: analyze-and-report from a file (used by bash trap) ────


def analyze_and_report(
    phase: str,
    exit_code: int,
    stderr_file: str,
    stdout_tail: str = "",
    project_root: str = ".",
) -> Classification:
    """Read stderr from file, classify, and (if flow-bug) write issue.

    Used by ``skills/_lib/post_flow_wrap.sh`` as the single entry point.
    Returns the Classification (for logging/UI hint).
    """
    try:
        with open(stderr_file, encoding="utf-8", errors="replace") as f:
            stderr = f.read()
    except OSError:
        stderr = ""
    try:
        with open(stdout_tail, encoding="utf-8", errors="replace") as f:
            stdout = f.read()
    except (OSError, TypeError):
        stdout = ""

    outcome = PhaseOutcome(
        phase=phase,
        exit_code=exit_code,
        stderr=stderr,
        stdout_tail=stdout[-2048:] if stdout else "",
    )
    classification = classify_phase_outcome(phase, outcome)

    if classification.should_report:
        report_flow_bug(classification, project_root=project_root)

    return classification


# ── CLI entry for bash invocation ──────────────────────────────────────


def _main(argv: list[str]) -> int:
    """Minimal CLI: ``python3 -m _lib.post_flow_analysis --phase P --exit-code N --stderr-file F [--project-root R]``."""
    import argparse
    parser = argparse.ArgumentParser(prog="post_flow_analysis")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--stderr-file", required=True)
    parser.add_argument("--stdout-file", default="")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv)

    cls = analyze_and_report(
        phase=args.phase,
        exit_code=args.exit_code,
        stderr_file=args.stderr_file,
        stdout_tail=args.stdout_file,
        project_root=args.project_root,
    )
    if cls.user_hint:
        print(f"[{cls.root_cause}] {cls.user_hint}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))


def analyze_phase_trace(
    trace_path: Optional[Path] = None,
    project_root: str = ".",
    phase: str = "unknown",
    exit_code: int = 0,
    stderr: str = "",
    stdout_tail: str = "",
) -> Optional[Classification]:
    """Classify a phase trace or direct stderr input.

    When ``trace_path`` is given, reads all subprocess events and
    synthesizes a ``PhaseOutcome`` for the first failing subprocess.
    When ``trace_path`` is None, uses the ``stderr``/``exit_code``
    parameters directly (unified path for consistency with the main
    classifier).

    Returns None for success paths (all subprocesses returned 0, or
    no pattern matched on the direct-input path).
    """
    if trace_path is None:
        # Direct-input path: unify with the main classifier.
        if exit_code == 0:
            return None
        match = _classify_failure_pattern(stderr)
        if match is None:
            return None
        category, skill_invoked, matched_rule = match
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=category,
            matched_rule=matched_rule,
            description=_truncate(_last_stderr_line(stderr), 200),
            stack=_extract_stack_frames(stderr),
            metadata={
                "phase": phase,
                "exit_code": exit_code,
                "matched_rule": matched_rule,
                "skill_invoked": skill_invoked,
            },
            should_report=True,
            user_hint=USER_HINTS[ROOT_CAUSE_FLOW],
        )

    events = _read_trace_events(trace_path)
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    if not subprocess_events:
        return None

    for event in subprocess_events:
        if event.get("returncode", 0) != 0:
            outcome = _outcome_from_event(event, project_root)
            return classify_phase_outcome(
                phase=os.environ.get("RDDF_PHASE", "unknown"),
                outcome=outcome,
            )

    text_blob = " ".join(
        e.get("stderr_tail", "") for e in subprocess_events
    )
    match = _classify_failure_pattern(text_blob)
    if match is not None:
        category, skill_invoked, matched_rule = match
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=category,
            matched_rule=f"{matched_rule}-cumulative",
            description="cumulative failure: "
            + _truncate(_last_stderr_line(text_blob), 200),
            stack=_extract_stack_frames(text_blob),
            metadata={
                "phase": "trace",
                "matched_rule": f"{matched_rule}-cumulative",
                "skill_invoked": skill_invoked,
            },
            should_report=True,
            user_hint=USER_HINTS.get(ROOT_CAUSE_FLOW, ""),
        )

    return None


def _read_trace_events(trace_path: Path) -> list[dict]:
    """Read events from a JSONL trace file. Tolerates missing/malformed lines."""
    events: list[dict] = []
    if not trace_path.is_file():
        return events
    try:
        with open(trace_path, encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return events


def _outcome_from_event(event: dict, project_root: str) -> PhaseOutcome:
    """Convert a subprocess trace event into a PhaseOutcome for classification."""
    return PhaseOutcome(
        phase=os.environ.get("RDDF_PHASE", "unknown"),
        exit_code=event.get("returncode", 0),
        stderr=event.get("stderr_tail", ""),
        stdout_tail=event.get("stdout_tail", ""),
        traceback="",
    )
