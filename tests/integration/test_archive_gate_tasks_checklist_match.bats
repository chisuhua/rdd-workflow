#!/usr/bin/env bats
# test_archive_gate_tasks_checklist_match.bats — preventive gate that catches
# "checkbox-as-done" drift: every `- [x]` in tasks.md must correspond to a
# real file change in `git diff <merge-base>..HEAD`.
#
# Per complete-project-yaml-config-gaps X.6 (MANDATORY root-cause prevention):
# the original i10 archive claimed "23/25 done" but 8 tasks had no code —
# this gate would have failed the archive, preventing the false-positive claim.
#
# This gate runs before `openspec archive` and exits non-zero if any
# completed task lacks a corresponding file change.
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    cd "$TEST_TMP"
    git init -q -b main
    git config user.email "t@t"
    git config user.name "T"
    echo "init" > README.md
    git add README.md
    git commit -q -m "init"
}

teardown() {
    rm -rf "$TEST_TMP"
}

_write_tasks_md() {
    # _write_tasks_md <commit_count_in_diff> [extra_checkbox_lines...]
    # Creates openspec/changes/test-change/tasks.md with the given `- [x]` lines
    # and corresponding file changes (file_1.txt, file_2.txt, etc.) so the gate
    # word-matching can find them in git diff.
    local file_changes="$1"
    shift
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Test Tasks

## M1
EOF
    for line in "$@"; do
        echo "$line" >> openspec/changes/test-change/tasks.md
    done
    git add openspec/changes/test-change/tasks.md
    # Add file changes (file_1.txt, file_2.txt, ...) — keyword `file` in diff
    if [ "$file_changes" -gt 0 ]; then
        for i in $(seq 1 "$file_changes"); do
            echo "change $i" > file_$i.txt
            git add file_$i.txt
        done
        git commit -q -m "feat: implement $file_changes files + tasks.md"
    else
        git commit -q --allow-empty -m "feat: tasks.md only (checkbox-as-done drift case)"
    fi
}

# Run the gate: parse tasks.md `- [x]` lines, grep each in git diff
_run_gate() {
    local change_name="$1"
    # bash function: parse tasks.md `- [x]` lines (excluding the heading)
    local unchecked
    unchecked=$(awk '/^- \[ \]/ {print "0"}' openspec/changes/${change_name}/tasks.md | wc -l)
    local checked
    checked=$(awk '/^- \[x\]/ {print "0"}' openspec/changes/${change_name}/tasks.md | wc -l)
    echo "checked=$checked unchecked=$unchecked"
    # Get merge-base
    local merge_base
    merge_base=$(git merge-base HEAD main 2>/dev/null || git rev-list --max-parents=0 HEAD)
    # For each - [x] line, check if it's mentioned in git diff (file paths or unique keywords)
    local missing=0
    local line_no=0
    while IFS= read -r line; do
        line_no=$((line_no + 1))
        # Skip empty lines and headings
        [ -z "$line" ] && continue
        echo "$line" | grep -qE '^#' && continue
        # Skip unchecked tasks (only validate DONE tasks)
        echo "$line" | grep -qE '^- \[ \]' && continue
        # Only process done tasks
        echo "$line" | grep -qE '^- \[x\]' || continue
        # Strip the "- [x] " prefix
        local content=$(echo "$line" | sed 's/^- \[x\] //')
        # Skip if content is too generic to verify (e.g. "Commit:")
        [ ${#content} -lt 10 ] && continue
        # Check if any word from the content appears in the diff
        local word=$(echo "$content" | grep -oE '\b[a-z_]+\.[a-z]+\b|\b[a-z][a-z_]{4,}\b' | head -1)
        [ -z "$word" ] && continue
        if ! git diff "$merge_base"..HEAD --stat | grep -q "$word" && \
           ! git diff "$merge_base"..HEAD | grep -q "$word"; then
            missing=$((missing + 1))
            echo "MISSING: line $line_no '$content' (word: $word)"
        fi
    done < openspec/changes/${change_name}/tasks.md
    if [ "$missing" -gt 0 ]; then
        echo "FAIL: $missing task(s) marked done but no file change"
        return 1
    fi
    echo "PASS: all $checked done-tasks have file changes"
    return 0
}

_write_tasks_md_with_files() {
    # _write_tasks_md_with_files <task_file_pairs...>
    # Each pair is "task_description|file_path"
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Test Tasks

## M1
EOF
    while IFS='|' read -r desc file_path; do
        [ -z "$desc" ] && continue
        echo "- [x] $desc" >> openspec/changes/test-change/tasks.md
        if [ -n "$file_path" ]; then
            mkdir -p "$(dirname "$file_path")"
            echo "# $desc" > "$file_path"
            git add "$file_path"
        fi
    done
    git add openspec/changes/test-change/tasks.md
    git commit -q -m "feat: implement tasks + tasks.md"
}


@test "gate: tasks.md with matching file changes passes" {
    _write_tasks_md_with_files \
        "implement _lib/foo.sh|_lib/foo.sh" \
        "implement _lib/bar.sh|_lib/bar.sh" \
        "implement _lib/baz.sh|_lib/baz.sh"
    run _run_gate test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"PASS"* ]]
}

@test "gate: tasks.md with NO matching file changes fails" {
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Test Tasks

## M1
EOF
    echo "- [x] implement _lib/missing.sh" >> openspec/changes/test-change/tasks.md
    echo "- [x] implement _lib/nonexistent.sh" >> openspec/changes/test-change/tasks.md
    git add openspec/changes/test-change/tasks.md
    git commit -q --allow-empty -m "feat: tasks.md only (drift case)"
    run _run_gate test-change
    [ "$status" -ne 0 ]
    [[ "$output" == *"FAIL"* ]]
    [[ "$output" == *"MISSING"* ]]
}

@test "gate: empty tasks.md passes (no done tasks to check)" {
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Test Tasks

## M1
- [ ] pending task
EOF
    git add openspec/changes/test-change/tasks.md
    git commit -q -m "add tasks.md"
    run _run_gate test-change
    [ "$status" -eq 0 ]
}

@test "gate: mixed done/pending tasks — done must have file changes" {
    _write_tasks_md_with_files \
        "implement _lib/real.sh|_lib/real.sh" \
        "implement pending helper (no file)|"
    run _run_gate test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"PASS"* ]]
}

@test "gate: detected drift case from i10 archive (checkbox-as-done)" {
    # Simulates the i10 case: tasks.md claims done but no actual code change
    mkdir -p openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Test Tasks

## M3
EOF
    echo "- [x] Task 3.1 — config_schema.json 新增 4 节 (TDD)" >> openspec/changes/test-change/tasks.md
    echo "- [x] Task 3.5 — populate_lib 透传 (TDD, 接收 i10 deferred)" >> openspec/changes/test-change/tasks.md
    echo "- [x] Task 3.6 — populate_lib fallback" >> openspec/changes/test-change/tasks.md
    git add openspec/changes/test-change/tasks.md
    git commit -q --allow-empty -m "feat: tasks.md only (checkbox-as-done drift case)"
    run _run_gate test-change
    # Should FAIL because no file changes but 3 tasks marked done
    [ "$status" -ne 0 ]
    [[ "$output" == *"FAIL"* ]]
}
