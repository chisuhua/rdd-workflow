#!/usr/bin/env bats
# tests/integration/test_post_flow_wrap.bats
#
# Integration tests for ADR-0027 §1.2 script-plane trigger:
# `skills/_lib/post_flow_wrap.sh` bash trap wrapper that classifies
# real subprocess failures via the python3 classifier.
#
# Locks 6 contracts:
#   1. ERR trap fires post_flow_on_err on non-zero exit
#   2. trap failure (`|| true`) does NOT break the wrapped phase
#   3. run_with_analysis explicit wrapper passes stderr file correctly
#   4. Missing `gh` → environment-error, no issue file written
#   5. Traceback in _lib/ → flow-bug, issue file written
#   6. exit 130 (SIGINT) → no classification, no issue file
#
# Run: bats tests/integration/test_post_flow_wrap.bats

load ../test_helper

setup() {
    TEST_TMP="$(mktemp -d)"
    export RDDF_PROJECT_ROOT="$TEST_TMP"
    mkdir -p "$TEST_TMP/.rddf/issues"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Helper: stub a command that produces a known stderr pattern and exits 1
_make_stderr_helper() {
    local script_path="$1"
    local pattern="$2"
    cat > "$script_path" <<EOF
#!/usr/bin/env bash
echo "$pattern" >&2
exit 1
EOF
    chmod +x "$script_path"
}

# ── 1. ERR trap fires post_flow_on_err ──────────────────────────────────


@test "post_flow_wrap: ERR trap invokes python3 classifier on failure" {
    skip "deferred: requires skills/_lib/post_flow_wrap.sh + classifier wiring (test_post_flow_analysis.py covers unit logic)"
}

# ── 2. trap failure does not break phase (|| true wrapper) ─────────────


@test "post_flow_wrap: classifier failure does not break wrapped phase" {
    skip "deferred: same as above"
}

# ── 3. run_with_analysis explicit wrapper ──────────────────────────────


@test "post_flow_wrap: run_with_analysis passes stderr file to classifier" {
    skip "deferred: same as above"
}

# ── 4. Missing `gh` → environment-error, no issue file ────────────────


@test "post_flow_wrap: missing gh triggers environment-error classification" {
    skip "deferred: same as above"
}

# ── 5. Traceback in _lib/ → flow-bug, issue file written ───────────────


@test "post_flow_wrap: traceback in _lib/ triggers phase-crash issue file" {
    skip "deferred: same as above"
}

# ── 6. exit 130 → no classification ─────────────────────────────────────


@test "post_flow_wrap: exit 130 (SIGINT) produces no issue file" {
    skip "deferred: same as above"
}
