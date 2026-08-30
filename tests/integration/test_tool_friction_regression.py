import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "skills" / "rdd-workflow-brainstorm" / "scripts" / "pre_tool_use_check.sh"


def run_guard(*args, **kw):
    env = dict(kw.pop("env", {}))
    env["PATH"] = "/usr/bin:/bin"
    return subprocess.run(
        ["bash", str(GUARD), *args], capture_output=True, text=True, env=env,
    )


def test_edit_oldstring_mismatch_triggers_read_fallback():
    proc = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "stale"})
    assert "STALE-LIKELY" in proc.stderr


def test_write_existing_file_triggers_edit_or_read_write():
    proc = run_guard("write", "a.md", env={"RDDF_GUARD_TARGET_EXISTS": "1"})
    assert "EXISTS" in proc.stderr


def test_read_hardcoded_offset_triggers_dynamic_offset():
    proc = run_guard("read", "a.py", "999")
    assert "OFFSET" in proc.stderr


def test_edit_after_read_under_5s_no_warning():
    proc = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "fresh"})
    assert proc.stderr.strip() == ""


def test_write_new_file_no_warning():
    proc = run_guard("write", "new.md", env={"RDDF_GUARD_TARGET_EXISTS": "0"})
    assert proc.stderr.strip() == ""


def test_read_with_offset_after_documented_count_no_warning():
    proc = run_guard("read", "a.py")
    assert proc.stderr.strip() == ""


def test_repeated_identical_tool_call_collapses_to_single_warning():
    # two consecutive stale edits → exactly one warning line total
    p1 = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "stale"})
    p2 = run_guard("edit", "a.md", env={"RDDF_GUARD_FILE_STATE": "stale"})
    assert p1.stderr.count("STALE-LIKELY") == 1
    assert p2.stderr.count("STALE-LIKELY") == 1
