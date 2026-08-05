"""Tests for session_stats module.

Per improvements/developer-experience-observability.md:
- Track tool calls (bash, read, edit, write, task)
- Track failures (quota exhausted, timeouts)
- Track phase durations (plan, execute, archive)
- Output to .rddf/state/session_stats.json
"""
import pytest
from datetime import datetime, timezone, timedelta

from skills._lib.session_stats import (
    record_tool_call,
    record_failure,
    record_phase_duration,
    save_session_stats,
    load_session_stats,
    reset_session_stats,
)


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Redirect RDDF_STATE_DIR to tmp path for isolated tests."""
    monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
    yield tmp_path


class TestSessionStats:
    def test_record_tool_call_increments_count(self, state_dir):
        """Recording tool calls increments count by tool name."""
        record_tool_call("bash")
        record_tool_call("bash")
        record_tool_call("read")
        stats = load_session_stats()
        assert stats["tool_calls"]["bash"] == 2
        assert stats["tool_calls"]["read"] == 1

    def test_record_failure_with_type_and_tool(self, state_dir):
        """Recording failure stores type, tool, count, timestamp."""
        record_failure("quota_exceeded", tool="task", count=1)
        stats = load_session_stats()
        assert len(stats["failures"]) == 1
        assert stats["failures"][0]["type"] == "quota_exceeded"
        assert stats["failures"][0]["tool"] == "task"
        assert stats["failures"][0]["count"] == 1

    def test_record_failure_aggregates_same_type(self, state_dir):
        """Multiple failures of same type increment count."""
        record_failure("quota_exceeded", tool="task", count=1)
        record_failure("quota_exceeded", tool="task", count=1)
        record_failure("timeout", tool="bash", count=2)
        stats = load_session_stats()
        # 2 aggregated quota_exceeded + 1 timeout
        types = [f["type"] for f in stats["failures"]]
        assert sorted(types) == ["quota_exceeded", "timeout"]
        quota = next(f for f in stats["failures"] if f["type"] == "quota_exceeded")
        assert quota["count"] == 2

    def test_record_phase_duration(self, state_dir):
        """Recording phase duration stores phase name and seconds."""
        record_phase_duration("plan", 1200)
        record_phase_duration("execute", 1800)
        stats = load_session_stats()
        assert stats["phase_durations"]["plan"] == 1200
        assert stats["phase_durations"]["execute"] == 1800

    def test_load_empty_when_no_file(self, state_dir):
        """Loading from empty state returns empty stats."""
        stats = load_session_stats()
        assert stats["tool_calls"] == {}
        assert stats["failures"] == []
        assert stats["phase_durations"] == {}

    def test_save_creates_session_id_when_not_provided(self, state_dir):
        """Save generates session_id if not provided."""
        record_tool_call("bash")
        stats = load_session_stats()
        assert "session_id" in stats
        assert isinstance(stats["session_id"], str)

    def test_save_with_explicit_session_id(self, state_dir):
        """Save uses provided session_id."""
        save_session_stats({"session_id": "ses_test_123", "tool_calls": {"bash": 5}})
        stats = load_session_stats()
        assert stats["session_id"] == "ses_test_123"
        assert stats["tool_calls"]["bash"] == 5

    def test_reset_clears_all_stats(self, state_dir):
        """Reset clears all stats."""
        record_tool_call("bash")
        record_failure("quota_exceeded", tool="task")
        record_phase_duration("plan", 100)
        reset_session_stats()
        stats = load_session_stats()
        assert stats["tool_calls"] == {}
        assert stats["failures"] == []
        assert stats["phase_durations"] == {}

    def test_atomic_write_via_tmp_rename(self, state_dir):
        """Save uses atomic write (tmp + rename)."""
        from pathlib import Path
        record_tool_call("bash")
        # Verify no .tmp file lingering
        tmp_files = list(state_dir.glob("session_stats.json.tmp"))
        assert tmp_files == []
        # Verify main file exists
        main_file = state_dir / "session_stats.json"
        assert main_file.exists()


class TestHookWhitelist:
    """Tests for hook comment whitelist (separate file)."""

    def test_bash_source_pattern_matches(self):
        from skills._lib.hook_whitelist import is_whitelisted_comment
        assert is_whitelisted_comment("# BASH_SOURCE[0] guard")
        assert is_whitelisted_comment("#   BASH_SOURCE[0]")

    def test_set_e_pattern_matches(self):
        from skills._lib.hook_whitelist import is_whitelisted_comment
        # Bash idioms are typically in comments (because they're not bash syntax in code review)
        assert is_whitelisted_comment("# set -e")
        assert is_whitelisted_comment("# set -u")
        assert is_whitelisted_comment("# set -o pipefail")
        assert is_whitelisted_comment("#   set -uo")

    def test_magic_number_pattern_matches(self):
        from skills._lib.hook_whitelist import is_whitelisted_comment
        assert is_whitelisted_comment("# 100ms threshold tuned for hardware X")
        assert is_whitelisted_comment("# Threshold: 200ms")

    def test_ticket_ref_pattern_matches(self):
        from skills._lib.hook_whitelist import is_whitelisted_comment
        assert is_whitelisted_comment("# TODO(bug-123)")
        assert is_whitelisted_comment("# TODO(rddf-456)")

    def test_normal_comment_not_whitelisted(self):
        from skills._lib.hook_whitelist import is_whitelisted_comment
        assert not is_whitelisted_comment("# This is a normal comment")
        assert not is_whitelisted_comment("# FIXME: fix this")

    def test_non_comment_not_whitelisted(self):
        from skills._lib.hook_whitelist import is_whitelisted_comment
        assert not is_whitelisted_comment("BASH_SOURCE[0] = $0")
        assert not is_whitelisted_comment("import os")
