#!/usr/bin/env bats
# scan_state() is documented to export only RECOMMEND + REASON.
# Lock: 1) doc comment lists exactly the exported variables,
#       2) guide.md priority-count comment matches scan-state.sh count.

load ../test_helper

@test "scan-state.sh header lists EXPORTED_VARS set to {RECOMMEND REASON}" {
  grep -qE '^#[[:space:]]*EXPORTED_VARS:[[:space:]]*\{RECOMMEND[[:space:]]+REASON\}' skills/_lib/scan-state.sh
}

@test "scan-state.sh priority list (1..N) is internally consistent" {
  # Count actual priority bullets in the comment block.
  # Pattern matches both "1. " (dot-space, for `1.`, `2.`, ... `10.`)
  # AND "1.5 " (no dot after sub-number, for `1.5`, `2.5`) so the
  # count is the actual semantic priority count (12 = 1, 1.5, 2, 2.5, 3-10).
  n=$(awk '/^#[[:space:]]+[0-9]+(\.[0-9]+)?\.?[[:space:]]/ {print}' skills/_lib/scan-state.sh | wc -l)
  echo "priority count = $n"
  [ "$n" -eq 12 ]
}

@test "guide.md priority comment matches scan-state.sh count" {
  guide_n=$(grep -oE '优先级[[:space:]]*[0-9]+[[:space:]]*条' skills/guide.md | grep -oE '[0-9]+' | head -1)
  # Same relaxed pattern as test 2 — accepts both "1. " and "1.5 " forms
  shell_n=$(awk '/^#[[:space:]]+[0-9]+(\.[0-9]+)?\.?[[:space:]]/ {print}' skills/_lib/scan-state.sh | wc -l)
  [ "$guide_n" = "$shell_n" ] || {
    echo "FAIL: guide.md claims $guide_n, scan-state.sh has $shell_n"
    return 1
  }
}
