from skills._lib.iteration.l2 import collect_l2_count
from skills._lib.iteration.store import load, save


def test_collect_l2_count_default_command(tmp_path, monkeypatch):
    """Default command output is parsed and written to iteration.json."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "echo 7")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [{"name": "c1", "status": "archived", "added_at": "2026-08-06T00:00:00+00:00"}],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "c1")

    assert warning is None
    data = load(str(tmp_path))
    assert data["changes"][0]["l2_violation_count_after"] == 7
    assert data["changes"][0]["l2_violation_kind"] == "sim_include_drv"


def test_collect_l2_count_missing_change(tmp_path, monkeypatch):
    """Missing change returns a warning but does not raise."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "echo 7")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "missing")

    assert warning is not None
    assert "missing" in warning


def test_collect_l2_count_invalid_output(tmp_path, monkeypatch):
    """Non-numeric command output returns a warning and does not touch file."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "echo not-a-number")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [{"name": "c1", "status": "archived", "added_at": "2026-08-06T00:00:00+00:00"}],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "c1")

    assert warning is not None
    assert "invalid result" in warning
    data = load(str(tmp_path))
    assert "l2_violation_count_after" not in data["changes"][0]


def test_collect_l2_count_command_failure(tmp_path, monkeypatch):
    """Command failure returns a warning and does not raise."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "exit 1")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [{"name": "c1", "status": "archived", "added_at": "2026-08-06T00:00:00+00:00"}],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "c1")

    assert warning is not None
