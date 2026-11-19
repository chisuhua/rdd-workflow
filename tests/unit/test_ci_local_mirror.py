"""Contract test: the local gate (./test.sh) mirrors the CI gates (.github/workflows/test.yml).

The failure this prevents (2026-08-15 → 2026-11-19, three months): CI was red
on master (the Ruff step, because `requirements.txt` pinned `ruff>=0.1` and a
ruff release widened the default rule set) while `./test.sh` was green — the
local runner never called the CI gates, so nobody saw it.

Three layers, all data-driven so they cannot rot into "the test passes because
it agrees with itself":

1. COMMAND MIRROR (the contract): every mirrored command must appear in BOTH
   test.sh and test.yml. Renaming a CI step does not break this layer — only
   changing a command does.
2. COVERAGE LEDGER: every CI step that has a `run:` must either be covered by
   one of the mirrored commands, or be listed in test.sh's NOT_MIRRORED array
   (the honest ledger of "which CI gates the local gate does NOT mirror, and
   why"). `uses:`-only steps (checkout / setup-python) are skipped.
3. REVERSE: every name in NOT_MIRRORED must really exist in test.yml — a
   ledger entry that names a step which no longer exists is itself drift.

When layer 2 fails there are exactly two ways out, and the message says so:
mirror the step, or add it to NOT_MIRRORED with a reason.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_SH = REPO_ROOT / "test.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test.yml"

# Command fragments the local gate mirrors. Each must appear in test.sh AND in
# test.yml — that is what "the local gate runs the CI gate" means concretely.
MIRRORED_COMMANDS = [
    "ruff check skills/_lib/",
    "mypy --strict skills/_lib/core/",
    "--gate structural",
    "check_test_isolation.sh",
    "pytest tests/unit/",
    "pytest tests/integration/",
    # NOTE: `bats tests/` is NOT mirrored — CI splits it (integration/ under the
    # baseline gate, the rest raw) because the baseline legitimately carries
    # accepted failures.
    "report_regression.sh",
    "--e2e-smoke",
]


def _test_sh_text() -> str:
    return TEST_SH.read_text(encoding="utf-8")


def _not_mirrored() -> list[str]:
    """Parse the NOT_MIRRORED array out of test.sh (single source of truth)."""
    text = _test_sh_text()
    m = re.search(r"^NOT_MIRRORED=\(\n(.*?)^\)", text, re.MULTILINE | re.DOTALL)
    assert m, "NOT_MIRRORED array not found in test.sh"
    return re.findall(r'"([^"]+)"', m.group(1))


def _workflow_steps() -> list[dict]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data["jobs"]["test"]["steps"]


def _run_text(step: dict) -> str:
    return step.get("run") or ""


# ── Layer 1: command mirror ──────────────────────────────────────────────

@pytest.mark.parametrize("command", MIRRORED_COMMANDS)
def test_mirrored_command_present_in_both_files(command: str):
    """The local gate and CI must run the SAME command for every mirrored gate."""
    in_test_sh = command in _test_sh_text()
    in_workflow = any(command in _run_text(s) for s in _workflow_steps())
    assert in_test_sh, (
        f"本地门缺这条命令: {command!r} —— test.sh 里找不到。"
        f"要么把它接进 test.sh，要么从 MIRRORED_COMMANDS 移除。"
    )
    assert in_workflow, (
        f"CI 里缺这条命令: {command!r} —— .github/workflows/test.yml 里找不到。"
        f"要么把 CI 的 step 改回这条命令，要么从 MIRRORED_COMMANDS 移除。"
    )


# ── Layer 2: coverage ledger ─────────────────────────────────────────────

def test_every_ci_step_is_mirrored_or_declared_not_mirrored():
    """No CI step may silently have no local counterpart."""
    steps = _workflow_steps()
    not_mirrored = set(_not_mirrored())
    uncovered: list[str] = []

    for step in steps:
        name = step.get("name", "")
        if not step.get("run"):
            continue  # uses:-only step (checkout / setup-python)
        if any(cmd in _run_text(step) for cmd in MIRRORED_COMMANDS):
            continue  # covered by a mirrored command
        if name in not_mirrored:
            continue  # explicitly declared as not mirrored
        uncovered.append(name)

    assert not uncovered, (
        "这些 CI step 在本地门里既没有对应命令，也没写进 test.sh 的 NOT_MIRRORED:\n"
        + "\n".join(f"  - {n}" for n in uncovered)
        + "\n两条出路：① 在 test.sh 里接上它（命令进 MIRRORED_COMMANDS）；"
          "② 把它写进 NOT_MIRRORED（并写明为什么本地不镜像）。"
    )


# ── Layer 3: reverse check on the ledger ────────────────────────────────

def test_not_mirrored_entries_exist_in_workflow():
    """A ledger entry naming a step that no longer exists is drift itself."""
    names = {s.get("name", "") for s in _workflow_steps()}
    missing = [n for n in _not_mirrored() if n not in names]
    assert not missing, (
        "NOT_MIRRORED 里的这些名字在 CI workflow 里已经不存在了:\n"
        + "\n".join(f"  - {n}" for n in missing)
        + "\n（CI 的 step 改名/删除后，这里必须同步）"
    )


def test_not_mirrored_entries_are_unique():
    """A duplicated entry means the ledger was edited carelessly."""
    entries = _not_mirrored()
    dupes = {n for n in entries if entries.count(n) > 1}
    assert not dupes, f"NOT_MIRRORED 有重复项: {sorted(dupes)}"
