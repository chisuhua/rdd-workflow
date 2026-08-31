import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "skills" / "rdd-workflow-brainstorm" / "scripts" / "pre_tool_use_check.sh"


def run_guard(*args, env_extra=None):
    env = dict(os.environ)
    env["RDDF_GUARD_FILE_STATE"] = "stale"  # simulated file state marker
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["bash", str(GUARD), *args],
        capture_output=True, text=True, env=env,
    )
    return proc


def test_guard_warns_on_stale_edit():
    proc = run_guard("edit", "file_x")
    assert proc.returncode == 0, proc.stderr
    assert "STALE-LIKELY" in proc.stderr


def test_guard_warns_on_write_existing():
    proc = run_guard("write", "file_x", env_extra={"RDDF_GUARD_TARGET_EXISTS": "1"})
    assert proc.returncode == 0, proc.stderr
    assert "EXISTS" in proc.stderr


def test_guard_warns_on_read_offset():
    proc = run_guard("read", "file_y", "1104")
    assert proc.returncode == 0, proc.stderr
    assert "OFFSET" in proc.stderr
