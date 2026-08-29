"""RFC ambiguity detection (5 acceptance cases per phase-2-general-20260829063814)."""
from __future__ import annotations
from pathlib import Path

from _lib.rfc_ambiguity import detect_ambiguity


def _write(tmp_path, body):
    p = tmp_path / "proposal.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_missing_acceptance_section(tmp_path):
    body = "# Test\n\n## Why\nTBD\n\n## What Changes\nTBD\n"
    out = detect_ambiguity(_write(tmp_path, body))
    kinds = {a.kind for a in out}
    assert "missing_acceptance" in kinds


def test_scope_exceeds_threshold(tmp_path):
    files = "\n".join(f"- path/to/file_{i}.py" for i in range(8))
    body = (
        f"# Test\n\n## Why\nx\n\n## What Changes\nIn Scope:\n{files}\n\n"
        "## Acceptance\n- [ ] A\n- [ ] B\n- [ ] C\n"
    )
    out = detect_ambiguity(_write(tmp_path, body))
    kinds = {a.kind for a in out}
    assert "scope_overflow" in kinds


def test_multi_stakeholder_indicates_federation(tmp_path):
    body = (
        "# Test\n\n## Why\nTouches api-auth and Hub cross-repo.\n\n"
        "## What Changes\nIn Scope: api-foo, api-bar\n\n"
        "## Acceptance\n- [ ] A\n- [ ] B\n- [ ] C\n"
    )
    out = detect_ambiguity(_write(tmp_path, body))
    kinds = {a.kind for a in out}
    assert "multi_stakeholder" in kinds


def test_self_contradiction_in_scope(tmp_path):
    body = (
        "# Test\n\n## Why\nx\n\n"
        "## What Changes\nIn Scope:\n- api-foo\n- api-bar\n\n"
        "Out of Scope:\n- api-foo\n\n"
        "## Acceptance\n- [ ] A\n- [ ] B\n- [ ] C\n"
    )
    out = detect_ambiguity(_write(tmp_path, body))
    kinds = {a.kind for a in out}
    assert "contradiction" in kinds


def test_vague_language_detected(tmp_path):
    body = (
        "# Test\n\n## Why\nmaybe this should probably fix things.\n\n"
        "## What Changes\nIn Scope: api-foo\n\n## Acceptance\n"
    )
    out = detect_ambiguity(_write(tmp_path, body))
    kinds = {a.kind for a in out}
    assert "vague" in kinds