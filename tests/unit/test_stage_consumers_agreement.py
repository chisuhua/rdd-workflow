"""Single-implementation contract for stage recommendation.

ADR-0062 consolidated the three independent decision ladders into ONE
implementation (``_lib/recommender.py::scan_state``). The bash copy went
away with ``skills/guide/`` (ADR-0063).

Two consumers remain and must agree:

  1. ``rddf guide``  — ``_lib/cli/guide_cmd.py::cmd_guide``
  2. ``rddf monitor`` — ``_lib/workflow_synthesizer.py::synthesize``

Because they share one implementation, the agreement assertions below are
**wiring** assertions (each consumer really routes through the shared
ladder), not a re-implementation of the ladder. The structural assertions
in ``test_recommender.py`` are what actually pin "exactly one ladder".

The v3 states are covered too — the CLI consumer cross-validates a stale
v3 plan-handoff against the filesystem, and that behaviour is now shared.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from skills._lib.cli.guide_cmd import cmd_guide
from skills._lib.workflow_synthesizer import synthesize

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
DESIGN_HANDOFF = {
    "version": 1,
    "design_complete_at": "2026-01-01",
    "proposals_reviewed": 3,
}

#: The synthesizer's catch-all swallows any exception into this reason.
#: A consumer whose reason equals it did NOT go through the shared ladder
#: successfully — the agreement assertion below would be vacuous.
FALLBACK_REASON = "fallback: synthesizer error"


def _project(tmp_path: Path, handoffs: dict, active_change: bool = False) -> str:
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    for name, payload in handoffs.items():
        text = payload if isinstance(payload, str) else json.dumps(payload)
        (state / name).write_text(text, encoding="utf-8")
    if active_change:
        (tmp_path / "openspec" / "changes" / "add-x").mkdir(parents=True)
    return str(tmp_path)


def _cli_recommend(project: str, monkeypatch) -> tuple[str, str]:
    """Run ``rddf guide`` and parse its (action, reason) from stdout."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", project)
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cmd_guide([])
    assert rc == 0
    out = buf.getvalue()
    m = re.search(r"💡 建议:\s*(\S+)\n\s*(.+)", out)
    assert m, f"could not parse recommendation from:\n{out}"
    return m.group(1), m.group(2).strip()


#: (state name, handoffs, active_change) — the states both consumers must
#: agree on. Includes the four v4 states plus the three divergence points
#: the pre-consolidation implementations disagreed on (no arch-handoff,
#: v3 design handoff, corrupt planner handoff, non-object handoff).
STATES = {
    "arch-only": ({".arch-handoff.json": ARCH_HANDOFF}, False),
    "arch+planner+active-change": (
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        True,
    ),
    "arch+planner-no-active-change": (
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        False,
    ),
    "corrupt-planner-handoff": (
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '{"schema":"planner-handoff-v1", TRUNCATED',
        },
        False,
    ),
    "no-arch-handoff": ({}, False),
    "v3-design-handoff": (
        {".arch-handoff.json": ARCH_HANDOFF, ".design-handoff.json": DESIGN_HANDOFF},
        False,
    ),
    "non-object-handoff": (
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '["not", "an", "object"]',
        },
        False,
    ),
}


@pytest.mark.parametrize("state_name", sorted(STATES))
def test_two_consumers_agree_on_stage(tmp_path, monkeypatch, state_name):
    handoffs, active_change = STATES[state_name]
    project = _project(tmp_path, handoffs, active_change)

    cli_stage, cli_reason = _cli_recommend(project, monkeypatch)
    synth = synthesize(project)

    assert synth.reason != FALLBACK_REASON, (
        f"state={state_name}: synthesizer fell back — the shared ladder "
        f"raised, so this assertion proves nothing"
    )
    assert synth.suggested_action == cli_stage, (
        f"state={state_name}: cli={cli_stage} ({cli_reason}) "
        f"synthesizer={synth.suggested_action} ({synth.reason})"
    )
    assert synth.reason == cli_reason, (
        f"state={state_name}: cli reason={cli_reason!r} "
        f"synthesizer reason={synth.reason!r}"
    )


def test_corrupt_handoff_diagnostic_is_visible(tmp_path, monkeypatch):
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
    _, cli_reason = _cli_recommend(project, monkeypatch)
    synth = synthesize(project)
    assert "损坏" in cli_reason
    assert "损坏" in synth.reason


def test_v3_design_handoff_is_not_reported_as_plan_leftover(tmp_path, monkeypatch):
    """A v3 DESIGN handoff means "design done, change generation next".
    Reporting the v3 PLAN leftover state here would be a behaviour
    regression (it was "进入变更生成" before this change set)."""
    project = _project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".design-handoff.json": DESIGN_HANDOFF,
        },
    )
    cli_stage, cli_reason = _cli_recommend(project, monkeypatch)
    synth = synthesize(project)

    assert cli_stage == synth.suggested_action == "rdd-builder"
    for reason in (cli_reason, synth.reason):
        assert "残留" not in reason
        assert "进入变更生成" in reason


def test_non_object_handoff_is_not_treated_as_valid(tmp_path, monkeypatch):
    """A handoff whose top-level JSON is not an object is not a handoff."""
    project = _project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '["not", "an", "object"]',
        },
    )
    cli_stage, _ = _cli_recommend(project, monkeypatch)
    synth = synthesize(project)

    assert cli_stage == synth.suggested_action == "rdd-planner"
