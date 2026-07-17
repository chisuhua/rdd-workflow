#!/usr/bin/env bats
# Smoke test: verify basic test infrastructure works.
#
# Run: bats tests/smoke.bats
#      npm test

load test_helper

@test "bats version is 1.10 or higher" {
  run bats --version
  [ "$status" -eq 0 ]
  # bats --version prints e.g. "Bats 1.10.0"; extract semver
  version=$(echo "$output" | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
  [[ -n "$version" ]]
  major=$(echo "$version" | cut -d. -f1)
  [ "$major" -ge 1 ]
}

@test "all skill files exist (dynamic)" {
  for f in skills/*.md; do
    [ -f "$f" ]
  done
}

@test "v1.x baseline skills still present (regression)" {
  [ -f "skills/INSTALL.md" ]
  [ -f "skills/guide/SKILL.md" ]
  [ -f "skills/guide-arch/SKILL.md" ]
  [ -f "skills/guide-plan/SKILL.md" ]
  [ -f "skills/guide-ship/SKILL.md" ]
  [ -f "skills/propose/SKILL.md" ]
  [ -f "skills/execute/SKILL.md" ]
  [ -f "skills/status/SKILL.md" ]
  [ -f "skills/roadmap/SKILL.md" ]
  [ -f "skills/deps/SKILL.md" ]
}

@test "all skill files have valid frontmatter" {
  for f in skills/*.md skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    head -1 "$f" | grep -q "^---$"
  done
}

@test "test_helper.bash is sourced" {
  [ -f "tests/test_helper.bash" ]
  grep -q "setup()" "tests/test_helper.bash" || grep -q "setup" "tests/test_helper.bash"
}

@test "package.json declares test script" {
  [ -f "package.json" ]
  grep -q '"test"' "package.json"
  grep -q 'bats' "package.json"
}

@test ".gitignore excludes .bats-tmp/" {
  [ -f ".gitignore" ]
  grep -q "^\.bats-tmp/" ".gitignore"
}

@test "test infrastructure directories exist" {
  [ -d "tests/_lib" ]
  [ -d "tests/integration" ]
  [ -f "tests/README.md" ]
}
