"""Unit tests for read_iteration_or_corrupt (fix-rddf-status-corrupt-message).

TDD Step 1: write failing tests. After implementation, all should pass.

Tests cover 4 cases:
  - missing: file doesn't exist → (None, None)
  - invalid JSON: file has syntax error → (None, "invalid JSON: ...")
  - schema-invalid: file has extra field that per-change item schema rejects
    → (None, "schema validation failed at ...: ...")
  - valid: file is well-formed → (data, None)
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills._lib import state_reader  # noqa: E402


def _write_iteration(project_root: Path, content: str) -> Path:
    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    iter_path = state_dir / "iteration.json"
    iter_path.write_text(content)
    return iter_path


class TestReadIterationOrCorrupt:
    def test_missing_file_returns_none_none(self, tmp_path):
        """GIVEN iteration.json does not exist
        WHEN read_iteration_or_corrupt is called
        THEN it returns (None, None) — caller distinguishes via os.path.isfile."""
        result = state_reader.read_iteration_or_corrupt(str(tmp_path))
        assert result == (None, None)

    def test_invalid_json_returns_error(self, tmp_path):
        """GIVEN iteration.json has a JSON syntax error (trailing comma)
        WHEN read_iteration_or_corrupt is called
        THEN it returns (None, error) where error mentions 'invalid JSON'."""
        _write_iteration(tmp_path, '{"version": 4, "changes": [],}')  # trailing comma
        data, err = state_reader.read_iteration_or_corrupt(str(tmp_path))
        assert data is None
        assert err is not None
        assert "invalid JSON" in err

    def test_schema_invalid_returns_error_with_path(self, tmp_path):
        """GIVEN iteration.json has a per-change entry with an extra 'updated_at' field
        WHEN read_iteration_or_corrupt is called
        THEN it returns (None, error) where error mentions 'schema validation failed'
        AND contains the JSON path to the bad entry."""
        # Replicate the exact bug pattern from this session:
        # changes[0] has an extra 'updated_at' field that the per-change
        # item schema rejects (additionalProperties: false).
        content = json.dumps({
            "version": 4,
            "updated_at": "2026-08-05T10:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {
                    "name": "test-change",
                    "status": "proposed",
                    "added_at": "2026-08-01T00:00:00+00:00",
                    "updated_at": "2026-08-05T11:00:00+00:00",  # not allowed per-item
                }
            ],
        })
        _write_iteration(tmp_path, content)
        data, err = state_reader.read_iteration_or_corrupt(str(tmp_path))
        assert data is None
        assert err is not None
        assert "schema validation failed" in err
        # Path should include the change index
        assert "changes" in err
        assert "0" in err

    def test_valid_file_returns_data(self, tmp_path):
        """GIVEN iteration.json is well-formed
        WHEN read_iteration_or_corrupt is called
        THEN it returns (data, None)."""
        content = json.dumps({
            "version": 4,
            "updated_at": "2026-08-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {
                    "name": "test-change",
                    "status": "proposed",
                    "added_at": "2026-08-01T00:00:00+00:00",
                }
            ],
        })
        _write_iteration(tmp_path, content)
        data, err = state_reader.read_iteration_or_corrupt(str(tmp_path))
        assert err is None
        assert data is not None
        assert data["version"] == 4
        assert data["changes"][0]["name"] == "test-change"

    def test_readonly_no_backup_files_created(self, tmp_path):
        """GIVEN a schema-invalid iteration.json
        WHEN read_iteration_or_corrupt is called
        THEN no .corrupt.<ts> backup is written (read-only contract)."""
        content = json.dumps({
            "version": 4,
            "updated_at": "2026-08-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {
                    "name": "x",
                    "status": "proposed",
                    "added_at": "2026-08-01T00:00:00+00:00",
                    "updated_at": "2026-08-05T11:00:00+00:00",
                }
            ],
        })
        _write_iteration(tmp_path, content)
        state_reader.read_iteration_or_corrupt(str(tmp_path))
        # No backup files should be created
        backups = list((tmp_path / ".rddf" / "state").glob("*.corrupt.*"))
        assert backups == [], f"Read-only contract violated: {backups} created"
