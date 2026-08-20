"""Tests for validate_fragment_refs — 8 rules R1-R8 (Task 6 / T14).

Per Metis review: R8 fixed to actually trigger (was using Set dedup so never fired).
Per Oracle recommendation: R4 regex strict pattern `phase-\\d+(\\.\\d+)?`.
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from _lib.roadmap_validate import validate_fragment_refs, ValidationError


@pytest.fixture
def setup_with_main_doc(tmp_path):
    """Create .rddf/roadmap/ with main doc + 3 fragments (1 valid, 1 invalid R1, 1 invalid R3)."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (base / "features").mkdir(parents=True)
    # Main doc with phase-1, phase-2 only (no phase-99)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-1 | ... |\n| phase-2 | ... |\n"
    )
    # Valid fragment
    (base / "phases" / "phase-1.md").write_text(
        "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    # R1 violation: phase_refs references phase-99 not in main doc
    (base / "features" / "feat-broken.md").write_text(
        "---\nid: feat-broken\nkind: feature\nstatus: active\nphase_refs: [phase-99]\n主题: T\n---\n\nbody"
    )
    # R3 violation: kind=invalid-value
    (base / "phases" / "phase-bad-kind.md").write_text(
        "---\nid: phase-bad-kind\nkind: invalid-value\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    return tmp_path


def test_r1_phase_refs_must_exist_in_main_doc(setup_with_main_doc):
    """R1: feature.phase_refs[] each id must exist in main doc phase table."""
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r1_errors = [e for e in errors if e.rule == "R1"]
    assert len(r1_errors) == 1
    assert r1_errors[0].fragment_id == "feat-broken"
    assert "phase-99" in r1_errors[0].message


def test_r2_id_must_be_unique(setup_with_main_doc, tmp_path):
    """R2: fragment ids must be unique across phases/features."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    # Create duplicate id in features (phase-1 already exists in phases)
    (base / "features" / "dup.md").write_text(
        "---\nid: phase-1\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r2_errors = [e for e in errors if e.rule == "R2"]
    assert len(r2_errors) >= 1
    assert r2_errors[0].fragment_id == "phase-1"


def test_r3_kind_must_be_enum(setup_with_main_doc):
    """R3: kind must be 'phase' or 'feature'."""
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r3_errors = [e for e in errors if e.rule == "R3"]
    assert len(r3_errors) == 1
    assert r3_errors[0].fragment_id == "phase-bad-kind"


def test_r4_phase_id_naming(setup_with_main_doc, tmp_path):
    """R4: phase id must match pattern phase-N(.M)?"""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "phases" / "bad-name.md").write_text(
        "---\nid: not-a-phase\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r4_errors = [e for e in errors if e.rule == "R4"]
    assert len(r4_errors) == 1
    assert r4_errors[0].fragment_id == "not-a-phase"


def test_r4_strict_pattern_rejects_phase_1_2_nesting(tmp_path):
    """R4 strict (per Oracle recommendation): pattern is `phase-N(.M)?`, rejects `phase-1-2` and `phase-1.2.3`."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-1 | T | active | | |\n| phase-2 | T | active | | |\n"
    )
    for bad_id in ("phase-1-2", "phase-1.2.3", "phase-1-"):
        (base / "phases" / f"{bad_id}.md").write_text(
            f"---\nid: {bad_id}\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
        )
    errors = validate_fragment_refs(str(tmp_path))
    r4 = [e for e in errors if e.rule == "R4"]
    assert len(r4) == 3, f"R4 should reject all 3 nested patterns, got {len(r4)}: {r4}"


def test_r4_strict_pattern_accepts_phase_2_1_subphase(tmp_path):
    """R4 strict accepts sub-phase id `phase-2.1` (single-level only)."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-2 | T | active | | |\n| phase-2.1 | T | active | | |\n"
    )
    (base / "phases" / "phase-2.1.md").write_text(
        "---\nid: phase-2.1\nkind: phase\nstatus: active\nphase_refs: [phase-2]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(tmp_path))
    r4 = [e for e in errors if e.rule == "R4"]
    assert r4 == [], f"phase-2.1 should match strict pattern, got R4 errors: {r4}"


def test_r5_feature_must_have_phase_refs(setup_with_main_doc, tmp_path):
    """R5: kind=feature must have non-empty phase_refs."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "features" / "feat-no-refs.md").write_text(
        "---\nid: feat-no-refs\nkind: feature\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r5_errors = [e for e in errors if e.rule == "R5"]
    assert len(r5_errors) == 1
    assert r5_errors[0].fragment_id == "feat-no-refs"
    assert r5_errors[0].severity == "WARNING"


def test_r6_phase_must_be_in_main_doc(setup_with_main_doc, tmp_path):
    """R6: phase fragment id must be in main doc phase table."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "phases" / "phase-99.md").write_text(
        "---\nid: phase-99\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r6_errors = [e for e in errors if e.rule == "R6"]
    assert len(r6_errors) == 1
    assert r6_errors[0].fragment_id == "phase-99"


def test_r7_fragments_dir_missing_warn(tmp_path):
    """R7: warn (not error) when fragments_dir missing (backward compat v1 handoff)."""
    errors = validate_fragment_refs(str(tmp_path / "nonexistent"))
    r7_errors = [e for e in errors if e.rule == "R7"]
    assert len(r7_errors) == 1
    assert r7_errors[0].severity == "WARNING"


def test_r8_duplicate_phase_id_in_main_doc(setup_with_main_doc, tmp_path):
    """R8: main doc phase table must not have duplicate phase ids (Per Metis: was always-false bug, fixed)."""
    md = setup_with_main_doc / ".rddf" / "roadmap.md"
    md.write_text("# Roadmap\n\n| phase-1 | ... |\n| phase-1 | ... |\n")
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r8_errors = [e for e in errors if e.rule == "R8"]
    assert len(r8_errors) == 1, f"R8 should fire on duplicate phase-1, got {len(r8_errors)}"
    assert "phase-1" in r8_errors[0].message
    assert r8_errors[0].severity == "CRITICAL"


def test_valid_setup_no_critical_errors(setup_with_main_doc, tmp_path):
    """Sanity: a fully valid setup yields no CRITICAL errors (only possible warnings)."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    # Remove the bad ones
    (base / "features" / "feat-broken.md").unlink()
    (base / "phases" / "phase-bad-kind.md").unlink()
    # Add a valid feature
    (base / "features" / "feat-good.md").write_text(
        "---\nid: feat-good\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    critical = [e for e in errors if e.severity == "CRITICAL"]
    assert critical == [], f"Valid setup should have no CRITICAL, got: {critical}"


def test_r1_normal_case_passes(setup_with_main_doc):
    """R1 normal: feature referencing valid phase passes (no R1 errors)."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "features" / "feat-broken.md").unlink()
    (base / "phases" / "phase-bad-kind.md").unlink()
    (base / "features" / "feat-good.md").write_text(
        "---\nid: feat-good\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r1 = [e for e in errors if e.rule == "R1"]
    assert r1 == [], f"R1 should not fire on valid setup, got: {r1}"


def test_r5_normal_feature_with_refs_no_warning(setup_with_main_doc):
    """R5 normal: feature with phase_refs has no R5 warning."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "features" / "feat-broken.md").unlink()
    (base / "phases" / "phase-bad-kind.md").unlink()
    (base / "features" / "feat-good.md").write_text(
        "---\nid: feat-good\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc))
    r5 = [e for e in errors if e.rule == "R5"]
    assert r5 == [], f"R5 should not warn on feature with refs, got: {r5}"
