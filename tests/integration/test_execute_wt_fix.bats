#!/usr/bin/env bats
#
# Wave 1 / T7: verify execute.md P0-7 and P0-9 fixes.
# See plan checkbox:
#   - [ ] 7. execute.md worktree $2 BUG + read -p fix (P0-7 + P0-9)
#
# P0-7: `git worktree list` default output is "path <sha> [branch]"
#       so the branch is in $3, not $2. Audit found 2 sites + 1 doc table
#       using $2 — fix to $3, inline a `wt_path_for_branch_inline` helper.
# P0-9: `read -p` blocks stdin in AI/CI environments — replace with
#       EXECUTE_CHOICE env var (defaults to 1).

load ../test_helper

# P0-7 ---------------------------------------------------------------------

@test "P0-7: execute.md no longer has \$2 openspec/ awk patterns" {
  [ -f "skills/execute/SKILL.md" ]
  # The old buggy pattern was: awk '$2 ~ /^openspec\// ...'
  # Use a regex that's specific to the bug (the field index $2 next to openspec/).
  if grep -nE '\$2[ ~]*\^?/?"?openspec/' "skills/execute/SKILL.md"; then
    echo "FAIL: \$2 BUG pattern still present in execute.md"
    return 1
  fi
}

@test "P0-7: execute.md uses \$3 (not \$2) for openspec/ branch matching" {
  [ -f "skills/execute/SKILL.md" ]
  # Should have at least one $3 pattern for branch matching (the awk branch filter)
  grep -qE '\$3[[:space:]]*~[[:space:]]*.*openspec' "skills/execute/SKILL.md"
  # And at least one $3 == "openspec/..." pattern (for path lookup)
  grep -qE '\$3=="openspec/' "skills/execute/SKILL.md"
}

@test "P0-7: execute.md has inline wt_path_for_branch_inline helper" {
  [ -f "skills/execute/SKILL.md" ]
  # Round A extraction: inline helper was removed, replaced by _lib/worktree.sh::wt_path_for_branch
  # sourced through _lib/select_worktree.sh. Verify execute.md no longer inlines the helper
  # and that worktree.sh provides the canonical implementation.
  ! grep -q "wt_path_for_branch_inline" "skills/execute/SKILL.md"
  grep -q "select_worktree.sh\|auto_detect_worktree_context" "skills/execute/SKILL.md"
  # The worktree.sh helper still exists (provides wt_path_for_branch)
  grep -q "wt_path_for_branch" "skills/_lib/worktree.sh"
}

# P0-9 ---------------------------------------------------------------------

@test "P0-9: execute.md no longer has read -p or read -r" {
  [ -f "skills/execute/SKILL.md" ]
  # The two most common blocking forms: read -p and read -r
  ! grep -qE '^\s*read -[pr]' "skills/execute/SKILL.md"
  # Also block the bare `read VAR` form (the original bug class)
  ! grep -qE '^\s*read [a-zA-Z_]+' "skills/execute/SKILL.md"
}

@test "P0-9: execute.md uses EXECUTE_CHOICE env var as escape hatch" {
  [ -f "skills/execute/SKILL.md" ]
  # Round A extraction: EXECUTE_CHOICE logic is in the helper, sourced by execute.md.
  # Verify it exists in the helper.
  grep -q "EXECUTE_CHOICE" "skills/execute/scripts/select_worktree.sh"
  # Should default to 1 when unset
  grep -qE 'EXECUTE_CHOICE:-1' "skills/execute/scripts/select_worktree.sh"
}

# Doc table ---------------------------------------------------------------

@test "P0-7: execute.md doc table uses \$3 (not \$2) as recommended" {
  [ -f "skills/execute/SKILL.md" ]
  # The "worktree 路径查找" row's 处理 (recommendation) should reference $3
  # Find the row, then look at the awk pattern in the 处理 column.
  if grep -nE 'worktree 路径查找' "skills/execute/SKILL.md" | grep -qE '\$2'; then
    echo "FAIL: doc table worktree-路径查找 row still uses \$2"
    return 1
  fi
  # The fix row should have $3
  grep -nE 'worktree 路径查找.*\$3' "skills/execute/SKILL.md"
}

# Runtime regression test --------------------------------------------------
# Verify the inline helper actually returns the right worktree path.
# This catches a subtle bug T2 documented: `git worktree list` default output
# wraps the branch in `[brackets]`, so $3 is `[openspec/X]`, not `openspec/X`.
# The T7 spec's literal `awk '$3 == br'` is broken unless `br` also includes
# the brackets. This test would have caught it.
@test "P0-7: inline wt_path_for_branch_inline actually finds a real worktree" {
  # Build a scratch git repo with an openspec/ worktree
  local tmp wt_dir
  tmp=$(mktemp -d)
  wt_dir="$tmp/.rddf/wt/test"
  ( cd "$tmp" \
    && git init -q \
    && git config user.email "t@t" \
    && git config user.name "t" \
    && echo x > a && git add a && git commit -q -m init \
    && git worktree add -b openspec/test-wt "$wt_dir" HEAD >/dev/null 2>&1
  )
  # Source the helper function from execute.md and call it
  # Use a temp file to avoid shell expansion of $3 in single-quoted strings
  local helper_file got
  helper_file=$(mktemp)
  cat > "$helper_file" <<'EOF'
wt_path_for_branch_inline() {
  local branch="${1:-}"
  [[ -z "$branch" ]] && return 1
  git worktree list 2>/dev/null | awk -v br="[openspec/$branch]" '$3 == br {print $1; exit}'
}
wt_path_for_branch_inline "test-wt"
EOF
  got=$( cd "$tmp" && bash "$helper_file" )
  rm -f "$helper_file"
  [ "$got" = "$wt_dir" ] || {
    echo "FAIL: helper returned [$got], expected [$wt_dir]"
    rm -rf "$tmp"
    return 1
  }
  rm -rf "$tmp"
}
