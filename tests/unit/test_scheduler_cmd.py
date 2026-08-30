"""Verify `rddf scheduler status` subcommand parsing + output."""
from pathlib import Path
from unittest.mock import patch


class TestSchedulerCmd:
    def test_subcommand_dispatches(self):
        import sys
        sys.path.insert(0, str(Path.cwd()))
        from _lib.cli.scheduler_cmd import cmd_scheduler

        with patch("_lib.cli.scheduler_cmd._status", return_value=0) as mock:
            rc = cmd_scheduler(["status"])
            assert rc == 0
            mock.assert_called_once_with()

    def test_status_no_args_shows_help(self, capsys):
        """Empty args prints usage + exits 0 (matches cmd_sessions convention)."""
        import sys
        sys.path.insert(0, str(Path.cwd()))
        from _lib.cli.scheduler_cmd import cmd_scheduler
        rc = cmd_scheduler([])
        out = capsys.readouterr().out
        assert "usage: rddf scheduler" in out
        assert rc == 0

    def test_status_prints_4_schedulers(self, capsys):
        import sys
        sys.path.insert(0, str(Path.cwd()))
        from _lib.cli.scheduler_cmd import _status
        rc = _status()
        out = capsys.readouterr().out
        for name in ("cron", "fs-watcher", "git-hook", "webhook"):
            assert name in out
        assert rc == 0
