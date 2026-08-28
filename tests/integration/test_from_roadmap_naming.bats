load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-from-roadmap-naming"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO/.rddf/improvements"
    mkdir -p "$TEST_REPO/.rddf/roadmap/phases"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    cat > ".rddf/roadmap/phases/phase-1.md" <<EOF
---
phase: phase-1
---
主题: 定时循环
EOF
    SH="$PROJECT_ROOT/skills/add-improve/scripts/from_roadmap.sh"
}

teardown() {
    rm -rf "$TEST_REPO"
}

@test "from_roadmap: default naming backward compat (from-roadmap-<phase>-<category>)" {
    run bash "$SH" --from-roadmap phase-1/arch --theme "定时循环" --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
}

@test "from_roadmap: --name-prefix overrides naming" {
    run bash "$SH" --from-roadmap phase-1/arch --theme "定时循环" --project-root "$TEST_REPO" --name-prefix "fix-audit-"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/fix-audit-phase-1-arch.md" ]
    [ ! -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
}

@test "from_roadmap: --name-suffix appends" {
    run bash "$SH" --from-roadmap phase-1/arch --theme "定时循环" --project-root "$TEST_REPO" --name-prefix "feat-" --name-suffix "-rfc"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/feat-phase-1-arch-rfc.md" ]
}

@test "from_roadmap: --auto-name generates timestamp-based unique name" {
    run bash "$SH" --from-roadmap phase-1/arch --theme "定时循环" --project-root "$TEST_REPO" --name-prefix "batch-" --auto-name "yes"
    [ "$status" -eq 0 ]
    files=("$TEST_REPO"/.rddf/improvements/batch-phase-1-arch-*.md)
    [ ${#files[@]} -eq 1 ]
    [[ "${files[0]}" =~ batch-phase-1-arch-[0-9]{14}\.md$ ]]
}

@test "from_roadmap: conflict appends -2, -3 suffix" {
    bash "$SH" --from-roadmap phase-1/arch --theme "定时循环" --project-root "$TEST_REPO"
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
    bash "$SH" --from-roadmap phase-1/arch --theme "定时循环" --project-root "$TEST_REPO"
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch-2.md" ]
}

@test "from_roadmap: backward compat when no new env vars set" {
    run bash "$SH" --from-roadmap phase-2/infra --theme "主题2" --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-2-infra.md" ]
}