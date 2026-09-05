"""Unit tests for _lib/shim_usage.py (Wave 2 telemetry)."""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

from _lib.shim_usage import record_shim_usage, count_shim_usage_recent_days


def test_record_shim_usage_creates_file(tmp_path):
    record_shim_usage(source="guide-design", args=["change-foo"], redirected_to="rddf builder", project_root=str(tmp_path))
    log = tmp_path / ".rddf" / "state" / ".shim-usage.jsonl"
    assert log.exists()
    content = log.read_text()
    entry = json.loads(content.strip().splitlines()[0])
    assert entry["source"] == "guide-design"
    assert entry["args"] == ["change-foo"]
    assert entry["redirected_to"] == "rddf builder"
    assert "timestamp" in entry


def test_record_shim_usage_appends_multiple(tmp_path):
    for i in range(3):
        record_shim_usage(source=f"guide-{i}", args=[f"change-{i}"], redirected_to="rddf builder", project_root=str(tmp_path))
    log = tmp_path / ".rddf" / "state" / ".shim-usage.jsonl"
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 3
    sources = [json.loads(line)["source"] for line in lines]
    assert sources == ["guide-0", "guide-1", "guide-2"]


def test_record_shim_usage_creates_state_dir_if_missing(tmp_path):
    assert not (tmp_path / ".rddf/state").exists()
    record_shim_usage(source="guide-design", args=[], redirected_to="rddf builder", project_root=str(tmp_path))
    assert (tmp_path / ".rddf/state").is_dir()
    assert (tmp_path / ".rddf/state/.shim-usage.jsonl").is_file()


def test_count_shim_usage_recent_days_zero_when_no_log(tmp_path):
    assert count_shim_usage_recent_days(days=7, project_root=str(tmp_path)) == 0


def test_count_shim_usage_recent_days_excludes_old_entries(tmp_path):
    log = tmp_path / ".rddf" / "state" / ".shim-usage.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    with open(log, "w") as f:
        f.write(json.dumps({"timestamp": old, "source": "guide-design", "args": [], "redirected_to": "rddf builder"}) + "\n")
        f.write(json.dumps({"timestamp": recent, "source": "guide-plan", "args": [], "redirected_to": "rddf builder"}) + "\n")
    assert count_shim_usage_recent_days(days=7, project_root=str(tmp_path)) == 1


def test_count_shim_usage_recent_days_includes_within_window(tmp_path):
    log = tmp_path / ".rddf" / "state" / ".shim-usage.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as f:
        for i in range(5):
            ts = (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()
            f.write(json.dumps({"timestamp": ts, "source": "guide-ship", "args": [], "redirected_to": "rddf builder"}) + "\n")
    assert count_shim_usage_recent_days(days=7, project_root=str(tmp_path)) == 5


def test_record_shim_usage_handles_corrupted_lines(tmp_path):
    log = tmp_path / ".rddf" / "state" / ".shim-usage.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as f:
        f.write("not-json-line\n")
        f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "source": "guide-design", "args": [], "redirected_to": "rddf builder"}) + "\n")
    record_shim_usage(source="guide-plan", args=[], redirected_to="rddf builder", project_root=str(tmp_path))
    assert count_shim_usage_recent_days(days=7, project_root=str(tmp_path)) == 2