"""Tests for skills/_lib/gate.py::_read_arch_handoff_paths priority chain.

Verifies the 3-level fallback: env-cache (13 fields) > handoff > hardcoded defaults.
Locks behavior for backward-compat with old 10-field cache files.

Run from repo root:
    python3 -m pytest tests/unit/test_gate_arch_handoff_paths.py -q
"""
import json
from pathlib import Path


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_env_cache_hits_first_when_discovered_fields_present(tmp_path):
    """When env-cache has discovered_*, those values win over handoff."""
    rddf = tmp_path / ".rddf" / "state"
    rddf.mkdir(parents=True)

    # env-cache: discovered_* present
    _write_json(rddf / ".env-cache.json", {
        "discovered_adr_dir": "documentation/decisions",
        "discovered_roadmap_path": "planning/roadmap.md",
        "discovered_architecture_dir": "docs/arch",
        "discovered_adr_pattern": "RFC-*.md",
    })
    # handoff: DIFFERENT values (should be ignored when env-cache has discovered_*)
    _write_json(rddf / ".arch-handoff.json", {
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
    })

    from skills._lib.gate import _read_arch_handoff_paths
    result = _read_arch_handoff_paths(str(tmp_path))
    assert result["adr_dir"] == "documentation/decisions"
    assert result["roadmap_path"] == "planning/roadmap.md"
    assert result["architecture_dir"] == "docs/arch"
    assert result["adr_pattern"] == "RFC-*.md"


def test_handoff_hits_when_env_cache_missing_discovered_fields(tmp_path):
    """When env-cache lacks discovered_* (old 10-field), fall back to handoff."""
    rddf = tmp_path / ".rddf" / "state"
    rddf.mkdir(parents=True)

    # env-cache: 10 fields only (legacy format, no discovered_*)
    _write_json(rddf / ".env-cache.json", {
        "timestamp": "1700000000",
        "branch": "master",
        "openspec_ver": "1.4.1",
    })
    _write_json(rddf / ".arch-handoff.json", {
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
    })

    from skills._lib.gate import _read_arch_handoff_paths
    result = _read_arch_handoff_paths(str(tmp_path))
    assert result["adr_dir"] == "docs/adr"
    assert result["roadmap_path"] == "roadmap.md"
    assert result["architecture_dir"] == "docs/architecture"
    assert result["adr_pattern"] == "ADR-*.md"


def test_default_hits_when_neither_cache_nor_handoff_present(tmp_path):
    """When both env-cache and handoff are missing, return hardcoded defaults."""
    from skills._lib.gate import _read_arch_handoff_paths
    result = _read_arch_handoff_paths(str(tmp_path))
    assert result["adr_dir"] == "docs/adr"
    assert result["roadmap_path"] == "roadmap.md"
    assert result["architecture_dir"] == "docs/architecture"
    assert result["adr_pattern"] == "ADR-*.md"