"""Verify multi-session.md + CHANGELOG.md are updated (AC-20)."""
from pathlib import Path


def test_multi_session_md_mentions_polling_loop():
    content = Path("docs/architecture/multi-session.md").read_text()
    assert "polling loop" in content.lower() or "轮询" in content
    assert "rddf_session_hook_poll_events" in content


def test_changelog_md_has_v41_polling_entry():
    content = Path("CHANGELOG.md").read_text()
    assert "add-guide-polling-loop-implementation" in content
    assert "polling" in content.lower() or "轮询" in content