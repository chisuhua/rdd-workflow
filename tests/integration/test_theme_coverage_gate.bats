#!/usr/bin/env bats
# tests/integration/test_theme_coverage_gate.bats
load test_helper

setup() {
    export TMPD
    TMPD="$(mktemp -d "${BATS_TMPDIR:-/tmp}/coverage-gate.XXXXXX")"
    mkdir -p "$TMPD/docs/adr" "$TMPD/.rddf/improvements"
    cat > "$TMPD/roadmap.md" <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | TestTheme | active | | |
EOF
}

teardown() {
    rm -rf "$TMPD"
}

skip_if_no_helpers() {
    [ -f "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" ] \
        || skip "helper file not extracted yet"
}

@test "gate: default (no STRICT) uncovered → exits 0 (warning only)" {
    skip_if_no_helpers
    run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -eq 0 ]
}

@test "gate: covered + STRICT=yes → exits 0" {
    skip_if_no_helpers
    cat > "$TMPD/.rddf/improvements/foo.md" <<'EOF'
---
**主题**: TestTheme
---
EOF
    STRICT_PROPOSAL_COVERAGE=yes run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -eq 0 ]
}

@test "gate: uncovered + STRICT=yes → exits 1" {
    skip_if_no_helpers
    STRICT_PROPOSAL_COVERAGE=yes run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -ne 0 ]
}

@test "gate: empty roadmap → exit 0 (skip)" {
    skip_if_no_helpers
    echo > "$TMPD/roadmap.md"
    STRICT_PROPOSAL_COVERAGE=yes run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -eq 0 ]
}

@test "gate: missing roadmap.md → exit 2 (error)" {
    skip_if_no_helpers
    rm -f "$TMPD/roadmap.md" "$TMPD/docs/roadmap.md"
    run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -eq 2 ]
}

@test "gate: SKIP_PROPOSAL_COVERAGE=yes wins over STRICT → exit 0" {
    skip_if_no_helpers
    SKIP_PROPOSAL_COVERAGE=yes STRICT_PROPOSAL_COVERAGE=yes \
        run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -eq 0 ]
}

@test "gate: uncovered theme appears in stdout when STRICT=yes" {
    skip_if_no_helpers
    STRICT_PROPOSAL_COVERAGE=yes run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [[ "$output" =~ "TestTheme" ]]
}

@test "gate: invalid project root → exit 2 (explicit error)" {
    skip_if_no_helpers
    run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "/nonexistent/path/zzz"
    [ "$status" -eq 2 ]
}

@test "gate: ~skipped~ themes excluded from denominator" {
    skip_if_no_helpers
    cat > "$TMPD/roadmap.md" <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | LiveTheme | active | | |
| phase-1 | SkipTheme ~skipped~ | active | | |
EOF
    STRICT_PROPOSAL_COVERAGE=yes run bash "$REPO_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh" "$TMPD"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "LiveTheme" ]]
    ! [[ "$output" =~ "SkipTheme" ]]
}