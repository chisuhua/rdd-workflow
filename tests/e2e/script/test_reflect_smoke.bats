#!/usr/bin/env bats
# tests/e2e/script/test_reflect_smoke.bats
#
# A-layer e2e (CI must-pass): reflect_engine + dedup + cooldown + draft routing.
# Spec: docs/superpowers/specs/2026-09-14-reflect-e2e-coverage-design.md
#
# Strategy:
#   - Invoke ReflectEngine.analyze() against an isolated fake git project under
#     $BATS_TEST_TMPDIR via tests/e2e/_lib/reflect_invoke.py (env-var passing,
#     Oracle C1 safe).
#   - Assert on 1-line JSON envelope (action/fingerprint/reason + draft).
#   - Verify zero pollution on $REPO_ROOT via isolation::verify_zero_pollution.
#
# Note: Only ARCH phase hook is wired in production
# (skills/rdd-arch/scripts/write_arch_handoff.sh:48-66). PLAN/SHIP phases are
# exercised by directly invoking ReflectEngine (no production hook wiring
# required for engine-behavior e2e).

load ../../test_helper
# E2E helpers live under tests/e2e/_lib/ (not tests/_lib/), so source directly.
# shellcheck source=../_lib/isolation.bash
source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
# shellcheck source=../_lib/script_smoke.bash
source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
# test_full_workflow_fixture provides invoke_planner_stage_with_reflect
# (added in add-plan-done-reflect-hook, FU-3).
# shellcheck source=/dev/null
source "$REPO_ROOT/tests/_lib/test_full_workflow_fixture.bash"

setup() {
    export SMOKE_FAKE_ROOT="$BATS_TEST_TMPDIR/fake-reflect"
    script_smoke::setup_fake_project "$SMOKE_FAKE_ROOT"
    BASELINE_FILE="$BATS_TEST_TMPDIR/baseline.sha256"
    isolation::snapshot_repo_state "$BASELINE_FILE"
    # Defensive: A-layer fixtures (e.g. test_full_workflow_e2e.bats teardown)
    # export SKIP_WORKFLOW_REFLECTION=1 to suppress side-effects. Ensure it
    # is unset so reflect actually runs in this test.
    unset SKIP_WORKFLOW_REFLECTION
}

teardown() {
    script_smoke::cleanup_fake_project "$SMOKE_FAKE_ROOT"
    isolation::verify_zero_pollution "$BASELINE_FILE" || return 1
}

# Helper: invoke reflect_invoke.py with given phase + failures + optional draft.
# Args: <phase> <failures_json> [draft_flag]
run_reflect() {
    local phase="$1"
    local failures="$2"
    local draft="${3:-}"
    REFLECT_PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
    REPO_ROOT="$REPO_ROOT" \
    REFLECT_PHASE="$phase" \
    REFLECT_FAILURES_JSON="$failures" \
    REFLECT_DRAFT="$draft" \
    run python3 "$REPO_ROOT/tests/e2e/_lib/reflect_invoke.py"
}

# ─── R-E1: arch cold start, 0 failures → action=none ─────────────────────────

@test "reflect R-E1: arch 0 failures -> action=none, no friction log written" {
    run_reflect arch '[]'
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "none"'* ]]
    [ ! -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-friction.log" ]
}

# ─── R-E2: arch with 1 failure → log_friction + friction log written ─────────

@test "reflect R-E2: arch with 1 gate_fail -> log_friction + friction log" {
    run_reflect arch '[{"type":"gate_fail","gate":"arch-done","error":"ADR quality gate failed"}]'
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "log_friction"'* ]]
    [[ "$output" == *'"fingerprint": "arch:arch-done:quality-gate-fail"'* ]]
    [ -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-friction.log" ]
    grep -q 'arch:arch-done:quality-gate-fail' "$SMOKE_FAKE_ROOT/.rddf/state/reflect-friction.log"
}

# ─── R-E7: SKIP_WORKFLOW_REFLECTION=1 → action=skipped ──────────────────────

@test "reflect R-E7: SKIP_WORKFLOW_REFLECTION=1 -> action=skipped" {
    REFLECT_PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
    REPO_ROOT="$REPO_ROOT" \
    REFLECT_PHASE=arch \
    REFLECT_FAILURES_JSON='[{"type":"gate_fail","gate":"arch-done","error":"x gate failed"}]' \
    SKIP_WORKFLOW_REFLECTION=1 \
    run python3 "$REPO_ROOT/tests/e2e/_lib/reflect_invoke.py"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "skipped"'* ]]
    [[ "$output" == *'SKIP_WORKFLOW_REFLECTION=1'* ]]
    [ ! -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-friction.log" ]
}

# ─── R-E3: plan with 2 same-cause failures → propose_issue ───────────────────
# Also asserts 1-failure boundary: below-threshold → action=none.

@test "reflect R-E3: plan 2 same-cause -> propose_issue + cooldown recorded; 1 failure -> none" {
    local f2='[{"type":"gate_fail","gate":"plan-done","error":"quality gate failed"},
               {"type":"gate_fail","gate":"plan-done","error":"quality gate failed"}]'
    run_reflect plan "$f2"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "propose_issue"'* ]]
    [[ "$output" == *'"fingerprint": "plan:plan-done:quality-gate-fail"'* ]]
    # propose_issue path writes cooldown file (reflect_engine.py:152)
    [ -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-cooldown.json" ]
    grep -q 'plan:plan-done:quality-gate-fail' "$SMOKE_FAKE_ROOT/.rddf/state/reflect-cooldown.json"

    # Below-threshold boundary: 1 distinct failure (different error string)
    # must NOT meet the >=2 same-cause threshold (reflect_engine._meets_threshold L161-174).
    run_reflect plan '[{"type":"gate_fail","gate":"plan-done","error":"unique error v2"}]'
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "none"'* ]]
}

# ─── R-E4: ship with 1 unrecovered_failure → propose_issue (threshold bypass) ─

@test "reflect R-E4: ship with 1 unrecovered_failure -> propose_issue (threshold bypass)" {
    run_reflect ship '[{"type":"unrecovered_failure","gate":"archive","error":"merge timeout after 3 retries"}]'
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "propose_issue"'* ]]
    [[ "$output" == *'"fingerprint": "ship:archive:timeout"'* ]]
    # _derive_phase (L176-185): unrecovered_failure forces 'ship' semantic,
    # _meets_threshold (L161-174): any unrecovered_failure type bypasses >=2 check.
}

# ─── R-E5: pre-seeded improvement matches fingerprint → action=matched ───────

@test "reflect R-E5: pre-seeded .rddf/improvements/*.md matches fingerprint -> matched" {
    mkdir -p "$SMOKE_FAKE_ROOT/.rddf/improvements"
    # Content must contain >=1 fingerprint keyword. DedupMatcher._fuzzy_match
    # splits fingerprint into lowercase tokens and checks >=1 token appears.
    # Fingerprint tokens for "plan:plan-done:quality-gate-fail":
    #   plan, plan, done, quality, gate, fail (split on : and -)
    cat > "$SMOKE_FAKE_ROOT/.rddf/improvements/plan-done-quality-gate-fail.md" <<'EOF'
# Fix plan-done quality gate fail
## Why
plan done quality gate fail keeps recurring in plan phase.
EOF

    local f2='[{"type":"gate_fail","gate":"plan-done","error":"quality gate failed"},
               {"type":"gate_fail","gate":"plan-done","error":"quality gate failed"}]'
    run_reflect plan "$f2"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "matched"'* ]]
    [[ "$output" == *'"matched_source": ".rddf/improvements"'* ]]
    [[ "$output" == *'"matched_name": "plan-done-quality-gate-fail"'* ]]
}

# ─── R-E6: fingerprint within 24h cooldown → action=none ─────────────────────

@test "reflect R-E6: fingerprint within 24h cooldown -> action=none (within cooldown window)" {
    # Pre-seed cooldown file with the same fingerprint the test will trigger,
    # so reflect_engine.CooldownManager.is_cooling() returns True BEFORE the
    # threshold/dedup checks (reflect_engine.py:137).
    mkdir -p "$SMOKE_FAKE_ROOT/.rddf/state"
    REFLECT_PROJECT_ROOT="$SMOKE_FAKE_ROOT" python3 - <<'PYEOF'
import json, os, time
fp = "plan:plan-done:quality-gate-fail"
now = time.time()
with open(os.path.join(os.environ["REFLECT_PROJECT_ROOT"],
                       ".rddf/state/reflect-cooldown.json"), "w") as f:
    json.dump({fp: {"first_triggered_at": now, "last_triggered_at": now}}, f)
PYEOF

    local f2='[{"type":"gate_fail","gate":"plan-done","error":"quality gate failed"},
               {"type":"gate_fail","gate":"plan-done","error":"quality gate failed"}]'
    run_reflect plan "$f2"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "none"'* ]]
    [[ "$output" == *'within cooldown window'* ]]
}

# ─── R-E8: isolation contract — propose_issue path does not pollute ──────────

@test "reflect R-E8: propose_issue path leaves improvements/ and openspec/ untouched" {
    # Seed sentinel improvement file: count + content must survive the run.
    mkdir -p "$SMOKE_FAKE_ROOT/.rddf/improvements"
    echo "sentinel content" > "$SMOKE_FAKE_ROOT/.rddf/improvements/sentinel.md"
    local before_count
    before_count=$(ls "$SMOKE_FAKE_ROOT/.rddf/improvements/" | wc -l)

    local f2='[{"type":"gate_fail","gate":"plan-done","error":"quality gate failed"},
               {"type":"gate_fail","gate":"plan-done","error":"quality gate failed"}]'
    run_reflect plan "$f2"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"action": "propose_issue"'* ]]

    # Sentinel improvement file preserved exactly.
    [ -f "$SMOKE_FAKE_ROOT/.rddf/improvements/sentinel.md" ]
    [ "$(cat "$SMOKE_FAKE_ROOT/.rddf/improvements/sentinel.md")" = "sentinel content" ]
    [ "$(ls "$SMOKE_FAKE_ROOT/.rddf/improvements/" | wc -l)" -eq "$before_count" ]

    # No openspec/changes pollution.
    [ -z "$(find "$SMOKE_FAKE_ROOT/openspec/changes" -name '*.md' 2>/dev/null)" ]

    # Cooldown record lives in fake root, not repo root (verified by teardown).
}

# ─── R-E9: draft_issue() template shape + dual repo routing ──────────────────

@test "reflect R-E9: draft_issue shape + repo routing (default + chisuhua)" {
    local f2='[{"type":"gate_fail","gate":"plan-done","error":"quality gate failed"},
               {"type":"gate_fail","gate":"plan-done","error":"quality gate failed"}]'
    run_reflect plan "$f2" 1
    [ "$status" -eq 0 ]
    # Default routing: fake project has no git origin remote → 'unknown/unknown'
    [[ "$output" == *'"target_repo": "unknown/unknown"'* ]]
    [[ "$output" == *'"title": "[reflect] plan: plan:plan-done:quality-gate-fail"'* ]]
    [[ "$output" == *'"labels": ["auto-reflect", "plan"]'* ]]
    [[ "$output" == *'"body_has_analysis": true'* ]]

    # Upstream routing: error string contains 'skills/_lib/' → 'chisuhua/rdd-workflow'
    # (reflect_engine._route_issue L213-229: substring match on errors list)
    # Clear cooldown so the new fingerprint can trigger propose_issue path.
    rm -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-cooldown.json"
    local f_sk='[{"type":"gate_fail","gate":"plan-done","error":"crash in skills/_lib/x.py"},
                 {"type":"gate_fail","gate":"plan-done","error":"crash in skills/_lib/x.py"}]'
    run_reflect plan "$f_sk" 1
    [ "$status" -eq 0 ]
    [[ "$output" == *'"target_repo": "chisuhua/rdd-workflow"'* ]]
}

# ─── R-E10: planner_stage_exit.sh post-handoff reflect hook integration ──────
# Verifies the production wiring of plan-done reflect hook added by
# add-plan-done-reflect-hook (FU-3). Runs the REAL planner_stage_exit.sh
# against a fake project passing 双门控, then asserts:
#   1. .planner-handoff.json written successfully (reflect did not block)
#   2. reflect hook ran (no event_log.json → action=none → no friction log)
#   3. handoff contract v1 keys present
#
# Spec: .rddf/improvements/add-plan-done-reflect-hook.md Acceptance #6

@test "reflect R-E10: planner_stage_exit.sh post-handoff reflect hook is non-blocking" {
    # Prepare fake project to pass planner-done 双门控:
    #   门控1: .rddf/roadmap.md must exist
    #   门控2: .planner-state.json::recommended_route != "unknown"
    touch "$SMOKE_FAKE_ROOT/.rddf/roadmap.md"
    mkdir -p "$SMOKE_FAKE_ROOT/.rddf/state"
    echo '{"recommended_route": "simple", "active_projects": []}' \
        > "$SMOKE_FAKE_ROOT/.rddf/state/.planner-state.json"
    mkdir -p "$SMOKE_FAKE_ROOT/openspec/changes/test-r10"
    echo "# test-r10" > "$SMOKE_FAKE_ROOT/openspec/changes/test-r10/proposal.md"
    git -C "$SMOKE_FAKE_ROOT" add -A
    git -C "$SMOKE_FAKE_ROOT" commit -q -m "e2e: seed planner-done gate inputs"

    # Invoke real planner_stage_exit.sh via fixture helper
    invoke_planner_stage_with_reflect "$SMOKE_FAKE_ROOT" "test-r10"

    # 1. Handoff written successfully (reflect hook did NOT block the script)
    [ -f "$SMOKE_FAKE_ROOT/.rddf/state/.planner-handoff.json" ]
    # 2. v1 contract keys present (per _lib/planner_handoff.py write_planner_handoff)
    grep -q '"schema": "planner-handoff-v1"' "$SMOKE_FAKE_ROOT/.rddf/state/.planner-handoff.json"
    grep -q '"owner": "rdd-planner"' "$SMOKE_FAKE_ROOT/.rddf/state/.planner-handoff.json"
    # 3. reflect hook ran with empty failures (no event_log.json in fake root)
    #    → action=none → no friction log, no cooldown mutation, no proposal draft
    [ ! -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-friction.log" ]
    [ ! -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-cooldown.json" ]
}

# ─── R-E11: SKIP_WORKFLOW_REFLECTION=1 + planner_stage_exit.sh still succeeds ─
# Verifies the SKIP guard in the plan-done reflect hook is non-blocking.
# Even with SKIP=1, planner_stage_exit.sh must complete .planner-handoff.json.
#
# Spec: .rddf/improvements/add-plan-done-reflect-hook.md Acceptance #7

@test "reflect R-E11: SKIP_WORKFLOW_REFLECTION=1 + planner_stage_exit.sh still succeeds" {
    touch "$SMOKE_FAKE_ROOT/.rddf/roadmap.md"
    mkdir -p "$SMOKE_FAKE_ROOT/.rddf/state"
    echo '{"recommended_route": "complex", "active_projects": []}' \
        > "$SMOKE_FAKE_ROOT/.rddf/state/.planner-state.json"
    mkdir -p "$SMOKE_FAKE_ROOT/openspec/changes/test-r11"
    echo "# test-r11" > "$SMOKE_FAKE_ROOT/openspec/changes/test-r11/proposal.md"
    git -C "$SMOKE_FAKE_ROOT" add -A
    git -C "$SMOKE_FAKE_ROOT" commit -q -m "e2e: seed planner-done gate inputs"

    # Run with SKIP guard → reflect hook short-circuits at L82 (analyze top guard)
    SKIP_WORKFLOW_REFLECTION=1 \
        invoke_planner_stage_with_reflect "$SMOKE_FAKE_ROOT" "test-r11"

    # Handoff still written (skip guard is non-blocking)
    [ -f "$SMOKE_FAKE_ROOT/.rddf/state/.planner-handoff.json" ]
    # No reflect side-effects (skipped)
    [ ! -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-friction.log" ]
    [ ! -f "$SMOKE_FAKE_ROOT/.rddf/state/reflect-cooldown.json" ]
}
