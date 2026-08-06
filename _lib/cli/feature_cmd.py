"""``rddf feature`` subcommand handler.

Routes to ``skills.feature.scripts.feature_cli`` render functions.
"""
from __future__ import annotations

import os
import sys


def cmd_feature(args: list[str]) -> int:
    """Handle ``feature [summary|graph|status <name>|order]``."""
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    sys.path.insert(0, project_root)

    try:
        from skills.feature.scripts import feature_cli
    except ImportError as e:
        print(f"❌ feature_cli module unavailable: {e}", file=sys.stderr)
        return 2

    sub = args[0] if args else "summary"

    if sub == "summary":
        feature_cli.render_summary(project_root)
        return 0

    if sub == "graph":
        feature_cli.render_graph(project_root)
        return 0

    if sub == "status":
        if len(args) < 2:
            print("usage: rddf feature status <feature-name>", file=sys.stderr)
            return 2
        feature_cli.render_status(project_root, args[1])
        return 0

    if sub == "order":
        feature_cli.render_order(project_root)
        return 0

    print(f"usage: rddf feature [summary|graph|status <name>|order]", file=sys.stderr)
    return 2