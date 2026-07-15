#!/usr/bin/env bats
# status skill must declare a top-level input dispatcher that maps
# user input to Mode A/B/C/D/E. Currently the doc only lists the
# inputs as a table but provides no parser code — S8.

load ../test_helper

@test "status.md documents a top-level case-based mode dispatcher" {
  # Pattern: a 'case \"\$1\" in' or equivalent follows the input spec
  awk '
    /##[[:space:]]+输入/         { in_input=1; next }
    in_input && /case[[:space:]]+"/ { found=1; exit }
    in_input && /^##/           { exit }
    END { exit (found ? 0 : 1) }
  ' skills/status.md
}

@test "status.md router maps --roadmap to Mode D and --iteration to Mode E" {
  grep -qE -- "--roadmap.*Mode[[:space:]]+D|roadmap.*→.*Mode D" skills/status.md
  grep -qE -- "--iteration.*Mode[[:space:]]+E|iteration.*→.*Mode E" skills/status.md
}

@test "status.md router handles bare change name → Mode B" {
  grep -qE 'change.*name.*→.*Mode[[:space:]]+B|<change-name>.*Mode B|<name>.*Mode B' skills/status.md
}
