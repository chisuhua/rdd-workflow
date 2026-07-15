#!/usr/bin/env bats
# Mode D currently interpolates $PROJECT_ROOT directly into Python -c
# source via bash double-quotes. Per v2.0.2 convention (Mode E already
# fixed this), we must use os.environ instead.

load ../test_helper

@test "status.md Mode D uses os.environ not \$PROJECT_ROOT interpolation" {
  # Only match the ## Mode D section header, not any Mode D mention
  awk '
    /^## Mode D/  { in_md=1 }
    in_md && /```bash/ && !bash_seen { bash_seen=1; next }
    in_md && /```/ && bash_seen { exit }
    in_md { print }
  ' skills/status.md > /tmp/mode_d.bash

  # Ensure no 'with open...$PROJECT_ROOT...' interpolation
  if grep -qE 'with open.*\$PROJECT_ROOT' /tmp/mode_d.bash; then
    echo "FAIL: Mode D still uses \$PROJECT_ROOT in Python source"; return 1
  fi
  # Ensure at least one os.environ usage exists (matches v2.0.2 style)
  grep -q "os.environ" /tmp/mode_d.bash
}
