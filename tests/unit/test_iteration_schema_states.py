"""`iteration_schema.json` declares the state enum the status view used to mirror.

Migrated (2026-11-20) from
`tests/integration/test_status_state_table.bats::"iteration.json schema declared
states match Mode A list"` when the retired `status` skill was archived to
`docs/legacy/` (change `retire-status-skill`).

The original @test only grepped the schema file — it never read the
skill document. Keeping it preserves the schema invariant that the
disk-derived status set (`planned` / `in_worktree` / `committed`) is a subset
of what the schema declares.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[2] / "_lib" / "schemas" / "iteration_schema.json"


def test_schema_declares_the_lifecycle_states() -> None:
    text = SCHEMA.read_text(encoding="utf-8")
    for state in ("planned", "proposed", "in_worktree", "completed", "archived"):
        assert state in text, f"{state!r} missing from iteration_schema.json"


def test_schema_is_valid_json() -> None:
    json.loads(SCHEMA.read_text(encoding="utf-8"))
