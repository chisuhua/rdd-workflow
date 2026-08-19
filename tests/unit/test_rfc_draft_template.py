"""Unit tests for add-rfc-draft-template new functions:
- build_rfc_draft_template / append_rfc_draft_template (in detect_cross_repo_impact.py)
- build_contract_draft_block (in report_issue_rfc.py)
"""
import sys
import os
import tempfile
from pathlib import Path

# Import detect_cross_repo_impact (reuses P0 #1 module)
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "add-improve" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR / "lib"))

import detect_cross_repo_impact  # noqa: E402
from detect_cross_repo_impact import (  # noqa: E402
    build_rfc_draft_template,
    append_rfc_draft_template,
    TEMPLATE_START_SENTINEL,
    TEMPLATE_END_SENTINEL,
)

# Import build_contract_draft_block
REPORT_SCRIPT = Path(__file__).resolve().parent.parent.parent / "skills" / "report-issue" / "scripts" / "report_issue_rfc.py"
import importlib.util
_spec = importlib.util.spec_from_file_location("_report_issue_rfc_mod", REPORT_SCRIPT)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load spec for {REPORT_SCRIPT}")
report_issue_rfc = importlib.util.module_from_spec(_spec)
sys.modules["_report_issue_rfc_mod"] = report_issue_rfc
_spec.loader.exec_module(report_issue_rfc)
build_contract_draft_block = report_issue_rfc.build_contract_draft_block


# ---------------------------------------------------------------------------
# build_rfc_draft_template
# ---------------------------------------------------------------------------

def test_build_template_with_matches_includes_all_sections():
    report = {
        "proposal_name": "auth-v2-redesign",
        "matches": [
            {"contract_name": "auth-v2.yaml", "contract_path": "contracts/auth-v2.yaml",
             "matched_keywords": ["auth", "v2"], "owners": ["org/repo-a"]},
        ],
        "suggested_stakeholders": ["org/repo-a"],
    }
    tpl = build_rfc_draft_template(report)

    assert TEMPLATE_START_SENTINEL in tpl
    assert TEMPLATE_END_SENTINEL in tpl
    assert "## 变更动机" in tpl
    assert "## 契约草案" in tpl
    assert "## 影响仓库" in tpl
    assert "## 兼容策略" in tpl
    assert "## 回滚方案" in tpl
    assert "auth-v2-redesign" in tpl
    assert "contracts/auth-v2.yaml" in tpl
    assert "`org/repo-a`" in tpl
    assert "Design-Gate" in tpl
    assert "Breaking-Change" in tpl


def test_build_template_with_no_matches_graceful():
    report = {
        "proposal_name": "lone-change",
        "matches": [],
        "suggested_stakeholders": [],
    }
    tpl = build_rfc_draft_template(report)

    assert "(no contracts matched)" in tpl
    assert "(no stakeholders detected)" in tpl
    assert TEMPLATE_START_SENTINEL in tpl


def test_build_template_custom_gate_and_impact():
    report = {"proposal_name": "x", "matches": [], "suggested_stakeholders": []}
    tpl = build_rfc_draft_template(report, gate="Ship-Gate", contract_impact="Low")
    assert "Ship-Gate" in tpl
    assert "Low" in tpl


# ---------------------------------------------------------------------------
# append_rfc_draft_template
# ---------------------------------------------------------------------------

def test_append_to_empty_file(tmp_path):
    p = tmp_path / "proposal.md"
    p.write_text("")
    tpl = build_rfc_draft_template({"proposal_name": "x", "matches": [], "suggested_stakeholders": []})
    append_rfc_draft_template(str(p), tpl)

    text = p.read_text()
    assert TEMPLATE_START_SENTINEL in text
    assert TEMPLATE_END_SENTINEL in text


def test_append_to_existing_content_preserves_content(tmp_path):
    p = tmp_path / "proposal.md"
    p.write_text("# My Proposal\n\nSome pre-existing content.\n")
    tpl = build_rfc_draft_template({"proposal_name": "x", "matches": [], "suggested_stakeholders": []})
    append_rfc_draft_template(str(p), tpl)

    text = p.read_text()
    assert "Some pre-existing content." in text
    assert TEMPLATE_START_SENTINEL in text
    # Template should come AFTER existing content
    assert text.index("pre-existing content") < text.index(TEMPLATE_START_SENTINEL)


def test_append_is_idempotent_replaces_existing_block(tmp_path):
    p = tmp_path / "proposal.md"
    p.write_text("# Title\n\nFirst template:\n" + TEMPLATE_START_SENTINEL + "\nold content\n" + TEMPLATE_END_SENTINEL + "\n\nEnd.\n")

    tpl = build_rfc_draft_template(
        {"proposal_name": "x", "matches": [], "suggested_stakeholders": []},
        gate="Plan-Gate",
    )
    append_rfc_draft_template(str(p), tpl)

    text = p.read_text()
    # Only one template block
    assert text.count(TEMPLATE_START_SENTINEL) == 1
    assert text.count(TEMPLATE_END_SENTINEL) == 1
    # Old content replaced, new gate injected
    assert "old content" not in text
    assert "Plan-Gate" in text
    # Original surrounding content preserved
    assert "# Title" in text
    assert "End." in text


# ---------------------------------------------------------------------------
# build_contract_draft_block
# ---------------------------------------------------------------------------

def test_contract_block_inlines_small_file(tmp_path):
    p = tmp_path / "contract.yaml"
    p.write_text("openapi: 3.0.0\ninfo: {title: Test}\n")

    block = build_contract_draft_block(str(p))
    assert "<details><summary>Contract draft" in block
    assert "</details>" in block
    assert str(p) in block
    assert "35 bytes" in block  # length of contract.yaml content
    # base64 of "openapi: 3.0.0\ninfo: {title: Test}\n"
    import base64
    expected_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    assert expected_b64 in block


def test_contract_block_missing_file_raises():
    try:
        build_contract_draft_block("/nonexistent/path/contract.yaml")
        assert False, "should have raised"
    except FileNotFoundError:
        pass


def test_contract_block_too_large_raises(tmp_path):
    p = tmp_path / "huge.yaml"
    p.write_bytes(b"x" * 50000)  # > 49152

    try:
        build_contract_draft_block(str(p))
        assert False, "should have raised"
    except ValueError as e:
        assert "too large" in str(e)
        assert "50000" in str(e)
