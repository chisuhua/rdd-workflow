#!/usr/bin/env bats

# tests/integration/test_archive_tasks_gate.bats
#
# Verifies STRICT_TASKS_GATE / SKIP_TASKS_GATE escalation in
# _lib/archive.sh::check_tasks_completion (ADR-0018 pattern).

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    source "$REPO_ROOT/_lib/archive.sh"
}

write_tasks() {
    local tasks_path="$1"
    local content="$2"
    mkdir -p "$(dirname "$tasks_path")"
    printf "%s" "$content" > "$tasks_path"
}

make_change_dir() {
    local change_name="$1"
    local pct="$2"
    local total=10
    local done_count=$(( total * pct / 100 ))
    local open_count=$(( total - done_count ))

    local body=""
    for ((i = 1; i <= done_count; i++)); do
        body+="- [x] done task $i"$'\n'
    done
    for ((i = 1; i <= open_count; i++)); do
        body+="- [ ] open task $i"$'\n'
    done
    write_tasks "$REPO_ROOT/openspec/changes/$change_name/tasks.md" "$body"
}

@test "默认 warning: tasks 80% → exit 0 + 📋 + ⚠" {
    make_change_dir test-change-1 80
    unset STRICT_TASKS_GATE
    unset SKIP_TASKS_GATE
    run check_tasks_completion test-change-1 "$REPO_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"📋 tasks completion: 8/10"* ]]
    [[ "$output" == *"⚠"* ]]
}

@test "STRICT 升级: STRICT_TASKS_GATE=yes + tasks 80% → exit 1 + ❌ STRICT" {
    make_change_dir test-change-2 80
    export STRICT_TASKS_GATE=yes
    unset SKIP_TASKS_GATE
    run check_tasks_completion test-change-2 "$REPO_ROOT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"❌ STRICT_TASKS_GATE"* ]]
}

@test "SKIP 跳过: SKIP_TASKS_GATE=yes → exit 0 含 SKIP 标记" {
    make_change_dir test-change-3 0
    export SKIP_TASKS_GATE=yes
    unset STRICT_TASKS_GATE
    run check_tasks_completion test-change-3 "$REPO_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP"* ]]
}

@test "0 tasks edge case: change 无 tasks.md → exit 0 + INFO" {
    rm -rf "$REPO_ROOT/openspec/changes/test-change-4"
    unset STRICT_TASKS_GATE
    unset SKIP_TASKS_GATE
    run check_tasks_completion test-change-4 "$REPO_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"INFO"* ]]
    [[ "$output" == *"no tasks.md"* ]]
}

@test "完成度统计准确性: - [x] + - [X] 算 done, - [ ] 算未完成 (忽略 - [~]/- [WIP])" {
    write_tasks "$REPO_ROOT/openspec/changes/test-change-5/tasks.md" \
"- [x] task1
- [X] task2
- [ ] task3
- [~] task4
- [WIP] task5
- [x] task6
- [X] task7
- [ ] task8
- [~] task9
- [WIP] task10"
    unset STRICT_TASKS_GATE
    unset SKIP_TASKS_GATE
    run check_tasks_completion test-change-5 "$REPO_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"4/6"* ]]
}

@test "100% 完成: exit 0, 无 warning" {
    make_change_dir test-change-6 100
    unset STRICT_TASKS_GATE
    unset SKIP_TASKS_GATE
    run check_tasks_completion test-change-6 "$REPO_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"10/10 (100%)"* ]]
    [[ "$output" != *"⚠"* ]]
}

teardown() {
    rm -rf "$REPO_ROOT/openspec/changes/test-change-1" \
           "$REPO_ROOT/openspec/changes/test-change-2" \
           "$REPO_ROOT/openspec/changes/test-change-3" \
           "$REPO_ROOT/openspec/changes/test-change-4" \
           "$REPO_ROOT/openspec/changes/test-change-5" \
           "$REPO_ROOT/openspec/changes/test-change-6"
    unset STRICT_TASKS_GATE SKIP_TASKS_GATE
}