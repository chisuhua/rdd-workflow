load ../test_helper

@test "archive-gate: blocks change with 0 completed tasks" {
    TMP="$BATS_TMPDIR/test-gate"
    mkdir -p "$TMP/openspec/changes/test-zero"
    printf -- '- [ ] Task 1\n- [ ] Task 2\n' > "$TMP/openspec/changes/test-zero/tasks.md"
    source "$PROJECT_ROOT/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-zero'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "未实现" ]]
}

@test "archive-gate: passes change with completed tasks" {
    TMP="$BATS_TMPDIR/test-gate2"
    mkdir -p "$TMP/openspec/changes/test-done"
    printf -- '- [x] Task 1\n- [x] Task 2\n' > "$TMP/openspec/changes/test-done/tasks.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-done'"
    [ "$status" -eq 0 ]
}

@test "archive-gate: skips with FORCE_ARCHIVE_INCOMPLETE" {
    TMP="$BATS_TMPDIR/test-gate3"
    mkdir -p "$TMP/openspec/changes/test-force"
    printf -- '- [ ] Task 1\n' > "$TMP/openspec/changes/test-force/tasks.md"
    FORCE_ARCHIVE_INCOMPLETE=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-force'"
    [ "$status" -eq 0 ]
}

@test "archive-gate: blocks when tasks.md is missing (no fail-open)" {
    TMP="$BATS_TMPDIR/test-gate4"
    mkdir -p "$TMP/openspec/changes/test-missing"
    source "$PROJECT_ROOT/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-missing'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "缺失" ]]
}

@test "archive-gate: reads tasks.md from explicit tasks_root (worktree path)" {
    # Simulate worktree path: tasks live at <wt>/openspec/changes/<name>/tasks.md
    # but the main repo openspec/changes/<name>/ doesn't exist.
    WT="$BATS_TMPDIR/wt-gate"
    MAIN="$BATS_TMPDIR/main-gate"
    mkdir -p "$WT/openspec/changes/worktree-change"
    printf -- '- [x] Done in worktree\n' > "$WT/openspec/changes/worktree-change/tasks.md"
    # main repo does NOT have openspec/changes/worktree-change
    source "$PROJECT_ROOT/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && archive_gate_check 'worktree-change' '$WT'"
    [ "$status" -eq 0 ]
}

@test "archive-gate: warns when change was previously archived (default WARN, exit 0)" {
    TMP="$BATS_TMPDIR/test-gate-rerun"
    mkdir -p "$TMP/openspec/changes/re-run-change"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/re-run-change/tasks.md"
    # Pre-existing archive entry (simulates prior rdd-builder P3 run)
    mkdir -p "$TMP/openspec/changes/archive/2026-09-21-re-run-change"
    touch "$TMP/openspec/changes/archive/2026-09-21-re-run-change/proposal.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 're-run-change'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already archived" ]]
    [[ "$output" =~ "2026-09-21-re-run-change" ]]
}

@test "archive-gate: blocks re-archive when RDDF_REQUIRE_ARCHIVE_UNIQUE=yes" {
    TMP="$BATS_TMPDIR/test-gate-unique"
    mkdir -p "$TMP/openspec/changes/uniq-change"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/uniq-change/tasks.md"
    mkdir -p "$TMP/openspec/changes/archive/2026-09-15-uniq-change"
    touch "$TMP/openspec/changes/archive/2026-09-15-uniq-change/proposal.md"
    RDDF_REQUIRE_ARCHIVE_UNIQUE=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'uniq-change'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "already archived" ]]
    [[ "$output" =~ "RDDF_REQUIRE_ARCHIVE_UNIQUE" ]]
}

@test "archive-gate: re-archive guard does not match different change names" {
    TMP="$BATS_TMPDIR/test-gate-nomatch"
    mkdir -p "$TMP/openspec/changes/fresh-change"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fresh-change/tasks.md"
    # Pre-existing archive entry for a DIFFERENT change name
    mkdir -p "$TMP/openspec/changes/archive/2026-09-10-other-change"
    touch "$TMP/openspec/changes/archive/2026-09-10-other-change/proposal.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fresh-change'"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "already archived" ]]
}

@test "archive-gate: file-presence warns when improvement.md table declares missing paths" {
    TMP="$BATS_TMPDIR/test-gate-fpwarn"
    mkdir -p "$TMP/openspec/changes/fpchange" "$TMP/.rddf/improvements"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fpchange/tasks.md"
    cat > "$TMP/.rddf/improvements/fpchange.md" <<'EOF'
# fpchange
## What Changes

| 文件/路径 | 类型 | 行数估算 |
|-----------|------|----------|
| `missing/file.py` | 新 | +100 |
| `also/missing.py` | 改 | +20 |
EOF
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fpchange'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "missing on disk" ]]
    [[ "$output" =~ "missing/file.py" ]]
    [[ "$output" =~ "also/missing.py" ]]
}

@test "archive-gate: file-presence blocks when RDDF_REQUIRE_FILES_PRESENT=yes" {
    TMP="$BATS_TMPDIR/test-gate-fpblock"
    mkdir -p "$TMP/openspec/changes/fpblock" "$TMP/.rddf/improvements"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fpblock/tasks.md"
    cat > "$TMP/.rddf/improvements/fpblock.md" <<'EOF'
# fpblock
## What Changes

| 文件/路径 | 类型 | 行数估算 |
|-----------|------|----------|
| `nonexistent.py` | 新 | +50 |
EOF
    RDDF_REQUIRE_FILES_PRESENT=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fpblock'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "RDDF_REQUIRE_FILES_PRESENT" ]]
}

@test "archive-gate: file-presence passes when all declared paths exist" {
    TMP="$BATS_TMPDIR/test-gate-fppass"
    mkdir -p "$TMP/openspec/changes/fppass" "$TMP/.rddf/improvements" "$TMP/existing"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fppass/tasks.md"
    touch "$TMP/existing/real.py"
    cat > "$TMP/.rddf/improvements/fppass.md" <<'EOF'
# fppass
## What Changes

| 文件/路径 | 类型 | 行数估算 |
|-----------|------|----------|
| `existing/real.py` | 新 | +10 |
EOF
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fppass'"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "missing on disk" ]]
}

@test "archive-gate: file-presence no-op when improvement.md has no file table" {
    TMP="$BATS_TMPDIR/test-gate-fpnotable"
    mkdir -p "$TMP/openspec/changes/fpnotable" "$TMP/.rddf/improvements"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fpnotable/tasks.md"
    cat > "$TMP/.rddf/improvements/fpnotable.md" <<'EOF'
# fpnotable
## What Changes

Just a paragraph, no table here.
EOF
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fpnotable'"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "missing on disk" ]]
}

@test "archive-gate: file-presence skipped when SKIP_FILE_PRESENCE_CHECK=yes" {
    TMP="$BATS_TMPDIR/test-gate-fpskip"
    mkdir -p "$TMP/openspec/changes/fpskip" "$TMP/.rddf/improvements"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fpskip/tasks.md"
    cat > "$TMP/.rddf/improvements/fpskip.md" <<'EOF'
# fpskip
## What Changes

| 文件/路径 | 类型 | 行数估算 |
|-----------|------|----------|
| `nope.py` | 新 | +5 |
EOF
    RDDF_REQUIRE_FILES_PRESENT=yes SKIP_FILE_PRESENCE_CHECK=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fpskip'"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "missing on disk" ]]
}

@test "archive-gate: file-presence ignores 删 (delete) rows" {
    TMP="$BATS_TMPDIR/test-gate-fpdel"
    mkdir -p "$TMP/openspec/changes/fpdel" "$TMP/.rddf/improvements"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fpdel/tasks.md"
    cat > "$TMP/.rddf/improvements/fpdel.md" <<'EOF'
# fpdel
## What Changes

| 文件/路径 | 类型 | 行数估算 |
|-----------|------|----------|
| `dead/code.py` | 删 | -50 |
EOF
    RDDF_REQUIRE_FILES_PRESENT=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fpdel'"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "missing on disk" ]]
}