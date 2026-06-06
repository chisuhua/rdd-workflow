#!/usr/bin/env bats
# tests/integration/test_menu_case.bats
# P3-3 regression: every skill file that displays a menu with
# "i. 其他输入" must also instruct the LLM how to handle invalid
# input via a `case "$choice" in` block. Without the case block,
# the LLM has no explicit instruction for what to do when the user
# types something off the menu (typo, help request, refresh,
# quit), so the user can be stranded with no feedback.
#
# These tests lock the case handler in place across the 5 skill
# files that contain "i. 其他输入" prompts:
#   - skills/guide-spec.md
#   - skills/guide-ship.md
#   - skills/propose.md
#   - skills/status.md
#   - skills/execute.md
#
# The standard case block must support at least 2 of the 3 common
# aliases so the LLM has explicit guidance for the most common
# off-menu inputs (q/quit/exit, r/refresh, ?/help).

load ../test_helper

FILES=(
  "$REPO_ROOT/skills/guide-spec.md"
  "$REPO_ROOT/skills/guide-ship.md"
  "$REPO_ROOT/skills/propose.md"
  "$REPO_ROOT/skills/status.md"
  "$REPO_ROOT/skills/execute.md"
)

@test "All skill files have case handler for invalid input" {
  for f in "${FILES[@]}"; do
    [ -f "$f" ] || { echo "FAIL: $f does not exist"; return 1; }
    # case handler is the literal "case \"\$choice\" in" bash construct
    grep -qE 'case "\$choice" in' "$f" || {
      echo "FAIL: $f has no case handler for invalid input"
      return 1
    }
  done
}

@test "case handler covers standard aliases (q, r, ?)" {
  for f in "${FILES[@]}"; do
    # Each file's case block should support at least 2 of the 3
    # standard aliases so the LLM has explicit guidance for the
    # most common off-menu inputs.
    count=0
    grep -qE 'q\|quit\|exit' "$f" && count=$((count+1))
    grep -qE 'r\|refresh' "$f"     && count=$((count+1))
    grep -qE '\?\|help' "$f"       && count=$((count+1))
    [ "$count" -ge 2 ] || {
      echo "FAIL: $f has < 2 of 3 standard aliases (q|quit|exit, r|refresh, ?|help)"
      return 1
    }
  done
}

@test "case handler has wildcard (*) fallthrough for unknown input" {
  # Every case block must end with a *) fallthrough that produces
  # user-visible feedback. Without it, unknown inputs are silently
  # dropped (or worse, echoed back raw).
  for f in "${FILES[@]}"; do
    grep -qE '\*\) echo' "$f" || {
      echo "FAIL: $f case block has no '*' fallthrough"
      return 1
    }
  done
}

@test "case handler is closed with esac in every file" {
  # The case ... esac construct must be balanced — an unclosed
  # case block is a documentation syntax error.
  for f in "${FILES[@]}"; do
    case_count=$(grep -cE 'case "\$choice" in' "$f")
    esac_count=$(grep -cE '^esac$' "$f")
    [ "$case_count" -gt 0 ] || { echo "FAIL: $f has no case open"; return 1; }
    [ "$esac_count" -ge "$case_count" ] || {
      echo "FAIL: $f has $case_count 'case' opens but only $esac_count 'esac' closes"
      return 1
    }
  done
}
