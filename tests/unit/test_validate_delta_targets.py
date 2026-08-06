"""Unit tests for validate_delta_targets.py."""
import pytest
import subprocess
from pathlib import Path
from typing import Optional


VALIDATOR_SCRIPT = Path(__file__).parent.parent.parent / "_lib" / "validate_delta_targets.py"


def run_validator(change_dir: Path, change_name: str) -> tuple[int, str]:
    result = subprocess.run(
        ["python3", str(VALIDATOR_SCRIPT), change_name],
        capture_output=True, text=True, cwd=change_dir,
    )
    return result.returncode, result.stdout + result.stderr


def setup_change_with_spec(tmp_path: Path, cap_name: str, spec_content: str,
                            main_specs: Optional[dict] = None) -> Path:
    """Create change dir + spec.md + optional main specs/."""
    change = tmp_path / f"openspec/changes/test-change/specs/{cap_name}"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(spec_content)
    if main_specs:
        for ms_name, ms_content in main_specs.items():
            ms = tmp_path / f"openspec/specs/{ms_name}"
            ms.mkdir(parents=True)
            (ms / "spec.md").write_text(ms_content)
    return tmp_path


def test_added_section_passes_when_no_main_spec(tmp_path):
    setup_change_with_spec(tmp_path, "new-cap", """\
# new-cap Specification
## ADDED Requirements
### Requirement: x
Body.
""")
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0  # ADDED is OK without main spec


def test_modified_section_fails_when_target_spec_missing(tmp_path):
    setup_change_with_spec(tmp_path, "new-cap", """\
# new-cap Specification
## MODIFIED Requirements
### Requirement: x
Body modifying nonexistent-target.
""")
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "nonexistent-target" in out or "MODIFIED" in out


def test_modified_section_passes_when_target_spec_exists(tmp_path):
    setup_change_with_spec(
        tmp_path, "new-cap",
        spec_content="""\
# new-cap Specification
## MODIFIED Requirements
### Requirement: x

modifies: existing-target

Body modifying existing-target.
""",
        main_specs={"existing-target": "# existing-target Specification\n## Purpose\nTBD\n"},
    )
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_renamed_section_fails_when_source_spec_missing(tmp_path):
    setup_change_with_spec(tmp_path, "new-cap", """\
# new-cap Specification
## RENAMED Requirements
### Requirement: old-name -> new-name
Body.
""")
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "RENAMED" in out or "old-name" in out


def test_v2_g_gpu_client_meyers_fallback_regression(tmp_path):
    """Regression test: v2 spec had MODIFIED section for non-existent capability.
    This validator MUST catch it before archive abort."""
    setup_change_with_spec(tmp_path, "shim-default-init-fallback", """\
# shim-default-init-fallback Specification
## MODIFIED Requirements
### Requirement: shim functions return SUCCESS instead of NOT_INITIALIZED
Body.
""")
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "MODIFIED" in out
