"""Verify guide_entry.sh invokes rddf_session_hook_poll_events (AC-2)."""
from pathlib import Path


def test_guide_entry_calls_polling():
    guide_entry = Path("skills/guide/scripts/guide_entry.sh").read_text()
    assert "rddf_session_hook_poll_events" in guide_entry, \
        "guide_entry.sh must call rddf_session_hook_poll_events (AC-2)"