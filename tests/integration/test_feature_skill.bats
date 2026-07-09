#!/usr/bin/env bats

# Integration tests for the feature skill.
# These extract the embedded bash block from skills/feature.md and run it
# against fixture iteration.json files.

load ../test_helper

setup() {
    FEATURE_SKILL="$REPO_ROOT/skills/feature.md"
    TEST_PROJECT="$(mktemp -d)"
    cd "$TEST_PROJECT"
    git init -q
    mkdir -p .rddf/state
    export PROJECT_ROOT="$TEST_PROJECT"
    export PYTHONPATH="$REPO_ROOT"
}

teardown() {
    cd "$REPO_ROOT"
    rm -rf "$TEST_PROJECT"
}

run_feature() {
    run bash <(sed -n '/^```bash$/,/^```$/p' "$FEATURE_SKILL" | sed '1d;$d') "$@"
}

@test "feature summary populates iteration.json" {
    cat > .rddf/state/iteration.json <<EOF
{
  "version": 3,
  "updated_at": "2026-07-09T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {"name": "feature-stream-core", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "feature-stream"},
    {"name": "feature-stream-tests", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "feature-stream"},
    {"name": "fix-typo", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00"}
  ]
}
EOF
    run_feature summary
    [ "$status" -eq 0 ]
    [ -f .rddf/state/iteration.json ]
    run python3 -c "import json; d=json.load(open('.rddf/state/iteration.json')); assert 'feature_view' in d; assert 'feature-stream' in d['feature_view']['features']; assert '__ungrouped__' in d['feature_view']['features']; print('ok')"
    [ "$status" -eq 0 ]
    [[ "$output" == *"ok"* ]]
}

@test "feature graph emits mermaid block" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 3, "updated_at": "2026-07-09T00:00:00+00:00", "current_phase": "default", "changes": [{"name": "a", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "f-a"}]}
EOF
    run_feature graph
    [ "$status" -eq 0 ]
    [[ "$output" == *"\`\`\`mermaid"* ]]
    [[ "$output" == *"flowchart LR"* ]]
    [[ "$output" == *"f-a["* ]]
}

@test "feature status <name> lists changes" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 3, "updated_at": "2026-07-09T00:00:00+00:00", "current_phase": "default", "changes": [
  {"name": "a-core", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "f-a"},
  {"name": "a-tests", "status": "archived", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "f-a"}
]}
EOF
    run_feature status f-a
    [ "$status" -eq 0 ]
    [[ "$output" == *"## f-a"* ]]
    [[ "$output" == *"a-core"* ]]
    [[ "$output" == *"a-tests"* ]]
}

@test "feature order lists waves" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 3, "updated_at": "2026-07-09T00:00:00+00:00", "current_phase": "default", "changes": [
  {"name": "a-core", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "f-a"},
  {"name": "b-core", "status": "proposed", "added_at": "2026-07-09T00:00:00+00:00", "parent_feature": "f-b"}
]}
EOF
    run_feature order
    [ "$status" -eq 0 ]
    [[ "$output" == *"Wave 0"* ]]
}

@test "empty project returns error with guide-plan hint" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 3, "updated_at": "2026-07-09T00:00:00+00:00", "current_phase": "default", "changes": []}
EOF
    run_feature summary
    [ "$status" -eq 1 ]
    [[ "$output" == *"guide-plan"* ]]
}

@test "missing iteration.json errors with helpful message" {
    rm -f .rddf/state/iteration.json
    run_feature summary
    [ "$status" -eq 1 ]
    [[ "$output" == *"guide-plan"* ]]
}