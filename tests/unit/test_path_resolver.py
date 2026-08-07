"""Tests for path_resolver — must always return real _lib/ paths.

Note: skill dir name `rdd-doctor` has a hyphen, which Python does not allow
in dotted imports. We inject the scripts dir into sys.path and import the
module by its basename. Same pattern used by other hyphenated skills in this
repo (see skills/rdd-env-check/SKILL.md for precedent).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Inject scripts dir so we can import path_resolver without the dotted path
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from path_resolver import (  # noqa: E402  (sys.path manipulation above is intentional)
    LibPathNotFoundError,
    resolve_real_lib_path,
)


def test_resolves_real_lib_dir_not_shim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies path resolver returns the real _lib/ dir, not the skills/_lib/ shim."""
    # Setup: real _lib/ + shim skills/_lib/ (shim has same file but wrong content)
    real_lib = tmp_path / "_lib"
    real_lib.mkdir()
    (real_lib / "schemas").mkdir()
    (real_lib / "schemas" / "iteration_schema.json").write_text('{"$id":"REAL"}')

    shim_lib = tmp_path / "skills" / "_lib"
    shim_lib.mkdir(parents=True)
    (shim_lib / "schemas").mkdir()
    (shim_lib / "schemas" / "iteration_schema.json").write_text('{"$id":"SHIM"}')

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    result = resolve_real_lib_path("schemas/iteration_schema.json")
    assert result.exists()
    assert result.read_text() == '{"$id":"REAL"}'


def test_raises_when_real_lib_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No _lib/ directory must raise, not silently fall back to shim."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    with pytest.raises(LibPathNotFoundError) as exc_info:
        resolve_real_lib_path("schemas/iteration_schema.json")
    assert "real _lib/" in str(exc_info.value).lower()


def test_never_returns_shim_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When BOTH real _lib/ and skills/_lib/ shim exist, only real is returned."""
    real_lib = tmp_path / "_lib"
    real_lib.mkdir()
    (real_lib / "schemas").mkdir()
    (real_lib / "schemas" / "foo.json").write_text('"real"')

    shim_lib = tmp_path / "skills" / "_lib"
    shim_lib.mkdir(parents=True)
    (shim_lib / "schemas").mkdir()
    (shim_lib / "schemas" / "foo.json").write_text('"shim"')

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    result = resolve_real_lib_path("schemas/foo.json")
    assert "shim" not in result.read_text()