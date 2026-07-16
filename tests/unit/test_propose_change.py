"""Unit tests for skills/_lib/propose_change.py."""
import json
import pytest
from skills._lib import propose_change as pc


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / "proposal-suggestions.md").write_text("[]")
    return str(tmp_path)


@pytest.fixture
def project_with_suggestions(tmp_path):
    entries = [
        {"name": "c1", "status": "待创建"},
        {"name": "c2", "status": "created"},
    ]
    (tmp_path / "proposal-suggestions.md").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2)
    )
    return str(tmp_path)


class TestSetSuggestionStatus:
    def test_updates_status_for_matching_name(self, project_with_suggestions):
        result = pc.set_suggestion_status(project_with_suggestions, "c1", "skeleton")
        assert result is True
        with open(f"{project_with_suggestions}/proposal-suggestions.md") as f:
            entries = json.load(f)
        assert entries[0]["status"] == "skeleton"
        assert entries[1]["status"] == "created"  # unchanged

    def test_no_op_when_name_not_found(self, project_with_suggestions):
        result = pc.set_suggestion_status(project_with_suggestions, "c999", "skeleton")
        assert result is False

    def test_no_op_when_file_missing(self, project_root):
        import os
        os.remove(f"{project_root}/proposal-suggestions.md")
        result = pc.set_suggestion_status(project_root, "c1", "skeleton")
        assert result is False

    def test_preserves_other_fields(self, project_with_suggestions):
        # Add extra fields to first entry
        with open(f"{project_with_suggestions}/proposal-suggestions.md") as f:
            entries = json.load(f)
        entries[0]["phase"] = "phase-1"
        entries[0]["priority"] = "P2"
        with open(f"{project_with_suggestions}/proposal-suggestions.md", "w") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.write("\n")
        pc.set_suggestion_status(project_with_suggestions, "c1", "skeleton")
        with open(f"{project_with_suggestions}/proposal-suggestions.md") as f:
            entries = json.load(f)
        assert entries[0]["status"] == "skeleton"
        assert entries[0]["phase"] == "phase-1"  # preserved
        assert entries[0]["priority"] == "P2"   # preserved
        assert entries[0]["name"] == "c1"       # preserved

    def test_returns_false_on_malformed_json(self, tmp_path):
        bad_file = tmp_path / "proposal-suggestions.md"
        bad_file.write_text("not valid json {{{")
        result = pc.set_suggestion_status(str(tmp_path), "c1", "skeleton")
        assert result is False