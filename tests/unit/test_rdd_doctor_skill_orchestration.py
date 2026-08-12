"""Tests for rdd-doctor SKILL.md — verify AI orchestration protocol is documented.

The SKILL.md is the contract between the skill and AI assistants (OpenCode,
Claude Code, etc.). When `skill_use("rdd-doctor")` is called, the AI reads
this file and follows its instructions. These tests lock that the protocol
contains all required elements so the AI can:
1. Find and present findings
2. Ask user for consent before fixing
3. Map findings to fix actions (rddf migrate-improvements etc.)
4. Use --dry-run before state-changing actions
5. Re-run doctor to verify after fixes
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_SKILL_PATH = (
    Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    """Read SKILL.md once per test module."""
    return _SKILL_PATH.read_text()


def test_skill_exists_and_readable():
    """SKILL.md must exist at the canonical path."""
    assert _SKILL_PATH.is_file(), f"SKILL.md missing at {_SKILL_PATH}"


def test_skill_documents_all_six_categories(skill_text):
    """SKILL.md must enumerate all categories that the doctor checks."""
    for cat in ("state", "plan-tdd", "roadmap-meta", "proposal-table",
                "tasks-checkbox", "migration-residue"):
        assert cat in skill_text, f"category '{cat}' not documented in SKILL.md"


def test_skill_marks_doctor_as_readonly(skill_text):
    """Doctor's read-only contract must be documented."""
    text = skill_text.lower()
    assert "只读" in text or "read-only" in text or "readonly" in text


def test_skill_has_ai_orchestration_section(skill_text):
    """SKILL.md must contain an AI orchestration / AI assistant protocol section."""
    text = skill_text.lower()
    assert any(
        marker in text
        for marker in (
            "ai 编排",
            "ai orchestration",
            "ai 助手",
            "ai assistant",
            "ai 协议",
            "agent 协议",
        )
    ), "SKILL.md missing AI orchestration section"


def test_skill_requires_user_consent_before_fixing(skill_text):
    """AI must ask user before executing any fix."""
    text = skill_text.lower()
    # Look for explicit consent language
    assert any(
        marker in text
        for marker in (
            "用户同意",
            "用户授权",
            "user consent",
            "ask user",
            "don't auto-fix",
            "不直接执行修复",
            "用户没明确授权",
        )
    ), "SKILL.md missing user-consent requirement"


def test_skill_documents_dry_run_before_state_changes(skill_text):
    """All state-changing fix actions must use --dry-run first."""
    text = skill_text.lower()
    assert any(
        marker in text
        for marker in (
            "--dry-run",
            "dry-run",
            "dry run",
        )
    ), "SKILL.md missing --dry-run guidance"


def test_skill_maps_migration_residue_to_migrate_improvements(skill_text):
    """migration-residue findings must be mapped to rddf migrate-improvements."""
    text = skill_text
    # Either in description table or in orchestration section
    assert "migrate-improvements" in text
    assert "migration-residue" in text


def test_skill_requires_re_verification_after_fix(skill_text):
    """After applying fixes, AI must re-run doctor to verify."""
    text = skill_text.lower()
    assert any(
        marker in text
        for marker in (
            "再跑 doctor",
            "re-run doctor",
            "再跑一次",
            "验证",
            "verify",
        )
    ), "SKILL.md missing re-verification step"


def test_skill_documents_iteration_loop_until_clean(skill_text):
    """After fix + verify, AI must ITERATE if new findings appear (loop semantics).

    Without explicit loop, AI might stop after one fix round and miss
    follow-on issues (e.g., a fix that uncovers a new CRITICAL, or
    multiple categories with findings where only one is fixable).
    """
    text = skill_text.lower()
    assert any(
        marker in text
        for marker in (
            "循环",
            "iterate",
            "loop",
            "下一轮",
            "until",
            "重复 step",
        )
    ), "SKILL.md missing iteration-loop semantics"


def test_skill_allows_user_to_stop_iteration(skill_text):
    """User must be able to stop the iteration (e.g., 'stop, I'll handle manually')."""
    text = skill_text.lower()
    assert any(
        marker in text
        for marker in (
            "用户说停",
            "用户可以停",
            "用户随时",
            "stop iteration",
            "stop, i'll handle",
            "early stop",
            "可随时停",
        )
    ), "SKILL.md missing user-stop semantics"


def test_skill_reminds_doctor_stays_readonly_after_protocol_add(skill_text):
    """Adding the orchestration section must NOT weaken the read-only contract."""
    text = skill_text.lower()
    # Both invariants must be present
    assert "只读" in text or "read-only" in text
    assert any(
        marker in text
        for marker in (
            "ai 编排",
            "ai 助手",
            "ai 协议",
        )
    )