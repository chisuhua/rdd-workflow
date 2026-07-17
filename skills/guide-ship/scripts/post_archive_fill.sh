#!/usr/bin/env bash
# skills/_lib/post_archive_fill.sh — extracted from guide-ship.md L562-L614
# Exports: run_post_archive_fill_suggestion()
#
# Post-archive hook: scans iteration.json for planned changes whose
# blocker just transitioned to archived/completed, and prints fill
# suggestions. Does NOT auto-call guide-plan fill.
#
# Uses iteration.get_unblocked_planned() (added in same change).
# Oracle C1: bash wrapper passes env vars only, no string interpolation
# in the PYEOF heredoc (quoted delimiter).

run_post_archive_fill_suggestion() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  # Scan for unblocked planned changes
  UNBLOCKED=$(
    PROJECT_ROOT="$PROJECT_ROOT" python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills._lib import iteration as it_mod

try:
    unblocked = it_mod.get_unblocked_planned(os.environ["PROJECT_ROOT"])
    for c in unblocked:
        print(c["name"])
except AttributeError:
    # Fallback: iteration.py predates get_unblocked_planned()
    data = it_mod.load(os.environ["PROJECT_ROOT"])
    for c in data.get("changes", []):
        if c.get("status") != "planned":
            continue
        blocker_name = c.get("blocker")
        if not blocker_name:
            print(c["name"])
            continue
        blocker = next(
            (b for b in data.get("changes", []) if b.get("name") == blocker_name),
            None,
        )
        if blocker and blocker.get("status") in ("completed", "archived"):
            print(c["name"])
except Exception as e:
    print(f"⚠️ get_unblocked_planned failed: {e}", file=sys.stderr)
PYEOF
)

  if [ -n "$UNBLOCKED" ]; then
    echo ""
    echo "💡 Fill suggestion (post-archive):"
    echo "   以下 planned change 的 blocker 已解除，可填充："
    for name in $UNBLOCKED; do
      echo "     - $name"
    done
    echo "   运行 'skill_use(\"guide-plan\")' → 选择 '3. 填充骨架 change (fill)' 来填充下一个"
  fi
}
