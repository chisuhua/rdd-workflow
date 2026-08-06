#!/usr/bin/env bash
# skills/_lib/sessions_count.sh — read-only orphaned rddf-session counter.

count_orphaned_sessions() {
  local root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local file="$root/.rddf/state/sessions.json"
  [ -f "$file" ] || { echo 0; return 0; }
  if command -v jq >/dev/null 2>&1; then
    jq '[.sessions[]? | select(.state == "orphaned")] | length' "$file" 2>/dev/null || echo 0
  else
    python3 -c 'import json,sys; f=sys.argv[1]; print(len([s for s in json.load(open(f)).get("sessions",[]) if s.get("state")=="orphaned"]))' "$file" 2>/dev/null || echo 0
  fi
}
