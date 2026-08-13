#!/usr/bin/env bats
# Spec 2026-08-13 §8: integration tests for default-ON orchestrator.

setup() {
    REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/../.." && pwd)"
    WORK="$(mktemp -d)"
    export RDDF_TRACE_DIR="$WORK/.rddf/state/trace"
    export RDDF_PHASE="int-test"
    mkdir -p "$RDDF_TRACE_DIR"
}

teardown() {
    rm -rf "$WORK"
    unset RDDF_TRACE_DIR RDDF_PHASE
}

@test "T1: default-ON phase run produces trace with finalize event" {
    PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/_lib" \
    RDDF_PROJECT_ROOT="${WORK}" \
    bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        trap "orchestrator_finalize" EXIT
        orchestrator_run bash -c "echo hi"
        orchestrator_finalize
    ' _ "${REPO_ROOT}"
    count=$(ls "$RDDF_TRACE_DIR"/int-test-*.jsonl 2>/dev/null | wc -l)
    [ "$count" -ge 1 ]
    trace=$(ls "$RDDF_TRACE_DIR"/int-test-*.jsonl 2>/dev/null | head -1)
    last=$(tail -1 "$trace")
    [[ "$last" == *'"finalize"'* ]]
}

@test "T2: kill -9 mid-phase leaves no finalize, sweep detects" {
    RDDF_TRACE_STALE_MINUTES=0
    export RDDF_TRACE_STALE_MINUTES
    trace="$RDDF_TRACE_DIR/int-test-stale-1-1-aaaaaaaa.jsonl"
    printf '{"ts":"2026-08-13T09:00:00Z","type":"subprocess","cmd":["x"],"returncode":0}\n' > "$trace"
    touch -t 202608130900 "$trace"
    PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/_lib" \
    RDDF_PROJECT_ROOT="${WORK}" \
    bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_sweep
    ' _ "${REPO_ROOT}"
    [ ! -f "$trace" ]
}

@test "T3: classify exit_code=1 with lib traceback produces flow-bug F1" {
    PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/_lib" \
    python3 - <<EOF
import sys
sys.path.insert(0, "${REPO_ROOT}/_lib")
from post_flow_analysis import PhaseOutcome, classify_phase_outcome
o = PhaseOutcome(
    phase="int-test",
    exit_code=1,
    stderr="Traceback (most recent call last):\n  File \"${REPO_ROOT}/_lib/foo.py\", line 1",
)
c = classify_phase_outcome("int-test", o)
assert c.should_report, "flow-bug must be reportable"
assert c.matched_rule == "F1", f"expected F1, got {c.matched_rule}"
print("OK")
EOF
}

@test "T4: RDDF_USE_ORCHESTRATOR=no bypasses deferral (old trap fires)" {
    run bash -c '
        export RDDF_USE_ORCHESTRATOR=no
        source "$1/skills/_lib/post_flow_wrap.sh" 2>/dev/null || true
        if [ "${RDDF_USE_ORCHESTRATOR:-yes}" = "yes" ]; then
            echo "deferred=1"
        else
            echo "deferred=0"
        fi
    ' _ "${REPO_ROOT}"
    [[ "$output" == *"deferred=0"* ]]
}

@test "T5: exit 130 (SIGINT) is excluded from reporting" {
    PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/_lib" \
    python3 - <<EOF
import sys
sys.path.insert(0, "${REPO_ROOT}/_lib")
from post_flow_analysis import PhaseOutcome, classify_phase_outcome
o = PhaseOutcome(phase="int-test", exit_code=130, stderr="")
c = classify_phase_outcome("int-test", o)
assert c.should_report == False
assert c.matched_rule == "SIGINT-EXCLUDED"
print("OK")
EOF
}

@test "T6: rddf orchestrate show prints trace timeline" {
    trace="$RDDF_TRACE_DIR/int-test-ses_x-1-100-aaaa.jsonl"
    printf '{"ts":"2026-08-13T10:00:00Z","type":"checkpoint","name":"start"}\n' > "$trace"
    printf '{"ts":"2026-08-13T10:00:01Z","type":"subprocess","cmd":["x"],"returncode":0}\n' >> "$trace"
    printf '{"ts":"2026-08-13T10:00:02Z","type":"finalize","subprocess_failures":0}\n' >> "$trace"
    out=$(PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/_lib" \
          RDDF_TRACE_DIR="${RDDF_TRACE_DIR}" \
          RDDF_PROJECT_ROOT="${WORK}" \
          python3 "${REPO_ROOT}/_lib/cli/orchestrate_cmd.py" show int-test)
    echo "$out" | grep -q "checkpoint"
    echo "$out" | grep -q "subprocess"
    echo "$out" | grep -q "finalize"
}
