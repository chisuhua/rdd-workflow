"""Unit tests for ac_verifier module."""
from pathlib import Path
import pytest
from skills.ac_verifier.scripts.ac_verifier import parse_acs


def test_parse_acs_empty_section(tmp_path: Path):
    """Section header present but no bullets → empty list."""
    p = tmp_path / "proposal.md"
    p.write_text("# T\n\n## 验收标准\n\n## Other\n", encoding="utf-8")
    assert parse_acs(p) == []


def test_parse_acs_single_checkbox(tmp_path: Path):
    """Single `- [ ]` bullet becomes AC-1."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- [ ] First AC\n\n## Other\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert len(result) == 1
    assert result[0]["ac_id"] == "AC-1"
    assert result[0]["description"] == "First AC"
    assert result[0]["has_checkbox"] is True


def test_parse_acs_multiple_prose_bullets(tmp_path: Path):
    """Prose bullets (no checkbox) are also ACs."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- First AC\n- Second AC\n- Third AC\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert [r["ac_id"] for r in result] == ["AC-1", "AC-2", "AC-3"]
    assert all(r["has_checkbox"] is False for r in result)


def test_parse_acs_mixed(tmp_path: Path):
    """Mix of checkbox and prose bullets."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- [ ] First\n- Second\n- [x] Done\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert len(result) == 3
    assert result[0]["has_checkbox"] is True
    assert result[1]["has_checkbox"] is False
    assert result[2]["has_checkbox"] is True


def test_parse_acs_missing_section(tmp_path: Path):
    """No `## 验收标准` section → empty list."""
    p = tmp_path / "proposal.md"
    p.write_text("# T\n\n## Acceptance\n- something\n", encoding="utf-8")
    assert parse_acs(p) == []


from skills.ac_verifier.scripts.ac_verifier import build_agent_prompt


def test_build_prompt_includes_all_acs():
    """All AC descriptions appear in the user prompt."""
    acs = [
        {"ac_id": "AC-1", "description": "First AC", "has_checkbox": True},
        {"ac_id": "AC-2", "description": "Second AC", "has_checkbox": False},
    ]
    system, user = build_agent_prompt(acs, "my-change")
    assert "AC-1" in user
    assert "First AC" in user
    assert "AC-2" in user
    assert "Second AC" in user
    assert "my-change" in system or "my-change" in user


def test_build_prompt_declares_tools():
    """System prompt lists all available tools."""
    acs = [{"ac_id": "AC-1", "description": "x", "has_checkbox": False}]
    system, _ = build_agent_prompt(acs, "x")
    for tool in ["codegraph_explore", "grep_app_searchGitHub", "codebase-memory-mcp", "git"]:
        assert tool in system, f"Tool {tool} not in system prompt"


def test_build_prompt_requires_json_schema():
    """System prompt specifies JSON array output format."""
    acs = [{"ac_id": "AC-1", "description": "x", "has_checkbox": False}]
    system, _ = build_agent_prompt(acs, "x")
    assert "JSON" in system or "json" in system
    assert "ac_id" in system
    assert "status" in system
    assert "pass" in system and "fail" in system


import os
from skills.ac_verifier.scripts.ac_verifier import invoke_ai_agent, AcVerifierError


def test_invoke_ai_agent_mock_pass(monkeypatch):
    """Mock mode returns canned JSON."""
    monkeypatch.setenv("AC_LLM_MOCK", "yes")
    monkeypatch.setenv("AC_LLM_MOCK_SCENARIO", "mock_pass_all")
    raw = invoke_ai_agent("system", "AC-1: foo\nAC-2: bar")
    import json
    parsed = json.loads(raw)
    assert len(parsed) == 2
    assert parsed[0]["status"] == "pass"
    assert parsed[1]["status"] == "pass"


def test_invoke_ai_agent_mock_fail(monkeypatch):
    """Mock fail scenario returns one fail."""
    monkeypatch.setenv("AC_LLM_MOCK", "yes")
    monkeypatch.setenv("AC_LLM_MOCK_SCENARIO", "mock_fail_one")
    raw = invoke_ai_agent("system", "AC-1: foo\nAC-2: bar")
    import json
    parsed = json.loads(raw)
    statuses = [v["status"] for v in parsed]
    assert "fail" in statuses


def test_invoke_ai_agent_raises_on_unmocked():
    """Without AC_LLM_MOCK=yes, raises AcVerifierError (no real LLM in unit tests)."""
    os.environ.pop("AC_LLM_MOCK", None)
    with pytest.raises(AcVerifierError):
        invoke_ai_agent("system", "user")


import json
from skills.ac_verifier.scripts.ac_verifier import parse_verdict


def test_parse_verdict_valid():
    """Valid JSON array with correct count passes through."""
    raw = json.dumps([
        {"ac_id": "AC-1", "description": "x", "status": "pass",
         "confidence": 0.9, "evidence": [], "reasoning": "ok"}
    ])
    result = parse_verdict(raw, expected_count=1)
    assert len(result) == 1
    assert result[0]["status"] == "pass"


def test_parse_verdict_missing_ac_filled_as_fail():
    """Missing AC entry auto-filled with fail."""
    raw = json.dumps([
        {"ac_id": "AC-1", "description": "x", "status": "pass",
         "confidence": 0.9, "evidence": [], "reasoning": "ok"}
        # AC-2 missing
    ])
    result = parse_verdict(raw, expected_count=2)
    assert len(result) == 2
    statuses = {r["ac_id"]: r["status"] for r in result}
    assert statuses["AC-1"] == "pass"
    assert statuses["AC-2"] == "fail"
    assert "AI omitted" in result[1]["reasoning"]


def test_parse_verdict_invalid_json_raises():
    """Unparseable JSON raises AcVerifierError."""
    with pytest.raises(AcVerifierError):
        parse_verdict("not json at all", expected_count=2)


from skills.ac_verifier.scripts.ac_verifier import apply_gate_rules


def test_apply_gate_rules_all_pass_returns_0():
    """All pass → exit 0."""
    verdict = [{"ac_id": "AC-1", "status": "pass"}]
    assert apply_gate_rules(verdict, strict=False) == 0


def test_apply_gate_rules_one_fail_warning_returns_0():
    """One fail, not strict → exit 0 (warning, not blocking)."""
    verdict = [
        {"ac_id": "AC-1", "status": "pass"},
        {"ac_id": "AC-2", "status": "fail"},
    ]
    assert apply_gate_rules(verdict, strict=False) == 0


def test_apply_gate_rules_one_fail_strict_returns_1():
    """One fail, strict → exit 1 (blocking)."""
    verdict = [
        {"ac_id": "AC-1", "status": "pass"},
        {"ac_id": "AC-2", "status": "fail"},
    ]
    assert apply_gate_rules(verdict, strict=True) == 1


def test_apply_gate_rules_partial_warning_returns_0():
    """Partial counts as warning (not fail)."""
    verdict = [{"ac_id": "AC-1", "status": "partial"}]
    assert apply_gate_rules(verdict, strict=False) == 0
    assert apply_gate_rules(verdict, strict=True) == 0  # partial != fail


def test_apply_gate_rules_empty_verdict_returns_2():
    """Empty verdict (no ACs) → exit 2 (skipped)."""
    assert apply_gate_rules([], strict=False) == 2
    assert apply_gate_rules([], strict=True) == 2