"""Unit tests for rfc_draft_schema.json + design_done_gate.check_rfc_draft."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
import jsonschema

# Add scripts to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "guide-design" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from design_done_gate import (  # noqa: E402
    _is_cross_repo_federation,
    _validate_rfc_draft,
    check_rfc_draft,
)


SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "skills" / "_lib" / "schemas" / "rfc_draft_schema.json"


def _valid_draft() -> dict:
    return {
        "version": "v1",
        "proposal_name": "auth-v2-redesign",
        "title": "[RFC] Redesign auth-v2 endpoints",
        "stakeholders": ["org/repo-a", "org/repo-b"],
        "gate": "Design-Gate",
        "contract_impact": "Breaking-Change",
        "created_at": "2026-08-19T10:00:00+00:00",
        "created_by": "test-user",
    }


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

def test_schema_is_valid_json():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator.check_schema(schema)


def test_valid_draft_passes_schema():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(_valid_draft(), schema)


def test_missing_field_fails_schema():
    draft = _valid_draft()
    del draft["title"]
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_wrong_version_fails_schema():
    draft = _valid_draft()
    draft["version"] = "v2"  # wrong schema version
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_invalid_stakeholder_format_fails_schema():
    draft = _valid_draft()
    draft["stakeholders"] = ["not-org-repo", "valid-org/repo"]
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_empty_stakeholders_fails_schema():
    draft = _valid_draft()
    draft["stakeholders"] = []
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_invalid_gate_fails_schema():
    draft = _valid_draft()
    draft["gate"] = "Custom-Gate"
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_invalid_impact_fails_schema():
    draft = _valid_draft()
    draft["contract_impact"] = "Maybe"
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_optional_fields_omitted_passes():
    draft = _valid_draft()
    # contract_draft_path and hub_issue_url are optional
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(draft, schema)  # should not raise


# ---------------------------------------------------------------------------
# check_rfc_draft tests
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """Create a minimal project layout: openspec/changes/<name>/ + .rddf/state/."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "openspec" / "changes").mkdir(parents=True)
    (root / ".rddf" / "state").mkdir(parents=True)
    os.environ["RDDF_PROJECT_ROOT"] = str(root)
    return root


def _write_change(root, name, category):
    change_dir = root / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "roadmap-meta.yaml").write_text(
        f"phase: v2.2\ncategory: {category}\nchange_type: feature\npriority: P0\n"
    )


def _write_draft(root, name, draft):
    draft_path = root / ".rddf" / "state" / f".rfc-draft-{name}.json"
    draft_path.write_text(json.dumps(draft))


def test_check_rfc_draft_returns_false_no_changes_dir(tmp_path):
    # No openspec/changes/ dir at all → no cross-repo proposals → pass
    import shutil
    root = tmp_path / "empty_proj"
    root.mkdir()
    os.environ["RDDF_PROJECT_ROOT"] = str(root)
    assert check_rfc_draft() is False


def test_check_rfc_draft_returns_false_no_cross_repo_changes(project_root):
    _write_change(project_root, "general-change", "general")
    assert check_rfc_draft() is False


def test_check_rfc_draft_returns_true_cross_repo_without_draft(project_root):
    _write_change(project_root, "my-rfc", "cross-repo-federation")
    assert check_rfc_draft() is True


def test_check_rfc_draft_returns_false_cross_repo_with_valid_draft(project_root):
    _write_change(project_root, "my-rfc", "cross-repo-federation")
    _write_draft(project_root, "my-rfc", _valid_draft())
    assert check_rfc_draft() is False


def test_check_rfc_draft_returns_true_cross_repo_with_invalid_draft(project_root):
    _write_change(project_root, "my-rfc", "cross-repo-federation")
    # Invalid draft (missing required field)
    draft = _valid_draft()
    del draft["title"]
    _write_draft(project_root, "my-rfc", draft)
    assert check_rfc_draft() is True


def test_check_rfc_draft_mixed_proposals_blocks_if_any_missing(project_root):
    _write_change(project_root, "general-change", "general")
    _write_change(project_root, "rfc-with-draft", "cross-repo-federation")
    _write_draft(project_root, "rfc-with-draft", _valid_draft())
    _write_change(project_root, "rfc-no-draft", "cross-repo-federation")
    # no draft for rfc-no-draft → gate blocks
    assert check_rfc_draft() is True


# ---------------------------------------------------------------------------
# _is_cross_repo_federation tests
# ---------------------------------------------------------------------------

def test_is_cross_repo_federation_true(project_root):
    _write_change(project_root, "rfc", "cross-repo-federation")
    assert _is_cross_repo_federation(str(project_root), "rfc") is True


def test_is_cross_repo_federation_false(project_root):
    _write_change(project_root, "general", "general")
    assert _is_cross_repo_federation(str(project_root), "general") is False


def test_is_cross_repo_federation_missing_returns_false(project_root):
    assert _is_cross_repo_federation(str(project_root), "nonexistent") is False