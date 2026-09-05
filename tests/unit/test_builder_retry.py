"""Tests for _lib/builder_retry (per spec §3.4, ADR-0034)."""

import sys
sys.path.insert(0, '/workspace/project/rdd-workflow')

from _lib.builder_retry import (
    route_verifier_verdict,
    should_halt_for_retry_exceeded,
    should_increment_retry,
)


def test_route_exit_0_success():
    result = route_verifier_verdict(0)
    assert result["next_phase"] == "phase-3-archive"
    assert result["should_back_route"] is False
    assert result["halted"] is False
    assert result["verifier_kind"] == "pass"


def test_route_exit_1_implementation_gap():
    result = route_verifier_verdict(1)
    assert result["next_phase"] == "phase-2"
    assert result["should_back_route"] is True
    assert result["halted"] is False
    assert result["verifier_kind"] == "implementation_gap"


def test_route_exit_2_ac_fail():
    result = route_verifier_verdict(2)
    assert result["next_phase"] == "phase-1"
    assert result["should_back_route"] is True
    assert result["halted"] is False
    assert result["verifier_kind"] == "ac_fail"


def test_route_exit_3_needs_human():
    result = route_verifier_verdict(3)
    assert result["next_phase"] == "halt"
    assert result["should_back_route"] is False
    assert result["halted"] is True
    assert result["verifier_kind"] == "needs_human"


def test_route_exit_4_halted_max_loops():
    result = route_verifier_verdict(4)
    assert result["next_phase"] == "halt"
    assert result["should_back_route"] is False
    assert result["halted"] is True
    assert result["verifier_kind"] == "halted_max_loops"


def test_route_exit_unknown():
    result = route_verifier_verdict(99)
    assert result["next_phase"] == "halt"
    assert result["should_back_route"] is False
    assert result["halted"] is True
    assert result["verifier_kind"] == "unknown_exit_99"


def test_route_custom_verifier_kind():
    result = route_verifier_verdict(1, verifier_kind="custom_kind")
    assert result["next_phase"] == "phase-2"
    assert result["verifier_kind"] == "custom_kind"


def test_halt_for_retry_under_max():
    assert should_halt_for_retry_exceeded(2, 3) is False


def test_halt_for_retry_at_max():
    assert should_halt_for_retry_exceeded(3, 3) is True


def test_halt_for_retry_over_max():
    assert should_halt_for_retry_exceeded(4, 3) is True


def test_halt_for_retry_zero_zero():
    assert should_halt_for_retry_exceeded(0, 0) is True


def test_increment_retry_true():
    assert should_increment_retry(True) is True


def test_increment_retry_false():
    assert should_increment_retry(False) is False


def test_route_exit_3_custom_kind():
    result = route_verifier_verdict(3, verifier_kind="my_human")
    assert result["halted"] is True
    assert result["verifier_kind"] == "my_human"


def test_route_exit_4_custom_kind():
    result = route_verifier_verdict(4, verifier_kind="my_halted")
    assert result["halted"] is True
    assert result["verifier_kind"] == "my_halted"
