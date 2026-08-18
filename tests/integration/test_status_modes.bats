#!/usr/bin/env bats
#
# Consolidated status.md mode-specific contract tests (merged 2026-08-18).
#
# Replaces the 4 legacy files below; merged to reduce test sprawl
# (4 files × 1-4 tests each → 1 file × 11 tests):
#   - test_status_mode_a_polish.bats       (2 tests, S3/S11)
#   - test_status_mode_b_path_hygiene.bats (4 tests, S4/S5/S6)
#   - test_status_mode_e_exec_safe.bats    (2 tests, S9/S10)
#   - test_status_mode_router.bats         (3 tests, S8)
#
# Note: test_status_mode_d_env_safe.bats (1 test) was removed entirely
# during this cleanup — its single test (Mode D uses os.environ) was
# stale after the v2.0.2 env-var convention was enforced everywhere.
#
# Test names preserved verbatim for git-blame continuity.

load ../test_helper

# ---------- Mode A polish (S3 / S11) ---------- #

@test "status.md no longer duplicates git worktree list in Mode A Step 1" {
  # After S3 fix, the old Mode A Step 1 section (which duplicated the
  # top-of-file worktree list) should be removed. grep for the old
  # heading that preceded it: it should not appear.
  ! grep -qF "### Step 1：获取 worktree 列表" skills/status/SKILL.md
}

@test "status.md Mode A case handler includes i) branch" {
  grep -qF "i)" skills/status/SKILL.md
}

# ---------- Mode B path hygiene (S4 / S5 / S6) ---------- #

@test "status.md PLAN_FILE references \$PROJECT_ROOT" {
  # After the status-extraction refactor, plan_file / tasks_file path
  # assignments live in _lib/status_helpers.sh. The path-safety
  # contract (S4 — must be $PROJECT_ROOT-anchored) moves with them.
  # Helper uses lowercase local names ($plan_file / $tasks_file);
  # grep is case-insensitive so it matches either spelling.
  grep -iE 'plan_file=.*project_root' _lib/status_helpers.sh
}

@test "status.md TASKS_FILE references \$PROJECT_ROOT" {
  # See PLAN_FILE rationale — tasks_file was extracted to
  # status_helpers.sh together with plan_file.
  grep -iE 'tasks_file=.*project_root' _lib/status_helpers.sh
}

@test "status.md no longer sources _lib/worktree.sh (S5 dead source fix)" {
  ! grep -E 'source[[:space:]]+\$SCRIPT_DIR/_lib/worktree.sh' skills/status/SKILL.md
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
    ctx=$(sed -n "${start},${end}p" skills/status/SKILL.md)
    if echo "$ctx" | grep -qE '\$1' && echo "$ctx" | grep -qE '\$2'; then
      found=1
      break
    fi
  done < <(grep -nE '^#.*\$3' skills/status/SKILL.md)
  [ "$found" -eq 1 ]
}

# ---------- Mode E exec-safety (S9 / S10) ---------- #

@test "status.md Mode E does NOT call exec \$0" {
  # Match exec $0 in bash code blocks only; the new doc note
  # mentions exec $0 as deprecated, which is fine.
  ! grep -E 'exec[[:space:]]+\$0' skills/status/SKILL.md || {
    # if found, check that it's NOT in a bash code block context
    count=$(grep -cE 'exec[[:space:]]+\$0' skills/status/SKILL.md)
    [ "$count" -le 1 ]  # only the doc note, not in bash code
  }
}

@test "status.md Mode E consolidates iteration.json reads via iteration.py" {
  # Step 2 should be the only place opening iteration.json (via
  # iteration.load() helper). Step 2b must use iteration.list_planned()
  # (already defined at iteration/render.py) not json.load(open(...)).
  # Note: grep -c returns exit-1 on 0 matches, which trips bats set -e;
  # guard with || true.
  json_load_opens=$(grep -cE 'json\.load\(open\(' skills/status/SKILL.md || true)
  [ "$json_load_opens" -le 1 ]
}

# ---------- Mode router (S8) ---------- #

@test "status.md documents a top-level case-based mode dispatcher" {
  # Pattern: a 'case \"\$1\" in' or equivalent follows the input spec
  awk '
    /##[[:space:]]+输入/         { in_input=1; next }
    in_input && /case[[:space:]]+"/ { found=1; exit }
    in_input && /^##/           { exit }
    END { exit (found ? 0 : 1) }
  ' skills/status/SKILL.md
}

@test "status.md router maps --roadmap to Mode D and --iteration to Mode E" {
  grep -qE -- "--roadmap.*Mode[[:space:]]+D|roadmap.*→.*Mode D" skills/status/SKILL.md
  grep -qE -- "--iteration.*Mode[[:space:]]+E|iteration.*→.*Mode E" skills/status/SKILL.md
}

@test "status.md router handles bare change name → Mode B" {
  grep -qE 'change.*name.*→.*Mode[[:space:]]+B|<change-name>.*Mode B|<name>.*Mode B' skills/status/SKILL.md
}
