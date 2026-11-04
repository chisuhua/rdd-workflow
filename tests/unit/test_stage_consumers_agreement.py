"""Cross-consumer agreement for stage recommendation.

Three independent implementations decide "which stage should run next":

  1. ``skills/guide/scripts/scan-state.sh::scan_state``  (bash)
  2. ``_lib/cli/guide_cmd.py::_scan_state``                (python, CLI)
  3. ``_lib/workflow_synthesizer.py::_decision_tree``      (python, library)

The spec delta ``agent-interface-contracts`` requires them to agree on the
recommended STAGE for every v4 planner-handoff state. A drift between any
two of them makes the agent's stage detection non-deterministic — which is
exactly the defect class this change set out to remove.

The v3 states are deliberately NOT covered here: their behaviour is
pre-existing and a documented divergence (the bash/CLI consumers
cross-validate a stale v3 plan-handoff against the filesystem, the
synthesizer does not) is retained on purpose.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from skills._lib.cli.guide_cmd import _scan_state
from skills._lib.workflow_synthesizer import synthesize

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_STATE_SH = REPO_ROOT / "skills" / "guide" / "scripts" / "scan-state.sh"

ARCH_HANDOFF = {"version": 1, "adr_dir": "docs/adr", "discovered": True, "adr_count": 1}
PLANNER_HANDOFF = {
    "schema": "planner-handoff-v1",
    "version": 1,
    "owner": "rdd-planner",
    "planner_complete_at": "2026-01-01",
    "current_sprint": "sprint-1",
    "recommended_route": "full",
    "awaiting_builder": ["add-x"],
}


def _project(tmp_path: Path, handoffs: dict, active_change: bool = False) -> str:
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    for name, payload in handoffs.items():
        text = payload if isinstance(payload, str) else json.dumps(payload)
        (state / name).write_text(text, encoding="utf-8")
    if active_change:
        (tmp_path / "openspec" / "changes" / "add-x").mkdir(parents=True)
    return str(tmp_path)


def _bash_scan_state(project_root: str) -> tuple[str, str]:
    """Run the bash consumer and parse RECOMMEND / REASON."""
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f"source '{SCAN_STATE_SH}'; scan_state '{project_root}'; "
            'echo "RECOMMEND=$RECOMMEND"; echo "REASON=$REASON"',
        ],
        capture_output=True,
        text=True,
    )
    recommend = re.search(r"^RECOMMEND=(.*)$", proc.stdout, re.M)
    reason = re.search(r"^REASON=(.*)$", proc.stdout, re.M)
    assert recommend, f"bash consumer produced no RECOMMEND:\n{proc.stdout}\n{proc.stderr}"
    return recommend.group(1).strip(), reason.group(1).strip() if reason else ""


V4_STATES = {
    "arch-only": ({".arch-handoff.json": ARCH_HANDOFF}, False, "rdd-planner"),
    "arch+planner+active-change": (
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        True,
        "rdd-builder",
    ),
    "arch+planner-no-active-change": (
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        False,
        "rdd-builder",
    ),
    "corrupt-planner-handoff": (
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '{"schema":"planner-handoff-v1", TRUNCATED',
        },
        False,
        "rdd-planner",
    ),
}


@pytest.mark.parametrize("state_name", sorted(V4_STATES))
def test_three_consumers_agree_on_stage(tmp_path, state_name):
    handoffs, active_change, expected = V4_STATES[state_name]
    project = _project(tmp_path, handoffs, active_change)

    bash_stage, bash_reason = _bash_scan_state(project)
    cli_stage, cli_reason = _scan_state(project)
    synth = synthesize(project)

    assert bash_stage == expected, f"bash: {bash_stage} ({bash_reason})"
    assert cli_stage == expected, f"cli: {cli_stage} ({cli_reason})"
    assert synth.suggested_action == expected, f"synthesizer: {synth.reason}"
    assert bash_stage == cli_stage == synth.suggested_action


def test_bash_and_cli_report_the_corrupt_handoff_diagnostic(tmp_path):
    """The corrupt-file case must be *visible*, not silently treated as
    'planner not run' — otherwise the agent cannot tell a corrupt handoff
    from a missing one."""
    project = _project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '{"schema":"planner-handoff-v1", TRUNCATED',
        },
    )
    _, bash_reason = _bash_scan_state(project)
    _, cli_reason = _scan_state(project)
    assert "损坏" in bash_reason
    assert "损坏" in cli_reason


def test_v3_design_handoff_is_not_reported_as_plan_leftover(tmp_path):
    """A v3 DESIGN handoff means "design done, change generation next".
    Reporting the v3 PLAN leftover state here would be a behaviour
    regression (it was "进入变更生成" before this change set)."""
    project = _project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".design-handoff.json": {
                "version": 1,
                "design_complete_at": "2026-01-01",
                "proposals_reviewed": 3,
            },
        },
    )
    bash_stage, bash_reason = _bash_scan_state(project)
    cli_stage, cli_reason = _scan_state(project)
    synth = synthesize(project)

    assert bash_stage == cli_stage == synth.suggested_action == "rdd-builder"
    for reason in (bash_reason, cli_reason, synth.reason):
        assert "残留" not in reason
        assert "进入变更生成" in reason


def test_non_object_handoff_is_not_treated_as_valid(tmp_path):
    """A handoff whose top-level JSON is not an object is not a handoff.

    The bash consumer, the CLI consumer and the library consumer must all
    reject it — otherwise the three disagree on the same project.
    """
    project = _project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '["not", "an", "object"]',
        },
    )
    bash_stage, _ = _bash_scan_state(project)
    cli_stage, _ = _scan_state(project)
    synth = synthesize(project)

    assert bash_stage == cli_stage == synth.suggested_action == "rdd-planner"


def test_unverifiable_handoff_is_marked_non_authoritative(tmp_path):
    """Without python3 the bash consumer cannot validate the handoff JSON.

    It must NOT present the recommendation as an authoritative stage
    decision — a corrupt handoff must never be silently accepted.
    """
    project = _project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '{"schema":"planner-handoff-v1", TRUNCATED',
        },
    )

    # A PATH without python3 — but still with the binaries scan-state.sh
    # needs (bash, ls, sed, awk, wc, tr, git, ...).
    sandbox = tmp_path / "nopy3-bin"
    sandbox.mkdir()
    for tool in ("bash", "ls", "sed", "awk", "wc", "tr", "cat", "git",
                 "mktemp", "rm", "cp", "mkdir", "dirname", "grep", "jq"):
        found = shutil.which(tool)
        if found:
            (sandbox / tool).symlink_to(found)
    assert shutil.which("python3", path=str(sandbox)) is None, \
        "sandbox still exposes python3 — the test would be vacuous"

    proc = subprocess.run(
        [
            str(sandbox / "bash"),
            "-c",
            f"source '{SCAN_STATE_SH}'; scan_state '{project}'; "
            'echo "REASON=$REASON"',
        ],
        capture_output=True,
        text=True,
        env={"PATH": str(sandbox), "HOME": str(tmp_path)},
    )
    reason = re.search(r"^REASON=(.*)$", proc.stdout, re.M)
    assert reason, f"no REASON emitted:\n{proc.stdout}\n{proc.stderr}"
    assert "非权威" in reason.group(1), (
        "an unverifiable handoff must be reported as non-authoritative, "
        f"got: {reason.group(1)!r}"
    )


def test_active_change_count_is_a_single_bare_integer(tmp_path):
    """`_count_active_changes` must print ONE integer.

    Under `set -o pipefail` a failing `ls` used to make the whole pipeline
    fail, so a trailing `|| echo 0` appended a second "0" to the already
    printed "0" ("00"). The value must be a single bare integer.
    """
    missing = tmp_path / "no-such-dir"
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f"source '{SCAN_STATE_SH}'; _count_active_changes '{missing}'",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0", f"expected a single '0', got {proc.stdout!r}"
