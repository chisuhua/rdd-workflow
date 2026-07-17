#!/usr/bin/env bats
# G3: guide binding-output block must mention graceful skip when BINDING_LINES is empty.
# G5: guide must support --help and --no-binding input flags.

load ../test_helper

@test "guide.md binding block documents skip-when-empty behavior" {
  # The doc should mention that empty BINDING_LINES results in silent skip
  grep -qE 'BINDING_LINES|graceful.*skip|空.*跳过|empty.*skip|NO_BINDING' skills/guide/SKILL.md
}

@test "guide.md supports --help flag" {
  grep -qE -- '--help' skills/guide/SKILL.md
}

@test "guide.md supports --no-binding flag" {
  grep -qE -- '--no-binding' skills/guide/SKILL.md
}
