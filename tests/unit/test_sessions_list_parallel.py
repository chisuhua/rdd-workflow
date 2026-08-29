"""Verify `rddf sessions list-parallel` subcommand parsing + grouping."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestSessionsListParallel:
    """Unit tests for the list-parallel subcommand (no real sessions file)."""

    def test_subcommand_dispatches_to_list_parallel(self):
        """cmd_sessions(['list-parallel']) must dispatch to the parallel lister,
        not fall through to 'unknown sub-command'."""
        sys.path.insert(0, str(Path.cwd()))
        from _lib.cli.sessions_cmd import cmd_sessions

        with patch("_lib.cli.sessions_cmd._list_parallel_sessions", return_value=0) as mock:
            rc = cmd_sessions(["list-parallel"])
            assert rc == 0
            mock.assert_called_once_with()

    def test_list_parallel_no_sessions(self, capsys):
        """Empty sessions file → friendly message, exit 0."""
        sys.path.insert(0, str(Path.cwd()))
        from _lib.cli.sessions_cmd import _list_parallel_sessions

        with patch("_lib.cli.sessions_cmd._get_coordinator") as mock_coord:
            class _FakeCoord:
                def list_sessions(self):
                    return []
            mock_coord.return_value = _FakeCoord()
            rc = _list_parallel_sessions()
            out = capsys.readouterr().out
            assert "no sessions" in out.lower()
            assert rc == 0

    def test_list_parallel_groups_by_workflow_group(self, capsys):
        """Sessions with same workflow_group must be grouped together."""
        sys.path.insert(0, str(Path.cwd()))
        from _lib.cli.sessions_cmd import _list_parallel_sessions

        class _FakeSession:
            def __init__(self, sid, kind, state, owner, changes, group):
                self.session_id = sid
                self.kind = kind
                self.state = state
                self.owner_opencode_session_id = owner
                self.attached_changes = changes
                self.workflow_group = group

        fake = [
            _FakeSession("rds_aaaabbbbcccc", "stage_plan", "active", "owner1", ["c1"], "group-A"),
            _FakeSession("rds_ddddeeeeffff", "stage_ship", "active", "owner2", ["c2"], "group-B"),
        ]
        with patch("_lib.cli.sessions_cmd._get_coordinator") as mock_coord:
            class _FakeCoord:
                def list_sessions(self):
                    return fake
            mock_coord.return_value = _FakeCoord()
            rc = _list_parallel_sessions()
            out = capsys.readouterr().out
            assert "group-A" in out
            assert "group-B" in out
            assert rc == 0