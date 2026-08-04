from pathlib import Path

from tests.unit.python_regression import compare_failures, parse_failed_tests


def test_parse_failed_tests_extracts_pytest_failure_lines():
    output = """
FAILED tests/unit/test_a.py::test_one - assert 1 == 2
FAILED tests/unit/test_b.py::test_two - assert 3 == 4
==== 2 failed in 0.01s ====
"""
    assert parse_failed_tests(output) == [
        "tests/unit/test_a.py::test_one",
        "tests/unit/test_b.py::test_two",
    ]


def test_compare_failures_detects_known_new_and_stale():
    baseline_path = Path("/tmp/dummy-python-baseline.txt")
    baseline_path.write_text(
        "tests/unit/test_a.py::test_one # historical\n"
        "tests/unit/test_c.py::test_three # fixed\n"
    )
    actual = [
        "tests/unit/test_a.py::test_one",
        "tests/unit/test_b.py::test_two",
    ]
    result = compare_failures(actual, baseline_path)
    assert result["known_count"] == 1
    assert result["new_count"] == 1
    assert result["stale_count"] == 1
    assert result["known"] == ["tests/unit/test_a.py::test_one"]
    assert result["new"] == ["tests/unit/test_b.py::test_two"]
    assert result["stale"] == ["tests/unit/test_c.py::test_three"]
    baseline_path.unlink()
