#!/usr/bin/env bats
# tests/integration/test_planner_feedback_cli.bats
# Stage 3 Change 3: planner feedback CLI subcommand contract.

load ../test_helper

@test "planner feedback: --help shows lifecycle commands" {
    run python3 -m _lib.cli planner feedback --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "--acknowledge" ]]
    [[ "$output" =~ "--resolve" ]]
    [[ "$output" =~ "--dismiss" ]]
    [[ "$output" =~ "--prune-resolved" ]]
}

@test "planner feedback: lists open entries by default when feedback exists" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state" "$TEST_TMP/.rddf/improvements"
    cat > "$TEST_TMP/.rddf/improvements/feat-x.md" <<'EOF'
---
name: feat-x
priority: P1
---
# feat-x
EOF
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP" >/dev/null 2>&1
    python3 -m _lib.cli planner feedback --recompute --project-root "$TEST_TMP" >/dev/null 2>&1
    run python3 -m _lib.cli planner feedback --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "open" ]]
}

@test "planner feedback: --status open filters to open entries only" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state" "$TEST_TMP/.rddf/improvements"
    cat > "$TEST_TMP/.rddf/improvements/feat-y.md" <<'EOF'
---
name: feat-y
priority: P2
---
# feat-y
EOF
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP" >/dev/null 2>&1
    python3 -m _lib.cli planner feedback --recompute --project-root "$TEST_TMP" >/dev/null 2>&1
    run python3 -m _lib.cli planner feedback --status open --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
}

@test "planner feedback: --acknowledge <id> transitions open to acknowledged" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state" "$TEST_TMP/.rddf/improvements"
    cat > "$TEST_TMP/.rddf/improvements/feat-z.md" <<'EOF'
---
name: feat-z
priority: P1
---
# feat-z
EOF
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP" >/dev/null 2>&1
    python3 -m _lib.cli planner feedback --recompute --project-root "$TEST_TMP" >/dev/null 2>&1
    FID=$(python3 -c "
import json
with open('$TEST_TMP/.rddf/state/.planner-feedback.json') as f:
    d = json.load(f)
print(d['feedbacks'][0]['feedback_id'])
")
    run python3 -m _lib.cli planner feedback --acknowledge "$FID" --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
with open('$TEST_TMP/.rddf/state/.planner-feedback.json') as f:
    d = json.load(f)
assert d['feedbacks'][0]['status'] == 'acknowledged', d['feedbacks'][0]['status']
print('OK')
"
    [ "$status" -eq 0 ]
}

@test "planner feedback: --resolve <id> transitions to resolved" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state" "$TEST_TMP/.rddf/improvements"
    cat > "$TEST_TMP/.rddf/improvements/feat-w.md" <<'EOF'
---
name: feat-w
priority: P1
---
# feat-w
EOF
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP" >/dev/null 2>&1
    python3 -m _lib.cli planner feedback --recompute --project-root "$TEST_TMP" >/dev/null 2>&1
    FID=$(python3 -c "
import json
with open('$TEST_TMP/.rddf/state/.planner-feedback.json') as f:
    d = json.load(f)
print(d['feedbacks'][0]['feedback_id'])
")
    run python3 -m _lib.cli planner feedback --resolve "$FID" --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
with open('$TEST_TMP/.rddf/state/.planner-feedback.json') as f:
    d = json.load(f)
assert d['feedbacks'][0]['status'] == 'resolved'
print('OK')
"
    [ "$status" -eq 0 ]
}

@test "planner feedback: --prune-resolved removes resolved/dismissed entries" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state" "$TEST_TMP/.rddf/improvements"
    cat > "$TEST_TMP/.rddf/improvements/feat-v.md" <<'EOF'
---
name: feat-v
priority: P1
---
# feat-v
EOF
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP" >/dev/null 2>&1
    python3 -m _lib.cli planner feedback --recompute --project-root "$TEST_TMP" >/dev/null 2>&1
    FID=$(python3 -c "
import json
with open('$TEST_TMP/.rddf/state/.planner-feedback.json') as f:
    d = json.load(f)
print(d['feedbacks'][0]['feedback_id'])
")
    python3 -m _lib.cli planner feedback --resolve "$FID" --project-root "$TEST_TMP" >/dev/null 2>&1
    run python3 -m _lib.cli planner feedback --prune-resolved --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
with open('$TEST_TMP/.rddf/state/.planner-feedback.json') as f:
    d = json.load(f)
assert len(d['feedbacks']) == 0, f'expected empty, got {len(d[\"feedbacks\"])}'
print('OK')
"
    [ "$status" -eq 0 ]
}