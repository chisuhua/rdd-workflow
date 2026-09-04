#!/usr/bin/env bats
#
# Wave 4 Change 3: KNOWN_FAILURES.txt shrink-only CI enforcement.
# Mirrors the .github/workflows/test.yml step locally so devs catch
# baseline growth before pushing.

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"
    BASELINE_FILE="$BATS_TMPDIR/known_failures_baseline.txt"
    CURRENT_FILE="$BATS_TMPDIR/known_failures_current.txt"
    cat > "$BASELINE_FILE" <<EOF
test_a # pre-existing WIP: original reason
test_b
test_c
EOF
}

teardown() {
    rm -f "$BASELINE_FILE" "$CURRENT_FILE"
}

shrink_only_check() {
    local baseline="$1"
    local current="$2"

    BASELINE_STRIPPED=$(sed -E 's/[[:space:]]+# (pre-existing|historical)[^[:alnum:]].*$//' "$baseline" | sed '/^[[:space:]]*$/d' | sort -u)
    CURRENT_STRIPPED=$(sed -E 's/[[:space:]]+# (pre-existing|historical)[^[:alnum:]].*$//' "$current" | sed '/^[[:space:]]*$/d' | sort -u)
    NEW_LINES=$(comm -13 <(echo "$BASELINE_STRIPPED") <(echo "$CURRENT_STRIPPED") || true)
    if [ -n "$NEW_LINES" ]; then
        return 1
    fi
    return 0
}

@test "KNOWN_FAILURES.txt can shrink (allowed)" {
    cat > "$CURRENT_FILE" <<EOF
test_a # pre-existing WIP: original reason
test_b
EOF
    run shrink_only_check "$BASELINE_FILE" "$CURRENT_FILE"
    [ "$status" -eq 0 ]
}

@test "KNOWN_FAILURES.txt unchanged → pass" {
    cp "$BASELINE_FILE" "$CURRENT_FILE"
    run shrink_only_check "$BASELINE_FILE" "$CURRENT_FILE"
    [ "$status" -eq 0 ]
}

@test "KNOWN_FAILURES.txt grows → fail" {
    cat > "$CURRENT_FILE" <<EOF
test_a # pre-existing WIP: original reason
test_b
test_c
test_d
EOF
    run shrink_only_check "$BASELINE_FILE" "$CURRENT_FILE"
    [ "$status" -ne 0 ]
}

@test "KNOWN_FAILURES.txt pre-existing-comment text changes allowed" {
    cat > "$CURRENT_FILE" <<EOF
test_a # pre-existing WIP: updated reason
test_b
test_c
EOF
    run shrink_only_check "$BASELINE_FILE" "$CURRENT_FILE"
    [ "$status" -eq 0 ]
}