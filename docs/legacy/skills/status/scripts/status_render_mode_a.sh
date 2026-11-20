#!/usr/bin/env bash
# _lib/status_render_mode_a.sh — extracted from status.md L134-L178
# Exports: render_status_mode_a()
#
# Mode A change status rendering. Queries iteration.json with filesystem-only
# fallback. Displays an emoji + status label for the given change name.
#
# Usage:
#   render_status_mode_a <change-name>
#   PROJECT_ROOT=/path/to/repo render_status_mode_a <change-name>
#
# Status mapping:
#   planned → 📋    committed → 💼    proposed → ✅
#   in_worktree → 🔧  completed → ✔    archived → 📦

render_status_mode_a() {
  local change="$1"
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  PY_PROJECT_ROOT="$PROJECT_ROOT" python3 - "$change" <<'PYEOF' 2>/dev/null
import json, sys, os
name = sys.argv[1]
project_root = os.environ.get("PY_PROJECT_ROOT", ".")
p = os.path.join(project_root, ".rddf/state/iteration.json")
try:
    data = json.load(open(p))
except Exception:
    # fallback: filesystem-only detection (commit in HEAD + no worktree)
    import subprocess
    has_committed = subprocess.run(
        ['bash','-c',
         'for d in openspec/changes/*/; do [ -d "$d" ] || continue; '
         'case "$d" in */archive/) continue ;; esac; '
         'git show HEAD:"$d.openspec.yaml" >/dev/null 2>&1 && exit 0; done; exit 1'
        ], capture_output=True, cwd=project_root).returncode == 0
    has_worktree = any(branch == f'openspec/{name}'
                       for line in subprocess.check_output(
                           ['git','worktree','list'], cwd=project_root
                       ).decode().splitlines()
                       for branch in [line.split()[-1].strip('[]')])
    if has_committed and not has_worktree:
        print('💼 committed (no worktree yet)')
    elif has_worktree:
        print('🔧 in_worktree (fallback)')
    else:
        print('📋 planned (skeleton fallback)')
    sys.exit(0)
ch = next((c for c in data.get('changes',[]) if c.get('name')==name), None)
if not ch:
    print('❓ unknown')
    sys.exit(0)
status = ch.get('status','unknown')
icons = {
    'planned':     '📋',
    'committed':   '💼',
    'proposed':    '✅',
    'in_worktree': '🔧',
    'completed':   '✔',
    'archived':    '📦',
}
print(f"{icons.get(status,'❓')} {status}")
PYEOF
}