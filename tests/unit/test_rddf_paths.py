"""Unit tests for `_lib/core/rddf_paths.py`.

The resolver is the single answer to "where do the two proposal index files
live", so its precedence rules are pinned here: `.rddf/` wins when both
copies exist, a legacy project-root copy is still honored, and a project with
neither gets the canonical `.rddf/` path.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from _lib.core.rddf_paths import (  # noqa: E402
    APPROVED_NAME,
    SUGGESTIONS_NAME,
    approved_file,
    candidates,
    is_rddf_hosted,
    link_prefix,
    resolve,
    suggestions_file,
)


def test_candidates_are_canonical_first(tmp_path: Path):
    assert candidates(str(tmp_path), SUGGESTIONS_NAME) == [
        str(tmp_path / ".rddf" / SUGGESTIONS_NAME),
        str(tmp_path / SUGGESTIONS_NAME),
    ]


def test_missing_files_resolve_to_canonical_rddf_path(tmp_path: Path):
    assert suggestions_file(str(tmp_path)) == str(tmp_path / ".rddf" / SUGGESTIONS_NAME)
    assert approved_file(str(tmp_path)) == str(tmp_path / ".rddf" / APPROVED_NAME)


def test_rddf_copy_wins_over_legacy_root_copy(tmp_path: Path):
    (tmp_path / ".rddf").mkdir()
    (tmp_path / ".rddf" / APPROVED_NAME).write_text("# canon\n")
    (tmp_path / APPROVED_NAME).write_text("# legacy\n")
    assert approved_file(str(tmp_path)) == str(tmp_path / ".rddf" / APPROVED_NAME)


def test_legacy_root_copy_is_still_resolved(tmp_path: Path):
    (tmp_path / SUGGESTIONS_NAME).write_text("# legacy\n")
    assert suggestions_file(str(tmp_path)) == str(tmp_path / SUGGESTIONS_NAME)


def test_is_rddf_hosted_only_for_direct_rddf_child(tmp_path: Path):
    assert is_rddf_hosted(str(tmp_path / ".rddf" / APPROVED_NAME)) is True
    assert is_rddf_hosted(str(tmp_path / APPROVED_NAME)) is False
    assert is_rddf_hosted(str(tmp_path / ".rddf" / "nested" / APPROVED_NAME)) is False


def test_link_prefix_relative_for_rddf_hosted_index(tmp_path: Path):
    assert link_prefix(str(tmp_path / ".rddf" / APPROVED_NAME)) == "improvements/"


def test_link_prefix_root_relative_for_legacy_index(tmp_path: Path):
    assert link_prefix(str(tmp_path / APPROVED_NAME)) == ".rddf/improvements/"
