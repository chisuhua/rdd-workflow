#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "install_lib: skills/ has __init__.py (Python package marker)" {
  [ -f "skills/__init__.py" ]
}

@test "install_lib: skills/_lib/ has __init__.py (Python sub-package marker)" {
  [ -f "skills/_lib/__init__.py" ]
}

@test "install_lib: install.sh copies skills/_lib/*.py (recursive)" {
  run grep -E 'cp.*_lib.*\*\.py|cp.*skills/_lib' install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: install.sh excludes __pycache__ / plugins / schedulers" {
  run grep -E '__pycache__|plugins|schedulers' install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: INSTALL.md L100 mirrors install.sh (also copies _lib)" {
  run grep -nE '_lib.*\.py|skills/_lib' skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: INSTALL.md fallback lists all 13 skills (or dynamic)" {
  # Either hardcoded 13 skills, OR a dynamic python3 derivation.
  # Static check: count the escaped \"<name>\" entries in fallback strings.
  count=$(grep -oE '\\\\"[A-Za-z0-9_-]+\\\\"' skills/INSTALL.md | sort -u | wc -l)
  if [ "$count" -lt 13 ]; then
    # Try without escape
    count=$(grep -oE '"[A-Za-z0-9_-]+"' skills/INSTALL.md | sort -u | wc -l)
  fi
  [ "$count" -ge 13 ]
}

@test "install_lib: INSTALL.md L3 description uses count-based phrasing (no enumerated names)" {
  # Description should NOT contain a comma-separated list of skill names inside parentheses
  desc=$(sed -n '1,15p' skills/INSTALL.md | grep -E "description:")
  # If it lists skill names separated by /, that's the fragile form
  if echo "$desc" | grep -qE "全部 [0-9]+ 个子技能.*\(.*/.*\)"; then
    # Check that the parenthetical list has fewer entries than claimed
    count_in_paren=$(echo "$desc" | sed -E 's/.*\((.*)\).*/\1/' | tr '/' '\n' | wc -l)
    claimed=$(echo "$desc" | grep -oE '全部 [0-9]+' | grep -oE '[0-9]+')
    if [ -n "$claimed" ] && [ "$count_in_paren" -lt "$claimed" ]; then
      echo "INSTALL.md description claims $claimed but lists $count_in_paren names"
      return 1
    fi
  fi
}

@test "install_lib: _lib/schemas/*.json are listed in install" {
  run grep -E 'schemas.*\.json|_lib/schemas' install.sh skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}
