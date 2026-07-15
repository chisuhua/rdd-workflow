#!/usr/bin/env bats
# Mode B hygiene fixes (S4/S5/S6):
#   S4: PLAN_FILE / TASKS_FILE paths must both be $PROJECT_ROOT-anchored
#   S5: dead `source ... _lib/worktree.sh` at top-of-skill must be removed
#   S6: awk column comment on line 382 must mention $1 (path), $2 (hash), $3 (branch)

load ../test_helper

@test "status.md PLAN_FILE references \$PROJECT_ROOT" {
  grep -E 'PLAN_FILE=' skills/status.md | grep -vE 'PROJECT_ROOT' | grep -q . && {
    echo "FAIL: a PLAN_FILE assignment lacks \$PROJECT_ROOT"; return 1;
  } || true
  grep -E 'PLAN_FILE=.*PROJECT_ROOT' skills/status.md
}

@test "status.md TASKS_FILE references \$PROJECT_ROOT" {
  grep -E 'TASKS_FILE=' skills/status.md | grep -vE 'PROJECT_ROOT' | grep -q . && {
    echo "FAIL: a TASKS_FILE assignment lacks \$PROJECT_ROOT"; return 1;
  } || true
  grep -E 'TASKS_FILE=.*PROJECT_ROOT' skills/status.md
}

@test "status.md no longer sources _lib/worktree.sh (S5 dead source fix)" {
  ! grep -E 'source[[:space:]]+\$SCRIPT_DIR/_lib/worktree.sh' skills/status.md
}

@test "status.md awk column comment mentions \$1, \$2, \$3" {
  # v2.0.3 fix (R4 — Oracle review): the original awk regex used
  # `\$3[[:space:]]*~?~?\/` which mandated a literal `/` after `$3`
  # — that pattern cannot match the comment text at line 382 (or its
  # replacement) so the test would be permanently red.
  # Replaced with a portable bash check: find any line containing $3,
  # then confirm $1 and $2 are within ±3 lines of context.
  local found=0
  local n
  while IFS=: read -r n _; do
    [ -z "$n" ] && continue
    local start=$(( n > 3 ? n - 3 : 1 ))
    local end=$(( n + 3 ))
    local ctx
    ctx=$(sed -n "${start},${end}p" skills/status.md)
    if echo "$ctx" | grep -qE '\$1' && echo "$ctx" | grep -qE '\$2'; then
      found=1
      break
    fi
  done < <(grep -nE '^#.*\$3' skills/status.md)
  [ "$found" -eq 1 ]
}
