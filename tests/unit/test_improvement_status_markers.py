"""The terminal-marker vocabulary must cover the registry's completion tokens.

Background (fix-rddf-status-terminal-markers): the classifier knew
``已完成并归档 / 已实施并验收 / 已归档 / 已完成 / 已实施 / implemented /
completed / 已作废 / 作废 / superseded / archived`` — but **not** the tokens the
project registry actually writes (``已落地`` / ``已拆分`` / ``已取代``). Every
delivered item therefore stayed in the Pending pool (13 of 19 rows in the
2026-11-26 measurement).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _lib.dashboard.improvement_status import (  # noqa: E402
    TERMINAL_MARKERS,
    classify_improvement_status,
)


# --- AC1: the registry's completion tokens are terminal ----------------------


@pytest.mark.parametrize(
    "raw,expected_label",
    [
        ("✅ **已落地**（2026-11-19 实施）", "已落地"),
        ("已落地", "已落地"),
        ("已拆分", "已作废"),
        ("已取代", "已作废"),
    ],
)
def test_registry_completion_tokens_are_terminal(raw, expected_label):
    terminal, label = classify_improvement_status(raw)
    assert terminal is True
    assert label == expected_label


# --- AC2: zero regression on the existing vocabulary -------------------------


@pytest.mark.parametrize(
    "token",
    [
        "已完成并归档", "已实施并验收", "已归档", "已完成", "已实施",
        "implemented", "completed", "已作废", "作废", "superseded", "archived",
    ],
)
def test_existing_terminal_tokens_stay_terminal(token):
    terminal, _label = classify_improvement_status(token)
    assert terminal is True


@pytest.mark.parametrize(
    "token",
    ["未立项", "待立项", "已立项", "draft", "规划输入", "backlog",
     "待审查", "待回填", "已推迟", "待讨论"],
)
def test_open_tokens_stay_non_terminal(token):
    terminal, _label = classify_improvement_status(token)
    assert terminal is False


def test_every_terminal_marker_is_reachable_through_the_classifier():
    """The table is not decoration — each marker classifies as terminal."""
    for marker, _label in TERMINAL_MARKERS:
        terminal, _ = classify_improvement_status(marker)
        assert terminal is True, marker
