#!/usr/bin/env bats
# test_rdd_verifier_archive_compat.bats — Verify SHA-fingerprint verdict cache
# integration with archive_gate_check (per ADR-0034 §7.2, amended by ADR-0045)
#
# v2.0 semantics (ADR-0045): the ac-verifier subprocess fallback is removed.
#   1. Cache hit (codebase_commit matches HEAD) → cache reused, no LLM call
#   2. Cache stale (new commit after cache) → fail closed
#   3. Cache missing → fail closed (run rdd-verify first, or audited bypass)
#   4. SKIP_AC_VERIFICATION=yes → bypass entire AC step (existing behavior)
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    unset PROJECT_ROOT
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    mkdir -p openspec/changes/test-change .rddf/state
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Tasks
- [x] task 1 done
- [x] task 2 done
EOF
    cat > openspec/changes/test-change/proposal.md <<'EOF'
# Test Change
## 验收标准
- AC-1: A test criterion
EOF
    git add . && git commit -q -m "init"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Symlink skills/ so verifier helpers are discoverable
_setup_skills_symlink() {
    ln -s "$REPO_ROOT/skills" "$TEST_TMP/skills"
}

@test "archive_gate_check: cache hit (matching SHA) reuses verdict without LLM call" {
    _setup_skills_symlink
    SHA=$(git rev-parse HEAD)

    # Seed verdict cache at current commit with valid pass verdict
    cat > .rddf/state/.ac-verdict-test-change.json <<EOF
{"version":1,"change":"test-change","codebase_commit":"$SHA","verdict":[
  {"ac_id":"AC-1","status":"pass","confidence":0.95,"evidence":[],"reasoning":"All good"}
],"ran_at":"2026-08-26T00:00:00Z","ran_by":"rdd-verifier"}
EOF

    # Source archive.sh, set up cache hit scenario
    source "$REPO_ROOT/_lib/archive.sh"

    # STRICT_AC_GATE=yes would normally fail on mock-pass; with cache hit,
    # the cached pass verdict should override and exit 0
    STRICT_AC_GATE=yes \
        run archive_gate_check test-change "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Reusing verifier verdict cache"* ]]
}

@test "archive_gate_check: stale cache (different SHA) fails closed (no fallback)" {
    _setup_skills_symlink
    OLD_SHA=$(git rev-parse HEAD)

    # Seed cache with OLD SHA
    cat > .rddf/state/.ac-verdict-test-change.json <<EOF
{"version":1,"change":"test-change","codebase_commit":"$OLD_SHA","verdict":[],"ran_at":"x","ran_by":"rdd-verifier"}
EOF

    # Create new commit to invalidate cache
    echo "new" > new.txt
    git add new.txt && git commit -q -m "new"

    source "$REPO_ROOT/_lib/archive.sh"

    # Cache is stale → no ac-verifier fallback → fail closed (ADR-0045)
    STRICT_AC_GATE=no \
        run archive_gate_check test-change "$TEST_TMP"

    [ "$status" -eq 1 ]
    [[ "$output" == *"stale"* ]]
    [[ "$output" == *"no valid verdict cache"* ]]
}

@test "archive_gate_check: missing cache fails closed (run rdd-verify first)" {
    _setup_skills_symlink
    # No cache file → fail closed per ADR-0045 (no ac-verifier fallback)
    source "$REPO_ROOT/_lib/archive.sh"

    STRICT_AC_GATE=no \
        run archive_gate_check test-change "$TEST_TMP"

    [ "$status" -eq 1 ]
    [[ "$output" == *"no valid verdict cache"* ]]
    [[ "$output" == *"rddf rdd-verify"* ]]
    [[ ! "$output" == *"Reusing verifier verdict cache"* ]]
}

@test "archive_gate_check: SKIP_AC_VERIFICATION=yes bypasses AC step" {
    _setup_skills_symlink
    SHA=$(git rev-parse HEAD)
    # Even with cache present, SKIP_AC_VERIFICATION bypasses
    cat > .rddf/state/.ac-verdict-test-change.json <<EOF
{"version":1,"change":"test-change","codebase_commit":"$SHA","verdict":[],"ran_at":"x","ran_by":"rdd-verifier"}
EOF

    source "$REPO_ROOT/_lib/archive.sh"
    SKIP_AC_VERIFICATION=yes STRICT_AC_GATE=yes \
        run archive_gate_check test-change "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ ! "$output" == *"Reusing ac-verifier verdict cache"* ]]
    [[ ! "$output" == *"AC verification"* ]]
}

@test "archive_gate_check: cache hit with STRICT_AC_GATE=yes + cached fail → blocks" {
    _setup_skills_symlink
    SHA=$(git rev-parse HEAD)
    # Seed cache with FAIL verdict (test scenario: AC failed in rdd-verifier run)
    cat > .rddf/state/.ac-verdict-test-change.json <<EOF
{"version":1,"change":"test-change","codebase_commit":"$SHA","verdict":[
  {"ac_id":"AC-1","status":"fail","confidence":0.95,"evidence":[],"reasoning":"missing implementation"}
],"ran_at":"2026-08-26T00:00:00Z","ran_by":"rdd-verifier"}
EOF

    source "$REPO_ROOT/_lib/archive.sh"
    AC_LLM_MOCK=yes STRICT_AC_GATE=yes \
        run archive_gate_check test-change "$TEST_TMP"

    # Cached fail + STRICT_AC_GATE → archive blocked
    [ "$status" -eq 1 ]
    [[ "$output" == *"AC verification failed"* ]]
}