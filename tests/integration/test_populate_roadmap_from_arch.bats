#!/usr/bin/env bats
# Test populate-roadmap-from-arch skill.
# Per SKILL.md: 10 integration tests (backup + write + validate + dry-run + preflight failure modes)

load ../test_helper

setup_test_repo() {
    local tmp="$1"
    cd "$tmp"
    git init -q .
    git config user.email "test@test.local" && git config user.name "test"
    mkdir -p docs/adr docs/architecture .rddf/roadmap/phases .rddf/roadmap/features .rddf/roadmap/archive .rddf/state
    touch docs/adr/.gitkeep docs/architecture/.gitkeep .rddf/roadmap/.gitkeep .rddf/roadmap/phases/.gitkeep .rddf/roadmap/features/.gitkeep .rddf/roadmap/archive/.gitkeep .rddf/state/.gitkeep
    git add -A && git commit -qm "initial"
}

create_arch_handoff_v2() {
    cat > .rddf/state/.arch-handoff.json <<'EOF'
{
  "version": 2,
  "adr_dir": "docs/adr",
  "roadmap_path": ".rddf/roadmap.md",
  "architecture_dir": "docs/architecture",
  "roadmap_fragments_dir": ".rddf/roadmap"
}
EOF
}

create_main_doc() {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 完整多会话支持 | active | | |
| phase-2 | 审批交互 | active | | |
| phase-3 | 流程定制层 | active | | |
| phase-4 | 多方对称 | active | | |
EOF
}

create_empty_fragment() {
    local phase="$1"
    cat > ".rddf/roadmap/phases/${phase}.md" <<EOF
---
id: ${phase}
kind: phase
status: active
phase_refs: []
主题: TBD
---

## ${phase} content (migrated from root roadmap.md)
EOF
}

create_sample_adr() {
    cat > docs/adr/ADR-0001-multi-session.md <<'EOF'
# ADR-0001 多会话管理

> **状态**: 已采纳

## Decision

引入多 session 管理，支持跨 OpenCode session 的 workflow 恢复。
EOF
    cat > docs/adr/README.md <<'EOF'
# ADR Index

| 状态 | ADR |
|------|-----|
| 已实施（v2.0.0+） | ADR-0001 |
EOF
}

create_sample_arch_doc() {
    cat > docs/architecture/overview.md <<'EOF'
# Overview

Top-level architecture overview for the project.
EOF
}

setup() {
    TMP=$(mktemp -d)
    setup_test_repo "$TMP"
    create_arch_handoff_v2
    create_main_doc
    create_sample_adr
    create_sample_arch_doc
    for p in phase-1 phase-2 phase-3 phase-4; do create_empty_fragment "$p"; done
    git add -A && git commit -qm "populate fixtures"

    SCRIPT="$REPO_ROOT/skills/populate-roadmap-from-arch/scripts/populate.sh"
    cd "$TMP"
}

teardown() {
    cd /
    rm -rf "$TMP" 2>/dev/null || true
}

# ---- Tests ----

@test "populate: dry-run does not modify fragments" {
    bash "$SCRIPT" --dry-run --yes

    for p in phase-1 phase-2 phase-3 phase-4; do
        assert_file_contains ".rddf/roadmap/phases/${p}.md" "migrated from root roadmap.md"
        if grep -qF "## ${p} 概览" ".rddf/roadmap/phases/${p}.md"; then
            echo "FAIL: ${p} was modified during --dry-run"
            return 1
        fi
    done
}

@test "populate: --yes populates all 4 phase fragments" {
    bash "$SCRIPT" --yes

    for p in phase-1 phase-2 phase-3 phase-4; do
        assert_file_contains ".rddf/roadmap/phases/${p}.md" "## ${p} 概览"
        assert_file_contains ".rddf/roadmap/phases/${p}.md" "## 已实施能力"
        assert_file_contains ".rddf/roadmap/phases/${p}.md" "## 架构文档锚点"
    done
}

@test "populate: creates backup before write" {
    bash "$SCRIPT" --yes

    backup_count=$(ls .rddf/roadmap/.backup/ 2>/dev/null | wc -l)
    [ "$backup_count" -ge 1 ] || { echo "FAIL: no backup created"; return 1; }

    latest_backup=$(ls -t .rddf/roadmap/.backup/ | head -1)
    assert_file_exists ".rddf/roadmap/.backup/${latest_backup}/phases/phase-1.md"
    assert_file_exists ".rddf/roadmap/.backup/${latest_backup}/phases/phase-4.md"
}

@test "populate: --no-backup skips backup" {
    bash "$SCRIPT" --yes --no-backup

    backup_count=$(ls .rddf/roadmap/.backup/ 2>/dev/null | wc -l)
    [ "$backup_count" -eq 0 ] || { echo "FAIL: backup created despite --no-backup"; return 1; }
}

@test "populate: preserves fragment frontmatter" {
    bash "$SCRIPT" --yes

    head -7 ".rddf/roadmap/phases/phase-1.md" | grep -qF "id: phase-1" || { echo "FAIL: frontmatter id changed"; return 1; }
    head -7 ".rddf/roadmap/phases/phase-1.md" | grep -qF "kind: phase" || { echo "FAIL: frontmatter kind changed"; return 1; }
    head -7 ".rddf/roadmap/phases/phase-1.md" | grep -qF "status: active" || { echo "FAIL: frontmatter status changed"; return 1; }
}

@test "populate: includes ADR links in generated body" {
    bash "$SCRIPT" --yes

    grep -qF "../../docs/adr/ADR-0001-multi-session.md" .rddf/roadmap/phases/phase-1.md || { echo "FAIL: ADR link missing"; return 1; }
}

@test "populate: --phase flag scopes to single phase" {
    bash "$SCRIPT" --phase phase-2 --yes

    assert_file_contains ".rddf/roadmap/phases/phase-2.md" "## phase-2 概览"

    if grep -qF "## phase-1 概览" ".rddf/roadmap/phases/phase-1.md"; then
        echo "FAIL: phase-1 was populated despite --phase phase-2"
        return 1
    fi
    assert_file_contains ".rddf/roadmap/phases/phase-1.md" "migrated from root roadmap.md"
}

@test "populate: preflight fails if no .arch-handoff.json" {
    rm -f .rddf/state/.arch-handoff.json

    run bash "$SCRIPT" --yes
    [ "$status" -ne 0 ] || { echo "FAIL: preflight should have failed"; return 1; }
    echo "$output" | grep -qF ".arch-handoff.json" || { echo "FAIL: error msg missing .arch-handoff.json"; return 1; }
}

@test "populate: preflight fails if no ADR files" {
    rm -rf docs/adr
    mkdir -p docs/adr
    touch docs/adr/.gitkeep

    run bash "$SCRIPT" --yes
    [ "$status" -ne 0 ] || { echo "FAIL: preflight should have failed"; return 1; }
    echo "$output" | grep -qF "ADR" || { echo "FAIL: error msg missing ADR"; return 1; }
}

@test "populate: preflight fails if main doc missing Phase Skeleton" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

No skeleton here.
EOF

    run bash "$SCRIPT" --yes
    [ "$status" -ne 0 ] || { echo "FAIL: preflight should have failed"; return 1; }
    echo "$output" | grep -qF "Phase Skeleton" || { echo "FAIL: error msg missing Phase Skeleton"; return 1; }
}


# ============================================================
# v1.1+: --code-verify flag integration tests
# ============================================================

create_code_verify_adr() {
    # ADR name MUST match existing fixture (ADR-0001-multi-session) so README lookup applies
    # Use theme-matching keywords (Test Phase / 测试) so it gets classified to phase-1.
    cat > docs/adr/ADR-0001-multi-session.md <<'EOF'
# ADR-0001 测试 Test phase helper

> **状态**: 已采纳

## Decision

引入 Test Phase 自动化,使用 BACKTICK_OPENhelper_func()BACKTICK_CLOSE and BACKTICK_OPENMyClassBACKTICK_CLOSE.
EOF
    # Replace BACKTICK placeholders with real backticks via sed
    sed -i 's/BACKTICK_OPEN/`/g; s/BACKTICK_CLOSE/`/g' docs/adr/ADR-0001-multi-session.md
    cat > docs/adr/README.md <<'EOF'
# ADR Index

| 状态 | ADR |
|------|-----|
| 已实施（v2.0.0+） | ADR-0001 |
EOF
    mkdir -p src
    echo "def helper_func(): pass" > src/foo.py
    echo "class MyClass: pass" >> src/foo.py
}

@test "code_verify_off_dry_run_skips_supplementary" {
    create_code_verify_adr
    run bash "$SCRIPT" --yes --code-verify=off --dry-run
    [ "$status" -eq 0 ]
    [ ! -f "$TMP/.rddf/state/.populate-supplementary.json" ]
}

@test "code_verify_on_writes_supplementary_v1" {
    create_code_verify_adr
    run bash "$SCRIPT" --yes --code-verify=on
    [ -f "$TMP/.rddf/state/.populate-supplementary.json" ]
    python3 -c "
import json
data = json.load(open('$TMP/.rddf/state/.populate-supplementary.json'))
assert data['version'] == 1, 'expected version=1'
assert len(data['records']) >= 1
"
}

@test "code_verify_strict_exits_2_on_discrepancy" {
    cat > docs/adr/ADR-0001-test.md <<EOF
---
title: Test
status: 已采纳
implementation_version: v2.0.0+
---
\`nonexistent_one()\` and \`nonexistent_two()\` and \`nonexistent_three()\`.
EOF
    run bash "$SCRIPT" --yes --code-verify=strict --dry-run
    [ "$status" -eq 2 ]
}

@test "code_verify_on_RDD_NO_MCP_fallback_writes" {
    create_code_verify_adr
    RDD_NO_MCP=1 run bash "$SCRIPT" --yes --code-verify=on
    [ -f "$TMP/.rddf/state/.populate-supplementary.json" ]
    python3 -c "
import json, sys
data = json.load(open('$TMP/.rddf/state/.populate-supplementary.json'))
assert data['version'] == 1, f'expected version=1, got {data[\"version\"]}'
adr_rec = next((r for r in data['records'] if r['adr_id'] == 'ADR-0001'), None)
assert adr_rec is not None, f'ADR-0001 missing from records: {[r[\"adr_id\"] for r in data[\"records\"]]}'
assert adr_rec['verification_status'] == 'confirmed', f'unexpected status: {adr_rec[\"verification_status\"]}'
"
}

@test "code_verify_on_render_supports_new_badges" {
    # Verify rendering: generate fragment with code-verify=on, then check that
    # _format_adr_block with verification=confirmed emits the new badge
    # (we check via Python so the test is robust to fixture-ADR classification)
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/skills/populate-roadmap-from-arch/scripts')
from populate_lib import AdrRecord, AdrCodeVerification, _format_badge_confirmed
rec = AdrCodeVerification(
    adr_id='ADR-0001', self_claim_version='v2.0.0+',
    code_symbols_found=['foo'], code_symbols_expected=['foo'],
    verification_status='confirmed', has_discrepancy=False,
    verified_at='2026-08-21T00:00:00Z', mcp_used=False,
)
badge = _format_badge_confirmed(rec.self_claim_version)
assert badge == '*\uff08\u5df2\u5b9e\u65bd v2.0.0+ + \u4ee3\u7801\u9a8c\u8bc1\uff09*', f'unexpected badge: {badge!r}'
"
    [ "$status" -eq 0 ]
}
