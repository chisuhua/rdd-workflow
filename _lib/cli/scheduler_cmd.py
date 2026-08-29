"""``rddf scheduler`` — one-shot status of the 4 built-in schedulers."""
from __future__ import annotations

import sys
from typing import Optional


def _status() -> int:
    """Print one-line status per scheduler (best-effort, no threads started)."""
    import importlib.util

    def _available(module: str) -> bool:
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            return False

    schedulers = [
        ("cron", "skills._lib.schedulers.cron_scheduler"),
        ("fs-watcher", "skills._lib.schedulers.fs_watcher"),
        ("git-hook", "skills._lib.schedulers.git_hook"),
        ("webhook", "skills._lib.schedulers.webhook_receiver"),
    ]
    print("📊 Scheduler status (modules installed, importable)")
    print(f"{'SCHEDULER':<12} {'MODULE':<45} STATE")
    print("-" * 70)
    for name, mod in schedulers:
        ok = _available(mod)
        state = "✅ importable" if ok else "❌ missing"
        print(f"{name:<12} {mod:<45} {state}")
    return 0


def cmd_scheduler(args) -> int:
    """Handle ``rddf scheduler [status]``."""
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: rddf scheduler [status]")
        print()
        print("sub-commands:")
        print("  status    One-shot status of 4 built-in schedulers (default)")
        return 0
    sub = args[0]
    if sub == "status":
        return _status()
    print(f"❌ scheduler: unknown sub-command {sub!r}", file=sys.stderr)
    print("   usage: rddf scheduler [status]", file=sys.stderr)
    return 2