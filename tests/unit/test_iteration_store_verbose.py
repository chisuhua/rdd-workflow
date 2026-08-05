"""Unit tests for _read_unlocked_verbose in iteration.store
(fix-rddf-status-corrupt-message).

TDD Step 1: write failing tests. After implementation, all should pass.

Tests cover 3 cases:
  - missing: file doesn't exist → (None, None)
  - schema-invalid: returns error with path
  - valid: returns (data, None)
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills._lib.iteration import store  # noqa: E402


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestReadUnlockedVerbose:
    def test_missing_file_returns_none_none(self, tmp_path):
        """GIVEN file doesn't exist
        WHEN _read_unlocked_verbose is called
        THEN returns (None, None)."""
        result = store._read_unlocked_verbose(str(tmp_path / "missing.json"))
        assert result == (None, None)

    def test_valid_file_returns_data(self, tmp_path):
        """GIVEN a well-formed iteration.json
        WHEN _read_unlocked_verbose is called
        THEN returns (data, None)."""
        path = tmp_path / "iteration.json"
        _write(path, json.dumps({
            "version": 4,
            "updated_at": "2026-08-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [],
        }))
        data, err = store._read_unlocked_verbose(str(path))
        assert err is None
        assert data["version"] == 4

    def test_schema_invalid_returns_error_with_path(self, tmp_path):
        """GIVEN a schema-invalid iteration.json (per-change entry with extra 'updated_at')
        WHEN _read_unlocked_verbose is called
        THEN returns (None, error) where error mentions 'schema validation failed'
        AND contains the JSON path to the bad entry."""
        path = tmp_path / "iteration.json"
        _write(path, json.dumps({
            "version": 4,
            "updated_at": "2026-08-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {
                    "name": "x",
                    "status": "proposed",
                    "added_at": "2026-08-01T00:00:00+00:00",
                    "updated_at": "2026-08-05T11:00:00+00:00",  # not allowed
                }
            ],
        }))
        data, err = store._read_unlocked_verbose(str(path))
        assert data is None
        assert err is not None
        assert "schema validation failed" in err
        assert "changes" in err
        assert "0" in err
