#!/usr/bin/env bats

load ../test_helper

@test "guide-spec.md no longer uses single hardcoded fallback" {
  [ -f "skills/guide-spec.md" ]
  # The OLD pattern: `command -v openspec 2>/dev/null || echo "/path"`
  # The NEW pattern: a for-loop with multiple paths
  # Verify: no single `|| echo "/path"` fallback
  if grep -nE 'command -v openspec[^|]*\|\| echo "/[^"]*"' skills/guide-spec.md; then
    echo "FAIL: single-path fallback still present"
    return 1
  fi
}

@test "guide-spec.md has multi-path fallback list" {
  [ -f "skills/guide-spec.md" ]
  # Should reference multiple known install locations
  grep -q "for p in" skills/guide-spec.md
  grep -q "/usr/local/bin/openspec" skills/guide-spec.md
  grep -q "/opt/homebrew/bin/openspec" skills/guide-spec.md
}

@test "guide-spec.md has install error message" {
  [ -f "skills/guide-spec.md" ]
  grep -q "请安装: npm install -g openspec-cli" skills/guide-spec.md
}

@test "OPENSPEC_PATH used after fallback chain (both lines 80 and 159)" {
  [ -f "skills/guide-spec.md" ]
  # Count occurrences of the for-loop pattern
  COUNT=$(grep -c "for p in" skills/guide-spec.md)
  [ "$COUNT" -ge 2 ]
}
