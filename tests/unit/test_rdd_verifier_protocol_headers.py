"""Behavioural checks for the AC header variants (fix-flow-drift-batch-1).

The implementation (`_lib/verifier/protocol.py`) accepts three header
spellings; the SKILL.md documentation used to list only two. A read-doc agent
would therefore have believed that a `## Acceptance` section is not recognised.

These tests assert the BEHAVIOUR (parse_acs over three fixture proposals)
rather than comparing the documentation string with the implementation string —
the latter breaks on formatting, not on semantics.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "_lib"))

from skills._lib.verifier.protocol import parse_acs  # noqa: E402


@pytest.mark.parametrize("header", ["## 验收标准", "## Acceptance Criteria", "## Acceptance"])
def test_parse_acs_accepts_every_header_variant(tmp_path: Path, header: str):
    proposal = tmp_path / "proposal.md"
    proposal.write_text(
        f"# demo\n\n{header}\n\n- [ ] first item\n- [ ] second item\n",
        encoding="utf-8",
    )
    acs = parse_acs(proposal)
    assert len(acs) == 2, acs
    assert [a["ac_id"] for a in acs] == ["AC-1", "AC-2"]


def test_skill_doc_lists_every_header_variant():
    skill = (ROOT / "skills" / "rdd-verifier" / "SKILL.md").read_text(encoding="utf-8")
    for variant in ("验收标准", "Acceptance Criteria", "Acceptance"):
        assert variant in skill, variant
