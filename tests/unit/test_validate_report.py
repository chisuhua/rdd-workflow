"""Tests for skills._lib.validate_report — openspec validate JSON view module (ADR-0015)."""
import json
import os
import tempfile

import pytest


def _sample_passing_raw():
    return {
        "items": [
            {"id": "ok-cap", "type": "spec", "valid": True, "issues": []},
            {"id": "ok-cap-2", "type": "spec", "valid": True, "issues": []},
        ],
        "summary": {
            "totals": {"items": 2, "passed": 2, "failed": 0},
            "byType": {"spec": {"items": 2, "passed": 2, "failed": 0}},
        },
        "version": "1.0",
    }


def _sample_failing_raw():
    return {
        "items": [
            {"id": "ok-cap", "type": "spec", "valid": True, "issues": []},
            {
                "id": "broken-spec",
                "type": "spec",
                "valid": False,
                "issues": [{"level": "ERROR", "path": "file", "message": "Missing ## Purpose"}],
            },
            {
                "id": "broken-spec-2",
                "type": "spec",
                "valid": False,
                "issues": [{"level": "ERROR", "path": "file", "message": "Missing ## Requirements"}],
            },
        ],
        "summary": {
            "totals": {"items": 3, "passed": 1, "failed": 2},
            "byType": {"spec": {"items": 3, "passed": 1, "failed": 2}},
        },
        "version": "1.0",
    }


def test_normalize_report_passes_when_no_failures():
    """normalize_report sets passed=True when summary.totals.failed == 0."""
    from skills._lib.validate_report import normalize_report

    out = normalize_report(_sample_passing_raw(), openspec_cli_version="1.4.1")
    assert out["passed"] is True
    assert out["version"] == 1
    assert out["openspec_cli_version"] == "1.4.1"
    assert out["failed_items"] == []
    assert out["summary"]["totals"]["passed"] == 2


def test_normalize_report_extracts_only_failed_items():
    """normalize_report failed_items contains every items[] entry with valid==False."""
    from skills._lib.validate_report import normalize_report

    out = normalize_report(_sample_failing_raw(), openspec_cli_version="1.4.1")
    assert out["passed"] is False
    assert len(out["failed_items"]) == 2
    ids = {fi["id"] for fi in out["failed_items"]}
    assert ids == {"broken-spec", "broken-spec-2"}
    # And every entry preserves issues verbatim
    for fi in out["failed_items"]:
        assert isinstance(fi["issues"], list)
        assert fi["issues"][0]["level"] == "ERROR"


def test_write_and_load_report_round_trip():
    """write_report persists a file load_report can read back."""
    from skills._lib.validate_report import write_report, load_report

    with tempfile.TemporaryDirectory() as tmp:
        written_path = write_report(tmp, _sample_failing_raw(), openspec_cli_version="1.4.1")
        assert os.path.isfile(written_path)
        # Path layout: <project_root>/.rddf/state/openspec-validate.json
        assert written_path.endswith(os.path.join(".rddf", "state", "openspec-validate.json"))

        loaded = load_report(tmp)
        assert loaded is not None
        assert loaded["passed"] is False
        assert loaded["openspec_cli_version"] == "1.4.1"
        assert len(loaded["failed_items"]) == 2


def test_load_report_returns_none_when_absent():
    """load_report returns None for missing files (not an exception)."""
    from skills._lib.validate_report import load_report

    with tempfile.TemporaryDirectory() as tmp:
        assert load_report(tmp) is None


def test_validate_report_dataclass_from_dict_and_to_dict():
    """ValidateReport round-trips through from_dict / to_dict without losing fields."""
    from skills._lib.validate_report import ValidateReport, normalize_report

    raw_norm = normalize_report(_sample_passing_raw(), openspec_cli_version="1.4.1")

    report = ValidateReport.from_dict(raw_norm)
    assert report.passed is True
    assert report.openspec_cli_version == "1.4.1"
    assert report.version == 1
    assert report.summary["totals"]["passed"] == 2
    assert report.failed_items == []

    roundtrip = report.to_dict()
    assert roundtrip == raw_norm


def test_write_report_is_atomic():
    """write_report does not leave .tmp files in the project root."""
    from skills._lib.validate_report import write_report

    with tempfile.TemporaryDirectory() as tmp:
        write_report(tmp, _sample_passing_raw())
        # Walk the tree — no .tmp orphan should remain
        for root, _, files in os.walk(tmp):
            for f in files:
                assert not f.endswith(".tmp"), (
                    f"atomic write left a .tmp file behind: {os.path.join(root, f)}"
                )


def test_normalize_report_handles_missing_summary_gracefully():
    """normalize_report tolerates malformed inputs (missing summary / items)."""
    from skills._lib.validate_report import normalize_report

    out = normalize_report({"items": [], "version": "1.0"}, openspec_cli_version="")
    assert out["passed"] is True
    assert out["failed_items"] == []
    assert out["summary"] == {}
