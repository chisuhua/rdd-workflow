"""Baseline vs current regression diff."""
from pathlib import Path
from _lib.cli.regression_diff_cmd import parse_known_failures, diff_failures


def test_parse_basic():
    text = "# comment\ntest_foo — env issue\ntest_bar — missing dep\n"
    assert parse_known_failures(text) == {"test_foo", "test_bar"}


def test_diff_no_new_failures(tmp_path):
    baseline = tmp_path / "known.txt"
    baseline.write_text("test_foo — env\n")
    current = {"test_foo"}
    new, removed = diff_failures(current, baseline)
    assert new == set()
    assert removed == set()


def test_diff_new_failure_detected(tmp_path):
    baseline = tmp_path / "known.txt"
    baseline.write_text("test_foo — env\n")
    current = {"test_foo", "test_new_regression"}
    new, removed = diff_failures(current, baseline)
    assert "test_new_regression" in new
    assert removed == set()


def test_diff_removed_failure_detected(tmp_path):
    baseline = tmp_path / "known.txt"
    baseline.write_text("test_foo — env\ntest_bar — missing\n")
    current = {"test_foo"}
    new, removed = diff_failures(current, baseline)
    assert new == set()
    assert "test_bar" in removed