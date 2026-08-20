#!/usr/bin/env bats
# Test skills/roadmap/scripts/roadmap_migrate.sh 9-step workflow.
# AC-1.16: ≥5 bats integration tests (dry-run / execute / rollback / 失败恢复 / 备份保留)

load ../test_helper

# Helper: source script in current shell (script uses bash with set -e; tests need fresh env per case).
setup_test_repo() {
    local tmp="$1"
    cd "$tmp"
    git init -q .
    git config user.email "test@test.local" && git config user.name "test"
    mkdir -p docs/adr
    # Sample root roadmap.md
    cat > roadmap.md <<'EOF'
# Test Roadmap

## Phase Skeleton

| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 基础架构 | done | 2026-01-01 | 2026-02-01 |
| phase-2 | 用户认证 | active | 2026-02-01 |  |

## Task Categories
- [x] auth-login (phase-2)
- [ ] rbac (phase-2)
EOF
    git add -A && git commit -qm "initial"
}

setup() {
    TMP=$(mktemp -d)
    setup_test_repo "$TMP"
    SCRIPT="/workspace/project/rdd-workflow/skills/roadmap/scripts/roadmap_migrate.sh"
}

teardown() {
    cd /
    rm -rf "$TMP" 2>/dev/null
}

@test "migrate --dry-run: previews slices without modifying any file" {
    cd "$TMP"
    run bash "$SCRIPT" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"phase-1"* ]]
    [[ "$output" == *"phase-2"* ]]
    [[ "$output" == *"Dry-run only"* ]]
    # Files NOT created
    [ ! -d ".rddf/roadmap/phases" ] || { ! ls ".rddf/roadmap/phases"/*.md >/dev/null 2>&1; }
    [ ! -f ".rddf/roadmap.md" ]
    # Original root roadmap.md unchanged
    grep -q "auth-login" roadmap.md
}

@test "migrate --execute: creates .rddf/roadmap/ + .rddf/roadmap.md + stub root roadmap.md" {
    cd "$TMP"
    run bash "$SCRIPT" --execute --yes
    [ "$status" -eq 0 ]
    # Fragments created
    [ -f ".rddf/roadmap/phases/phase-1.md" ]
    [ -f ".rddf/roadmap/phases/phase-2.md" ]
    # Fragment has theme from root (not hardcoded TBD)
    grep -q "主题: 基础架构" ".rddf/roadmap/phases/phase-1.md"
    grep -q "主题: 用户认证" ".rddf/roadmap/phases/phase-2.md"
    # Main doc created with AUTO-INDEX
    [ -f ".rddf/roadmap.md" ]
    grep -q "<!-- AUTO-ININDEX -->" ".rddf/roadmap.md" || grep -q "<!-- AUTO-INDEX -->" ".rddf/roadmap.md"
    # Root roadmap.md is now stub
    grep -q "本文件已迁移" roadmap.md
    grep -q ".rddf/roadmap.md" roadmap.md
}

@test "migrate --rollback: restores original root + removes new structure" {
    cd "$TMP"
    # Execute first
    bash "$SCRIPT" --execute --yes >/dev/null
    [ -d ".rddf/roadmap" ]
    # Find backup
    BACKUP=$(ls -td .rddf/.roadmap-migrate-backup-* | head -1)
    [ -n "$BACKUP" ]
    # Rollback
    run bash "$SCRIPT" --rollback "$BACKUP" --yes
    [ "$status" -eq 0 ]
    # Original root content restored
    grep -q "auth-login" roadmap.md
    grep -q "phase-1" roadmap.md
    # New structure removed
    [ ! -d ".rddf/roadmap" ]
    [ ! -f ".rddf/roadmap.md" ]
}

@test "migrate 备份保留: backup dir contains original roadmap.md" {
    cd "$TMP"
    bash "$SCRIPT" --execute --yes >/dev/null
    BACKUP=$(ls -td .rddf/.roadmap-migrate-backup-* | head -1)
    [ -f "$BACKUP/roadmap.md" ]
    grep -q "phase-1" "$BACKUP/roadmap.md"
    grep -q "基础架构" "$BACKUP/roadmap.md"
    # Verify backup timestamp present in dir name
    [[ "$BACKUP" == *".rddf/.roadmap-migrate-backup-"* ]]
}

@test "migrate refuses --execute without --yes (safety gate)" {
    cd "$TMP"
    run bash "$SCRIPT" --execute
    [ "$status" -ne 0 ]
    [[ "$output" == *"without --yes"* ]]
    # Nothing modified
    [ ! -d ".rddf/roadmap/phases" ] || { ! ls ".rddf/roadmap/phases"/*.md >/dev/null 2>&1; }
    [ ! -f ".rddf/roadmap.md" ]
}
