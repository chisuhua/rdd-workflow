#!/usr/bin/env bash
# skills/_lib/wave_scheduler_hooks.sh - bash wrappers for WaveScheduler
# Exports:
#   - wave_scheduler_post_archive <project_root> <archived_name>
#   - wave_scheduler_entry_check <project_root> <skill_name>
#
# Oracle C1 safe: passes all parameters via env vars (no bash string
# interpolation into Python heredoc). The quoted 'PYEOF' delimiter
# prevents shell expansion inside the heredoc.

wave_scheduler_post_archive() {
  # Args: <project_root> <archived_name>
  local PROJECT_ROOT="${1:-${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
  local ARCHIVED_NAME="${2:-}"
  export PROJECT_ROOT
  export ARCHIVED_NAME

  if [ -z "$ARCHIVED_NAME" ]; then
      return 0
  fi

  export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

  local OUTPUT
  OUTPUT=$(WS_PROJECT_ROOT="$PROJECT_ROOT" WS_ARCHIVED_NAME="$ARCHIVED_NAME" python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["WS_PROJECT_ROOT"])
try:
    from skills._lib.wave_scheduler import WaveScheduler
    sched = WaveScheduler()
    recs = sched.check_on_archive(os.environ["WS_PROJECT_ROOT"], os.environ["WS_ARCHIVED_NAME"])
    if not recs:
        sys.exit(0)
    print("💡 Wave suggestion (post-archive):")
    for r in recs:
        print(f"  - {r.name}: {r.reason} (wave={r.wave}, source={r.source})")
    print("")
    print("   运行 'skill_use(\"guide-plan\")' 填充 (wave=fill) 或 'skill_use(\"guide-ship\")' 执行 (wave=ship)")
except Exception as e:
    print(f"⚠️ wave_scheduler_post_archive failed: {e}", file=sys.stderr)
    sys.exit(0)  # Never block archive on hook failure
PYEOF
)
  if [ -n "$OUTPUT" ]; then
      echo ""
      echo "$OUTPUT"
  fi
}

wave_scheduler_entry_check() {
  # Args: <project_root> <skill_name>
  local PROJECT_ROOT="${1:-${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
  local SKILL_NAME="${2:-}"
  export PROJECT_ROOT
  export SKILL_NAME
  export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

  local OUTPUT
  OUTPUT=$(WS_PROJECT_ROOT="$PROJECT_ROOT" WS_SKILL_NAME="$SKILL_NAME" python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["WS_PROJECT_ROOT"])
try:
    from skills._lib.wave_scheduler import WaveScheduler
    sched = WaveScheduler()
    recs = sched.check_on_entry(os.environ["WS_PROJECT_ROOT"], os.environ["WS_SKILL_NAME"])
    if not recs:
        sys.exit(0)
    print("💡 Wave suggestion (entry):")
    for r in recs:
        print(f"  - {r.name}: {r.reason} (wave={r.wave}, source={r.source})")
    print("")
    print("   可推进的 changes 如上 (wave=fill -> guide-plan, wave=ship -> guide-ship)")
except Exception as e:
    print(f"⚠️ wave_scheduler_entry_check failed: {e}", file=sys.stderr)
    sys.exit(0)
PYEOF
)
  if [ -n "$OUTPUT" ]; then
      echo ""
      echo "$OUTPUT"
  fi
}
