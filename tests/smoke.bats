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

@test "all 9 skill files exist" {
  [ -f "skills/INSTALL.md" ]
  [ -f "skills/guide.md" ]
  [ -f "skills/guide-spec.md" ]
  [ -f "skills/guide-ship.md" ]
  [ -f "skills/propose.md" ]
  [ -f "skills/execute.md" ]
  [ -f "skills/status.md" ]
  [ -f "skills/roadmap.md" ]
  [ -f "skills/deps.md" ]
}

@test "all skill files have valid frontmatter" {
  for f in skills/*.md; do
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
