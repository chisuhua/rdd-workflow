#!/usr/bin/env bats
# S7: Mode C archive flow must require explicit confirmation before
# invoking archive_change(). Constrains "归档不可逆" (key constraint #4).
#
# v2.0.3 fix: First attempt used keyword 确认|confirm|read -r — too
# permissive; matched the unrelated "前置条件：确认全部完成" section.
# Now uses a regex that anchors on the actual `read -r` interactive
# prompt pattern, which only exists when there's a real y/n gate.

load ../test_helper

@test "status.md Mode C documents a confirmation prompt before archive_change" {
  # Match an interactive read pattern, not just any "confirm" keyword
  grep -qE "read -r|\\[ -n -r|\\[ -r" skills/status.md
}

@test "status.md Mode C does NOT call archive_change before user y/n" {
  # The confirmation block (read -r) MUST appear BEFORE the first
  # archive_change invocation.
  awk '
    /archive_change/ && !found_archive { found_archive=NR; exit }
    /read -r/ { found_confirm=NR }
    END {
      if (found_archive == 0) exit 1  # no archive_change at all
      if (found_confirm == 0) exit 1  # no read -r gate
      exit (found_confirm < found_archive ? 0 : 1)
    }
  ' skills/status.md
}
