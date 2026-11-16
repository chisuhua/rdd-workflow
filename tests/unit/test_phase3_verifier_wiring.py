"""Static guards for fix-p3-verifier-gate (AC-1 / AC-2).

These encode two invariants that a behavioural test cannot see:

1. No code path may reference ``verifier_run`` — that script never existed, and
   the historical ``[ -f ... ]`` guard made the whole verifier pre-call a no-op.
2. P3 must not harbour a ``VERIFIER_EXIT`` default that turns "the pre-call
   never ran" into "verification passed".
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHASE3 = ROOT / "skills" / "rdd-builder" / "scripts" / "phase3_archive.sh"


def test_no_verifier_run_reference_in_code():
    out = subprocess.run(
        ["grep", "-rn", "verifier_run", str(ROOT / "skills"), str(ROOT / "_lib")],
        capture_output=True,
        text=True,
    )
    # grep exits 1 (no match) → stdout empty. Any hit is a regression.
    assert out.stdout.strip() == "", out.stdout


def test_phase3_has_no_default_pass_on_verifier_exit():
    src = PHASE3.read_text()
    assert "VERIFIER_EXIT" not in src
    assert "route_verifier_verdict" not in src
    assert "archive_gate_check" in src
