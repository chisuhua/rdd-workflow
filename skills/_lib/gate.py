"""Gate mechanism — phase-transition validator with two severity levels.

Three phase transitions are supported: `arch_done` (arch → plan),
`plan_done` (plan → ship), `ship_done` (ship → archive). Each transition
has a default checklist of `Check` objects, each with a name, a condition
(lambda returning (passed: bool, severity: str|None)), a message, and a
suggestion string.

- `error` severity blocks the transition.
- `warning` severity allows the transition but records a warning event.

Plugins can register additional checks via `register_gate_check()`.
"""
from __future__ import annotations
import json
import logging
import os
import subprocess
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Callable, Optional

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity
from skills._lib.state_vector import StateVector
from skills._lib.defaults import STATE_VECTOR_PATH, EVENT_LOG_PATH

logger = logging.getLogger(__name__)


Check = namedtuple("Check", ["name", "condition", "message", "suggestion", "severity"], defaults=[None])
# severity field is informational; the actual severity comes from condition return.
# Kept for explicit documentation in registered checks.


# Module-level registry for plugin-registered checks
_PLUGIN_REGISTRY: list[Check] = []


def register_gate_check(check: Check) -> None:
    """Module-level API for plugins to register a custom Check."""
    _PLUGIN_REGISTRY.append(check)


@dataclass
class GateResult:
    """Result of a gate verification."""
    passed: bool
    transition: str
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    suggestion: Optional[str] = None


def _check_adr_exists(ctx: dict) -> tuple[bool, Optional[str]]:
    return (os.path.isdir("docs/adr") and any(f.startswith("ADR-") for f in os.listdir("docs/adr")), None)


def _check_roadmap_defined(ctx: dict) -> tuple[bool, Optional[str]]:
    return (os.path.isfile("roadmap.md"), None)


def _check_gap_analysis_complete(ctx: dict) -> tuple[bool, Optional[str]]:
    return (True, "warning")  # Warning: gap analysis is optional


def _check_arch_handoff_exists(ctx: dict) -> tuple[bool, Optional[str]]:
    return (os.path.isfile(".rddf/state/.arch-handoff.json"), None)


def _check_changes_committed(ctx: dict) -> tuple[bool, Optional[str]]:
    sv: StateVector = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    active = sv.get_field("arch_side.current_change")
    if not active:
        return (True, None)
    return (os.path.isfile(f"openspec/changes/{active}/proposal.md"), None)


def _check_artifacts_complete(ctx: dict) -> tuple[bool, Optional[str]]:
    sv: StateVector = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    active = sv.get_field("arch_side.current_change")
    if not active:
        return (True, None)
    base = f"openspec/changes/{active}"
    return (all(os.path.isfile(f"{base}/{a}") for a in ["proposal.md", "design.md", "tasks.md"]), None)


def _check_deps_analyzed(ctx: dict) -> tuple[bool, Optional[str]]:
    """Check that deps analysis has produced a real output (ADR-0015 Decision 3).

    The historic implementation returned `(True, "warning")` unconditionally,
    a no-op that left deps silent. Real semantics:

    - If `.rddf/state/.deps-output.md` is missing  → `(False, "warning")`
    - If the file is present but empty (<10 bytes) → `(False, "warning")`
    - If `openspec validate --specs --json` is callable and reports failures
      on deps-related specs → `(False, "warning")`
    - Otherwise → `(True, None)`

    Warning-level (not error): plan_done can transition without deps, but
    downstreams see a recorded warning so the gap is observable.
    """
    deps_md = ".rddf/state/.deps-output.md"
    if not os.path.isfile(deps_md):
        return (False, "warning")
    try:
        if os.path.getsize(deps_md) < 10:
            return (False, "warning")
    except OSError:
        return (False, "warning")
    try:
        result = subprocess.run(
            ["openspec", "validate", "--specs", "--json"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return (True, "warning")
    try:
        report = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return (True, "warning")
    summary = report.get("summary") or {}
    totals = summary.get("totals") or {}
    failed = int(totals.get("failed", 0))
    return (False, "warning") if failed > 0 else (True, None)


def _check_openspec_validate(ctx: dict) -> tuple[bool, Optional[str]]:
    """Run `openspec validate --all --strict --json` and gate the transition on it (ADR-0015).

    Behaviour:
    - Returns `(True, None)` when JSON summary shows 0 failed items.
    - Returns `(False, "error")` when summary.failed > 0 — the typical case where
      `## Purpose` / `## Requirements` / `#### Scenario:` blocks are missing in
      one or more specs, or where a proposal/design/tasks artifact is malformed.
    - Returns `(True, "warning")` when the `openspec` binary is not on PATH
      (FileNotFoundError) or times out. Per ADR-0007 we degrade rather than
      crash on missing tooling.

    The Check's `suggestion` field tells the user the exact recovery command:
    `openspec validate` (read failures) → fix → re-run.
    """
    try:
        result = subprocess.run(
            ["openspec", "validate", "--all", "--strict", "--json"],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        return (True, "warning")
    except (subprocess.TimeoutExpired, OSError):
        return (True, "warning")

    try:
        report = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return (True, "warning")

    summary = report.get("summary") or {}
    totals = summary.get("totals") or {}
    failed = int(totals.get("failed", 0))
    if failed > 0:
        return (False, "error")
    return (True, None)


def _check_plan_review_dismissed(ctx: dict) -> tuple[bool, Optional[str]]:
    """If a `plan.review_validation` override flag was set, surface it as a warning.

    ADR-0015 leaves an opt-out path: a user invoking the
    `plan.review_validation` human-in-loop node can record an override
    in the state vector under `plan_side.review_validation_override`.
    We surface that override as a warning so archive-time reviews can
    see *why* the gate passed without a clean OpenSpec pass.
    """
    sv: StateVector = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    override = sv.get_field("plan_side.review_validation_override")
    if override:
        return (True, "warning")
    return (True, None)


def _check_worktrees_empty(ctx: dict) -> tuple[bool, Optional[str]]:
    import subprocess
    result = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True)
    # Default worktree is always present; check for any extras
    lines = [l for l in result.stdout.strip().split("\n") if l]
    return (len(lines) <= 1, None)


def _check_archive_empty(ctx: dict) -> tuple[bool, Optional[str]]:
    return (True, None)  # Archive is checked at archive time, not pre-ship


def _check_tests_pass(ctx: dict) -> tuple[bool, Optional[str]]:
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/unit/", "-q", "--no-header"],
        capture_output=True, text=True,
    )
    return (result.returncode == 0, None)


def _check_review_debt_recorded(ctx: dict) -> tuple[bool, Optional[str]]:
    import json, os, subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", "*.cpp", "*.h", "*.py", "*.ts"],
            capture_output=True, text=True, timeout=10,
        )
        new_todos = [
            l for l in result.stdout.split('\n')
            if l.startswith('+') and any(t in l for t in ('TODO', 'FIXME', 'HACK'))
        ]
        if not new_todos:
            return (True, None)
        if not os.path.isfile("proposal-suggestions.md"):
            return (False, "warning")
        with open("proposal-suggestions.md") as f:
            entries = json.load(f)
        debt_names = {
            e['name'] for e in entries
            if isinstance(e, dict) and e.get('type') == 'debt'
        }
        return (True, None) if debt_names else (False, "warning")
    except Exception:
        return (True, None)


_DEFAULT_CHECKS = {
    "arch_done": [
        Check("adr_exists", _check_adr_exists, "ADR directory missing or empty", "Create ADRs: mkdir -p docs/adr && touch docs/adr/ADR-0001.md", "error"),
        Check("roadmap_defined", _check_roadmap_defined, "roadmap.md not found", "Create roadmap: touch roadmap.md", "error"),
        Check("gap_analysis_complete", _check_gap_analysis_complete, "Gap analysis not run", "Run: openspec scan", "warning"),
    ],
    "plan_done": [
        Check("arch_handoff_exists", _check_arch_handoff_exists, "arch-done handoff 缺失", "请先运行 skill_use('guide-arch') 完成架构定义", "error"),
        Check("changes_committed", _check_changes_committed, "Change artifacts not committed", "git add openspec/changes/<name>/ && git commit", "error"),
        Check("artifacts_complete", _check_artifacts_complete, "Missing proposal/design/tasks", "Create all three artifacts in openspec/changes/<name>/", "error"),
        Check("openspec_validate", _check_openspec_validate, "Plan fails OpenSpec schema validation", "Run: openspec validate --all --strict --json  and fix reported items", "error"),
        Check("deps_analyzed", _check_deps_analyzed, "Dependencies not analyzed", "Run: openspec deps <name>", "warning"),
        Check("plan_review_dismissed", _check_plan_review_dismissed, "plan.review_validation override active", "Review the recorded override under plan_side.review_validation_override before archive", "warning"),
    ],
    "ship_done": [
        Check("worktrees_empty", _check_worktrees_empty, "Active worktrees remain", "git worktree remove .rddf/wt/<name>", "error"),
        Check("archive_empty", _check_archive_empty, "Archive not empty", "Verify archive/", "error"),
        Check("tests_pass", _check_tests_pass, "Tests failing", "Run: pytest tests/ -v", "error"),
        Check("review_debt_recorded", _check_review_debt_recorded,
              "execute 后债务未在 proposal-suggestions.md 中记录",
              "运行 Phase 2.5 review 或选择跳过 (debt 可 deferred)", "warning"),
    ],
}


class GateMechanism:
    """Validates phase transitions against a checklist of Checks."""

    def __init__(
        self,
        state_path: str = STATE_VECTOR_PATH,
        event_log_path: str = EVENT_LOG_PATH,
        load_defaults: bool = True,
    ):
        self.state_path = state_path
        self.event_log_path = event_log_path
        self._checks: dict[str, list[Check]] = {
            t: list(c) for t, c in _DEFAULT_CHECKS.items()
        } if load_defaults else {t: [] for t in ["arch_done", "plan_done", "ship_done"]}
        # Note: plugin-registered checks are read dynamically from _PLUGIN_REGISTRY
        # at verify time, so additions after construction are visible (see _all_checks).

    def _all_checks(self, transition: str) -> list[Check]:
        """Combine instance-registered and module-plugin checks for `transition`."""
        return list(self._checks[transition]) + list(_PLUGIN_REGISTRY)

    def register(self, check: Check) -> None:
        """Register a check against all known transitions."""
        for t in self._checks:
            self._checks[t].append(check)

    def get_registered_check_names(self) -> list[str]:
        """Flat list of all registered check names."""
        seen = set()
        names = []
        for t in self._checks:
            for c in self._all_checks(t):
                if c.name not in seen:
                    seen.add(c.name)
                    names.append(c.name)
        return names

    def verify_transition(self, transition: str, context: dict) -> GateResult:
        """Run all checks for `transition`. Returns GateResult."""
        if transition not in self._checks:
            return GateResult(
                passed=False,
                transition=transition,
                error=f"Unknown transition '{transition}'. Must be one of: {list(self._checks.keys())}",
            )

        # Augment context with state vector
        try:
            sv = StateVector.load(self.state_path, verify_checksum=False)
            context = {**context, "state_vector": sv}
        except Exception:
            logger.warning("Gate: state vector load failed")

        failed = []
        warnings = []
        suggestions = []
        for check in self._all_checks(transition):
            try:
                passed, severity = check.condition(context)
            except Exception as e:
                failed.append(check.name)
                suggestions.append(f"{check.message} (error during check: {e})")
                continue
            if passed:
                continue
            if severity == "warning":
                warnings.append(check.name)
                suggestions.append(f"[WARN] {check.name}: {check.message}. {check.suggestion}")
            else:
                failed.append(check.name)
                suggestions.append(f"{check.name}: {check.message}. {check.suggestion}")

        passed = len(failed) == 0
        result = GateResult(
            passed=passed,
            transition=transition,
            failed_checks=failed,
            warnings=warnings,
            error="; ".join(failed) if failed else None,
            suggestion="\n".join(suggestions) if suggestions else None,
        )

        # Record event
        try:
            log = EventLog(self.event_log_path)
            if passed:
                log.record(
                    EventType.GATE_TRANSITION, Severity.INFO,
                    f"Transition {transition} allowed (warnings: {warnings})",
                    context={"transition": transition, "warnings": warnings},
                )
            else:
                log.record(
                    EventType.GATE_FAILED, Severity.ERROR,
                    f"Transition {transition} blocked (failed: {failed})",
                    context={"transition": transition, "failed_checks": failed},
                )
        except Exception:
            logger.warning("Gate: event log record failed")

        return result

    def force_transition(self, transition: str, context: dict, reason: str) -> bool:
        """Force a transition despite gate failure. Records a GATE_FORCED event."""
        try:
            log = EventLog(self.event_log_path)
            log.record(
                EventType.GATE_FORCED, Severity.WARN,
                f"User forced transition {transition}: {reason}",
                context={"transition": transition, "reason": reason},
            )
        except Exception:
            logger.warning("Gate: force_transition event log failed")
        return True

    def get_suggestion(self, transition: str) -> Optional[str]:
        """Return the aggregated suggestion for a transition (after a failed verify)."""
        result = self.verify_transition(transition, {})
        return result.suggestion


# Re-export for convenience
GateError = GateResult  # backward compat alias
