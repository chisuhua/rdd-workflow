#!/usr/bin/env bats
# Integration tests for `rddf feedback` CLI.

load test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/improvements"
    mkdir -p "$TEST_TMP/.rddf/state"
    cd "$TEST_TMP"
    git init -q .
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "feedback: add appends entry to improvement file" {
    cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
---
# foo proposal
EOF

    run python3 -m _lib.cli feedback add foo \
        --from guide-design \
        --kind needs-revision \
        --body "missing acceptance criteria" \
        --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "Feedback appended" ]]
    grep -q "## Feedback" .rddf/improvements/foo.md
    grep -q "missing acceptance criteria" .rddf/improvements/foo.md
}

@test "feedback: add increments revision_count" {
    cat > .rddf/improvements/bar.md <<'EOF'
---
name: bar
revision_count: 0
max_revisions: 3
---
EOF

    python3 -m _lib.cli feedback add bar \
        --from guide-design \
        --kind needs-revision \
        --body "test" \
        --project-root "$TEST_TMP"

    grep -q "revision_count: 1" .rddf/improvements/bar.md
}

@test "feedback: loop guard blocks 4th revision" {
    cat > .rddf/improvements/baz.md <<'EOF'
---
name: baz
revision_count: 0
max_revisions: 3
---
EOF

    for i in 1 2 3; do
        python3 -m _lib.cli feedback add baz \
            --from guide-design \
            --kind needs-revision \
            --body "attempt $i" \
            --project-root "$TEST_TMP"
    done

    run python3 -m _lib.cli feedback add baz \
        --from guide-design \
        --kind needs-revision \
        --body "4th attempt" \
        --project-root "$TEST_TMP"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOOP EXCEEDED" ]]
}

@test "feedback: invalid source returns non-zero" {
    cat > .rddf/improvements/qux.md <<'EOF'
---
name: qux
---
EOF

    run python3 -m _lib.cli feedback add qux \
        --from bogus-source \
        --kind noted \
        --body "test" \
        --project-root "$TEST_TMP"

    [ "$status" -ne 0 ]
}

@test "feedback: missing proposal file returns exit 1" {
    run python3 -m _lib.cli feedback add nonexistent \
        --from human \
        --kind noted \
        --body "test" \
        --project-root "$TEST_TMP"

    [ "$status" -eq 1 ]
}

@test "feedback: --ref-change cross-references change" {
    cat > .rddf/improvements/ref.md <<'EOF'
---
name: ref
---
EOF

    python3 -m _lib.cli feedback add ref \
        --from rdd-verifier \
        --kind ac-fail \
        --body "AC #3 not met" \
        --ref-change change-foo \
        --project-root "$TEST_TMP"

    grep -q "ref_change\*\*: change-foo" .rddf/improvements/ref.md
}

@test "feedback: show-schema outputs valid JSON" {
    run python3 -m _lib.cli feedback show-schema --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; json.loads(sys.stdin.read())"
}

@test "feedback: list outputs file content" {
    cat > .rddf/improvements/listable.md <<'EOF'
---
name: listable
---
# My Proposal
EOF

    run python3 -m _lib.cli feedback list listable --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "My Proposal" ]]
}

@test "feedback: --dry-run does not modify file" {
    cat > .rddf/improvements/dry.md <<'EOF'
---
name: dry
---
EOF
    ORIGINAL=$(cat .rddf/improvements/dry.md)

    run python3 -m _lib.cli feedback add dry \
        --from human \
        --kind noted \
        --body "would write" \
        --dry-run \
        --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [ "$(cat .rddf/improvements/dry.md)" = "$ORIGINAL" ]
}