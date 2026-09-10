#!/usr/bin/env bats
# tests/integration/test_rdd_arch_no_roadmap.bats
# Integration tests for ADR-0048 §Decision 1: rdd-arch completely detached from roadmap.
#
# Verifies:
#  - rdd-arch SKILL.md role.boundaries.owns no longer lists roadmap.md or features/phases
#  - arch-done gate (arch_done_gate.sh) is single-gate (ADR >= 1 only)
#  - rdd-arch SKILL.md does not contain "Phase 4 roadmap-define"
#  - rdd-arch SKILL.md does not contain ".populate-state.json" in owns
#  - arch-done handoff v3 schema does NOT include roadmap_path field
#  - arch_done_gate.sh does NOT check roadmap existence

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    ARCH_SKILL="$REPO_ROOT/skills/rdd-arch/SKILL.md"
    ARCH_GATE="$REPO_ROOT/skills/rdd-arch/scripts/arch_done_gate.sh"
    SCHEMA="$REPO_ROOT/_lib/schemas/arch_handoff_schema.json"
    WORK_TMP="$(mktemp -d)"
    cd "$WORK_TMP"
    git init -q .
    mkdir -p docs/adr
}

teardown() {
    rm -rf "$WORK_TMP"
}

# Helper: extract frontmatter `boundaries:` block from a SKILL.md.
# awk state machine: track role/owns/not_owns regions, emit only bullet items.
extract_role_boundaries() {
    local skill_file="$1"
    awk '
        BEGIN { in_role = 0; in_owns = 0; in_not_owns = 0 }
        /^role:/ { in_role = 1; next }
        in_role && /^---$/ { exit }
        # Match `owns:` or `not_owns:` at start of line (with optional space).
        in_role && /^  owns:/ { in_owns = 1; in_not_owns = 0; next }
        in_role && /^  not_owns:/ { in_owns = 0; in_not_owns = 1; next }
        # Any other role:* key resets both flags.
        in_role && /^  [a-z_]+:/ { in_owns = 0; in_not_owns = 0 }
        in_role && in_owns && /^    - / { print "owns:", $0 }
        in_role && in_not_owns && /^    - / { print "not_owns:", $0 }
    ' "$skill_file"
}

# ---------------------------------------------------------------------------
# rdd-arch SKILL.md role.boundaries.owns cleanup (per ADR-0048 §Decision 1)
# ---------------------------------------------------------------------------

@test "rdd-arch: role.boundaries.owns does NOT contain roadmap.md" {
    [ -f "$ARCH_SKILL" ]
    run extract_role_boundaries "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    ! [[ "$output" =~ "owns:.*\"roadmap\.md\"" ]]
}

@test "rdd-arch: role.boundaries.owns does NOT contain .rddf/roadmap/features/*.md" {
    [ -f "$ARCH_SKILL" ]
    run extract_role_boundaries "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    ! [[ "$output" =~ "owns:.*\.rddf/roadmap/features" ]]
}

@test "rdd-arch: role.boundaries.owns does NOT contain .rddf/roadmap/phases/*.md" {
    [ -f "$ARCH_SKILL" ]
    run extract_role_boundaries "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    ! [[ "$output" =~ "owns:.*\.rddf/roadmap/phases" ]]
}

@test "rdd-arch: role.boundaries.owns does NOT contain .populate-state.json" {
    [ -f "$ARCH_SKILL" ]
    run extract_role_boundaries "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    ! [[ "$output" =~ "owns:.*populate-state" ]]
}

@test "rdd-arch: role.boundaries.not_owns contains roadmap.md (explicit denial)" {
    [ -f "$ARCH_SKILL" ]
    run extract_role_boundaries "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    # Use grep -F (fixed string) for robust matching of quoted path
    echo "$output" | grep -qF 'not_owns:     - "roadmap.md"'
}

@test "rdd-arch: role.boundaries.not_owns contains .rddf/roadmap/features/*.md (explicit denial)" {
    [ -f "$ARCH_SKILL" ]
    run extract_role_boundaries "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -qF 'not_owns:     - ".rddf/roadmap/features/*.md"'
}

# ---------------------------------------------------------------------------
# rdd-arch SKILL.md body: no Phase 4 roadmap-define (per ADR-0048 §Decision 1)
# ---------------------------------------------------------------------------

@test "rdd-arch: SKILL.md body does NOT contain 'Phase 4: roadmap-define'" {
    [ -f "$ARCH_SKILL" ]
    run grep -E "^## Phase 4:.*roadmap" "$ARCH_SKILL"
    [ "$status" -ne 0 ]
}

@test "rdd-arch: SKILL.md body does NOT contain 'roadmap-define' as a phase heading" {
    [ -f "$ARCH_SKILL" ]
    run grep -nE "^### Phase [0-9]+:.*roadmap-define" "$ARCH_SKILL"
    [ "$status" -ne 0 ]
}

@test "rdd-arch: SKILL.md mentions ADR-0048 in body (decision traceability)" {
    [ -f "$ARCH_SKILL" ]
    run grep -c "ADR-0048" "$ARCH_SKILL"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

# ---------------------------------------------------------------------------
# arch-done gate: single-gate (per ADR-0048 §Decision 1)
# ---------------------------------------------------------------------------

@test "arch_done_gate.sh: source comments mention single-gate per ADR-0048" {
    [ -f "$ARCH_GATE" ]
    run grep -E "single-gate|单门控|per ADR-0048" "$ARCH_GATE"
    [ "$status" -eq 0 ]
}

@test "arch_done_gate.sh: does NOT actively check roadmap_path existence" {
    [ -f "$ARCH_GATE" ]
    # After ADR-0048, the only "roadmap" reference should be in comments
    # (the deprecated DISCOVERED_ROADMAP_PATH env var). Any active `if [ ... roadmap ... ]`
    # check is a regression.
    run grep -nE "if .*roadmap.*\]|test -f .*roadmap" "$ARCH_GATE"
    [ "$status" -ne 0 ]
}

@test "arch_done_gate.sh: refuses when no ADR exists" {
    [ -f "$ARCH_GATE" ]
    # Setup: no ADR (empty docs/adr/), no roadmap
    # The script defines check_arch_done_gate() but does NOT auto-call it,
    # so we must source and invoke explicitly.
    run env -u PROJECT_ROOT bash -c "
        cd '$WORK_TMP'
        source '$ARCH_GATE'
        check_arch_done_gate
    "
    [ "$status" -ne 0 ]
    [[ "$output" =~ "失败" ]]
    [[ "$output" =~ "至少需要 1 个 ADR" ]]
}

@test "arch_done_gate.sh: refuses when no ADR exists even with roadmap present" {
    [ -f "$ARCH_GATE" ]
    # Setup: roadmap.md exists but no ADR — gate must STILL fail (per ADR-0048 single-gate)
    echo "# Roadmap" > roadmap.md
    run env -u PROJECT_ROOT bash -c "
        cd '$WORK_TMP'
        source '$ARCH_GATE'
        check_arch_done_gate
    "
    [ "$status" -ne 0 ]
    [[ "$output" =~ "失败" ]]
    [[ "$output" =~ "至少需要 1 个 ADR" ]]
}

# ---------------------------------------------------------------------------
# arch-handoff schema v3: no roadmap fields (per ADR-0043)
# ---------------------------------------------------------------------------

@test "arch-handoff schema: version 3 declared" {
    [ -f "$SCHEMA" ]
    run python3 -c "
import json
s = json.load(open('$SCHEMA'))
version = s.get('properties', {}).get('version', {})
assert version.get('enum') == [1, 2, 3], s
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "arch-handoff schema: does NOT require top-level roadmap_path" {
    [ -f "$SCHEMA" ]
    run python3 -c "
import json
s = json.load(open('$SCHEMA'))
required = s.get('required', [])
assert 'roadmap_path' not in required, s
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "arch-handoff schema: does NOT require top-level roadmap_exists" {
    [ -f "$SCHEMA" ]
    run python3 -c "
import json
s = json.load(open('$SCHEMA'))
required = s.get('required', [])
assert 'roadmap_exists' not in required, s
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}
