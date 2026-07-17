"""Unit tests for validate_baseline.py."""
import pytest
import subprocess
import tempfile
import os
import yaml
from pathlib import Path


VALIDATOR_SCRIPT = Path(__file__).parent.parent.parent / "skills" / "propose" / "scripts" / "validate_baseline.py"


def run_validator(change_dir: Path, change_name: str) -> tuple[int, str]:
    """Run validate_baseline.py as subprocess. Return (exit_code, stdout+stderr)."""
    result = subprocess.run(
        ["python3", str(VALIDATOR_SCRIPT), change_name],
        capture_output=True, text=True, cwd=change_dir,
    )
    return result.returncode, result.stdout + result.stderr


def make_change_with_baseline(tmpdir: Path, baseline: dict) -> Path:
    """Create a fake change dir with .openspec.yaml containing baseline."""
    openspec_dir = tmpdir / "openspec/changes/test-change"
    openspec_dir.mkdir(parents=True)
    spec_dir = openspec_dir / "specs/test-cap"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# test-cap Specification\n## Purpose\nTBD\n")
    yaml_content = {
        "schema": "spec-driven",
        "name": "test-change",
        "baseline": baseline,
    }
    (openspec_dir / ".openspec.yaml").write_text(yaml.dump(yaml_content))
    return tmpdir


def test_file_exists_claim_passes_when_path_exists(tmp_path):
    fake_file = tmp_path / "src/exists.cpp"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("// exists")
    make_change_with_baseline(tmp_path, {
        "exists-file": f"file-exists:{fake_file.relative_to(tmp_path)}"
    })
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_file_exists_claim_fails_when_path_missing(tmp_path):
    make_change_with_baseline(tmp_path, {
        "missing-file": "file-exists:does/not/exist.cpp"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "does/not/exist.cpp" in out
    assert "file-exists" in out


def test_symbol_exists_claim_passes_when_match(tmp_path):
    src = tmp_path / "src/foo.cpp"
    src.parent.mkdir(parents=True)
    src.write_text("class FooBar {}")
    make_change_with_baseline(tmp_path, {
        "symbol": f"symbol-exists:{src.relative_to(tmp_path)}:FooBar"
    })
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_symbol_exists_claim_fails_when_no_match(tmp_path):
    src = tmp_path / "src/foo.cpp"
    src.parent.mkdir(parents=True)
    src.write_text("class Bar {}")
    make_change_with_baseline(tmp_path, {
        "symbol": f"symbol-exists:{src.relative_to(tmp_path)}:FooBar"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "FooBar" in out


def test_git_history_claim_passes_for_existing_symbol(tmp_path):
    # Set up minimal git repo with a commit
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("class RealSymbol {}")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add real symbol"], cwd=tmp_path, check=True)

    make_change_with_baseline(tmp_path, {
        "history": "git-history:RealSymbol"
    })
    rc, _ = run_validator(tmp_path, "test-change")
    assert rc == 0


def test_free_text_baseline_passes_with_warning(tmp_path):
    make_change_with_baseline(tmp_path, {
        "free-text": "this is just a description, no structured claim"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 0  # pass
    assert "unverifiable" in out.lower() or "skipped" in out.lower()


def test_v1_g_gpu_client_baseline_fails_regression(tmp_path):
    """Regression test: v1 spec claimed 'CudaStub g_cuda_stub; exists' but it didn't.
    This validator MUST catch it."""
    # Set up a git repo with a file that does NOT contain 'CudaStub g_cuda_stub;'
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    stub = tmp_path / "src/test_fixture/cuda_stub.cpp"
    stub.parent.mkdir(parents=True)
    stub.write_text("// CudaStub class definition\nclass CudaStub {};\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add stub"], cwd=tmp_path, check=True)

    make_change_with_baseline(tmp_path, {
        "g_cuda_stub static instance": "git-history:CudaStub g_cuda_stub"
    })
    rc, out = run_validator(tmp_path, "test-change")
    assert rc == 1
    assert "CudaStub g_cuda_stub" in out
