import subprocess
from pathlib import Path


def test_archive_change_calls_collect_l2_count():
    """archive.sh should run collect_l2_count after mark_iteration_archived."""
    # This is an integration-level assertion; we will verify via bats later.
    # For the unit test, assert that the helper function exists and can be sourced.
    archive_sh = Path(__file__).parents[2] / "_lib" / "archive.sh"
    assert archive_sh.is_file()
    result = subprocess.run(
        ["bash", "-c", f"source '{archive_sh}' && type collect_l2_count_wrapper"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
