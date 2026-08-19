"""Unit tests for detect_cross_repo_impact + hub_contract_metadata.

Mock-based: no real gh CLI calls. Test the algorithm in isolation.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts/lib to path for direct imports
# test file: <root>/tests/unit/test_detect_cross_repo_impact.py
# SCRIPTS_DIR = <root>/skills/add-improve/scripts
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "add-improve" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR / "lib"))

import hub_contract_metadata  # noqa: E402
from hub_contract_metadata import (  # noqa: E402
    list_hub_contracts,
    parse_x_owners,
    extract_match_keywords,
)


# ---------------------------------------------------------------------------
# hub_contract_metadata unit tests
# ---------------------------------------------------------------------------

def test_list_hub_contracts_parses_gh_api_output():
    fake = [
        {"name": "auth-v2.yaml", "path": "contracts/auth-v2.yaml", "type": "file", "sha": "abc"},
        {"name": "user.json", "path": "contracts/user.json", "type": "file", "sha": "def"},
        {"name": "README.md", "path": "contracts/README.md", "type": "file", "sha": "ghi"},
    ]
    with patch.object(subprocess, "run", return_value=MagicMock(stdout=json.dumps(fake), returncode=0)):
        result = list_hub_contracts("my-org/rdd-hub")
    assert len(result) == 3
    assert result[0]["name"] == "auth-v2.yaml"
    assert result[0]["sha"] == "abc"


def test_list_hub_contracts_filters_non_files():
    fake = [
        {"name": "subdir", "path": "contracts/subdir", "type": "dir", "sha": "abc"},
        {"name": "auth.yaml", "path": "contracts/auth.yaml", "type": "file", "sha": "def"},
    ]
    with patch.object(subprocess, "run", return_value=MagicMock(stdout=json.dumps(fake), returncode=0)):
        result = list_hub_contracts("my-org/rdd-hub")
    assert len(result) == 1
    assert result[0]["name"] == "auth.yaml"


def test_list_hub_contracts_returns_empty_on_network_error():
    with patch.object(subprocess, "run", side_effect=subprocess.CalledProcessError(1, "gh")):
        assert list_hub_contracts("my-org/rdd-hub") == []


def test_list_hub_contracts_returns_empty_on_timeout():
    with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 20)):
        assert list_hub_contracts("my-org/rdd-hub") == []


def test_list_hub_contracts_rejects_invalid_format():
    with patch("builtins.print") as mock_print:
        result = list_hub_contracts("invalid-no-slash")
    assert result == []
    assert any("must be <owner>" in str(c) for c in mock_print.call_args_list)


def test_parse_x_owners_extracts_org_repo_pairs():
    yaml_text = """
openapi: 3.0.0
x-owners: [my-org/repo-backend, my-org/repo-security]
info:
  title: Test
"""
    assert parse_x_owners(yaml_text) == ["my-org/repo-backend", "my-org/repo-security"]


def test_parse_x_owners_returns_empty_when_missing():
    yaml_text = """
openapi: 3.0.0
info:
  title: Test
"""
    assert parse_x_owners(yaml_text) == []


def test_parse_x_owners_filters_invalid_formats():
    yaml_text = """
x-owners: [valid-org/repo, invalid-no-slash, also-invalid, another/valid]
"""
    result = parse_x_owners(yaml_text)
    assert "valid-org/repo" in result
    assert "another/valid" in result
    assert "invalid-no-slash" not in result
    assert "also-invalid" not in result


def test_extract_match_keywords_strips_extension():
    kws = extract_match_keywords("auth-v2.yaml")
    assert "auth-v2" in kws
    assert "auth-v2.yaml" in kws
    assert "auth" in kws
    assert "v2" in kws


def test_extract_match_keywords_handles_json():
    kws = extract_match_keywords("user-profile.json")
    assert "user-profile" in kws
    assert "user" in kws
    assert "profile" in kws


def test_extract_match_keywords_underscore_and_dash():
    kws = extract_match_keywords("order_api-v2.yaml")
    assert "order" in kws
    assert "api" in kws
    assert "v2" in kws
    assert "order_api-v2" in kws


# ---------------------------------------------------------------------------
# detect_cross_repo_impact unit tests (using detect() directly)
# ---------------------------------------------------------------------------

SCRIPTS_PARENT = SCRIPTS_DIR
sys.path.insert(0, str(SCRIPTS_PARENT))
import detect_cross_repo_impact  # noqa: E402
from detect_cross_repo_impact import (  # noqa: E402
    extract_body,
    body_matches,
    detect,
    write_report_atomic,
)


def test_extract_body_strips_yaml_frontmatter():
    text = """---
author: someone
---
# Title

Body content.
"""
    body = extract_body(text)
    assert "author" not in body
    assert "Title" in body
    assert "Body content" in body


def test_extract_body_strips_head_fields():
    text = """# Proposal

**阶段**: v2.2
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why

Real content here.
"""
    body = extract_body(text)
    assert "阶段" not in body
    assert "分类" not in body
    assert "类型" not in body
    assert "特性" not in body
    assert "Real content" in body


def test_body_matches_word_boundary():
    assert body_matches("auth-v2 is good", ["auth", "v2"]) == ["auth", "v2"]
    assert body_matches("authenticator handles login", ["auth"]) == ["auth"]


def test_body_matches_no_match():
    assert body_matches("nothing related here", ["auth", "v2"]) == []


def test_body_matches_case_insensitive():
    assert body_matches("AUTH-v2 supports AUTH flow", ["auth-v2"]) == ["auth-v2"]


def _make_proposal(tmp_path: Path, body_text: str) -> str:
    p = tmp_path / "test-proposal.md"
    p.write_text(
        """# Test Proposal

**阶段**: v2.2
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why

""" + body_text + "\n",
        encoding="utf-8",
    )
    return str(p)


def test_detect_single_contract_match(tmp_path):
    proposal = _make_proposal(tmp_path, "Need to update auth-v2 flow with new field.")

    fake_contracts = [
        {"name": "auth-v2.yaml", "path": "contracts/auth-v2.yaml", "sha": "abc"},
    ]
    fake_content = "openapi: 3.0.0\nx-owners: [my-org/repo-backend]\n"

    def fake_list(repo):
        return fake_contracts

    def fake_fetch(repo, path, sha):
        return fake_content

    with patch.object(hub_contract_metadata, "list_hub_contracts", fake_list), \
         patch.object(hub_contract_metadata, "fetch_contract_content", fake_fetch):
        report = detect(proposal, "my-org/rdd-hub")

    assert len(report["matches"]) == 1
    assert report["matches"][0]["contract_name"] == "auth-v2.yaml"
    assert report["matches"][0]["owners"] == ["my-org/repo-backend"]
    assert report["suggested_stakeholders"] == ["my-org/repo-backend"]
    assert report["suggested_category"] == "cross-repo-federation"


def test_detect_no_match(tmp_path):
    proposal = _make_proposal(tmp_path, "Just a regular local-only change.")

    with patch.object(hub_contract_metadata, "list_hub_contracts", return_value=[
        {"name": "auth-v2.yaml", "path": "contracts/auth-v2.yaml", "sha": "abc"}
    ]), patch.object(hub_contract_metadata, "fetch_contract_content", return_value=None):
        report = detect(proposal, "my-org/rdd-hub")

    assert report["matches"] == []
    assert report["suggested_category"] is None
    assert report["suggested_stakeholders"] == []


def test_detect_multi_contract_match_owners_union(tmp_path):
    proposal = _make_proposal(tmp_path, "Update both auth-v2 and user-profile.")

    fake_contracts = [
        {"name": "auth-v2.yaml", "path": "contracts/auth-v2.yaml", "sha": "a"},
        {"name": "user-profile.json", "path": "contracts/user-profile.json", "sha": "b"},
    ]

    def fake_fetch(repo, path, sha):
        if "auth-v2" in path:
            return "x-owners: [org/repo-backend]\n"
        if "user-profile" in path:
            return "x-owners: [org/repo-data, org/repo-frontend]\n"
        return None

    with patch.object(hub_contract_metadata, "list_hub_contracts", return_value=fake_contracts), \
         patch.object(hub_contract_metadata, "fetch_contract_content", side_effect=fake_fetch):
        report = detect(proposal, "my-org/rdd-hub")

    assert len(report["matches"]) == 2
    assert set(report["suggested_stakeholders"]) == {
        "org/repo-backend", "org/repo-data", "org/repo-frontend"
    }


def test_detect_missing_owners_defaults_empty(tmp_path):
    proposal = _make_proposal(tmp_path, "Touch auth-v2.")

    with patch.object(hub_contract_metadata, "list_hub_contracts", return_value=[
        {"name": "auth-v2.yaml", "path": "contracts/auth-v2.yaml", "sha": "x"}
    ]), patch.object(hub_contract_metadata, "fetch_contract_content", return_value="openapi: 3.0.0\n"):
        report = detect(proposal, "my-org/rdd-hub")

    assert report["matches"][0]["owners"] == []


def test_detect_handles_malformed_body(tmp_path):
    p = tmp_path / "broken.md"
    p.write_bytes(b"\x00\x01\x02 broken bytes \xff\xfe")

    with patch.object(hub_contract_metadata, "list_hub_contracts", return_value=[]):
        report = detect(str(p), "my-org/rdd-hub")

    assert report["matches"] == []
    assert report["version"] == 1


def test_write_report_atomic(tmp_path):
    report = {"version": 1, "matches": [], "test": True}
    output = tmp_path / "report.json"
    write_report_atomic(report, str(output))
    assert output.exists()
    data = json.loads(output.read_text())
    assert data["version"] == 1
    assert data["test"] is True
    # No leftover .tmp files
    leftover = list(tmp_path.glob(".cross-repo-detection-*.tmp"))
    assert leftover == []


def test_main_opt_out_env_exits_zero(tmp_path):
    import subprocess as sp
    proposal = _make_proposal(tmp_path, "anything")
    output = tmp_path / "report.json"
    env = os.environ.copy()
    env["RDDF_SKIP_CROSS_REPO_DETECTION"] = "yes"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_PARENT / "detect_cross_repo_impact.py"),
            "--proposal", proposal,
            "--hub-repo", "my-org/rdd-hub",
            "--output", str(output),
        ],
        env=env,
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert not output.exists()


def test_main_invalid_hub_repo_format(tmp_path):
    proposal = _make_proposal(tmp_path, "anything")
    output = tmp_path / "report.json"
    env = os.environ.copy()
    env.pop("RDDF_SKIP_CROSS_REPO_DETECTION", None)
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_PARENT / "detect_cross_repo_impact.py"),
            "--proposal", proposal,
            "--hub-repo", "no-slash-here",
            "--output", str(output),
        ],
        env=env,
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "must be <owner>" in r.stderr


def test_main_missing_proposal(tmp_path):
    env = os.environ.copy()
    env.pop("RDDF_SKIP_CROSS_REPO_DETECTION", None)
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_PARENT / "detect_cross_repo_impact.py"),
            "--proposal", str(tmp_path / "nope.md"),
            "--hub-repo", "my-org/hub",
            "--output", str(tmp_path / "out.json"),
        ],
        env=env,
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "not found" in r.stderr


def test_main_dry_run_no_side_effects(tmp_path):
    proposal = _make_proposal(tmp_path, "anything")
    output = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_PARENT / "detect_cross_repo_impact.py"),
            "--proposal", proposal,
            "--hub-repo", "my-org/hub",
            "--output", str(output),
            "--dry-run",
        ],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert not output.exists()
    assert "DRY-RUN" in r.stderr